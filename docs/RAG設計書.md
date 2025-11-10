# RAG設計書 - 商品レコメンドLLMアプリ

## 📋 **RAG（Retrieval-Augmented Generation）概要**

### RAGシステムとは
本プロジェクトでは、FAISSを活用したベクトル検索によるRetrieval-Augmented Generationシステムを実装しています。従来の文字列マッチング検索に加えて、意味的類似度による高精度な商品検索を提供します。

### 実装状況
- ✅ **基本検索**: 文字列マッチング検索（メイン機能）
- ✅ **RAG検索**: FAISSベクトル検索（オプション機能）
- ✅ **ハイブリッド**: 両検索方式の併用可能

## 🏗️ **RAGアーキテクチャ設計**

### システム構成図
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ユーザークエリ   │ -> │   埋め込み生成    │ -> │  ベクトル検索     │
│   "疲労回復"      │    │  OpenAI API     │    │  FAISS Index    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      |
                                                      v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   検索結果表示    │ <- │   結果生成処理   │ <- │  類似度ランキング  │
│  商品リスト表示   │    │  商品情報取得    │    │  上位K件取得      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### データフロー
```
1. ユーザー入力 → テキスト正規化
2. OpenAI Embeddings → ベクトル変換
3. FAISS Index Search → 類似ベクトル検索
4. 結果マッピング → 商品情報取得
5. ランキング → 類似度順ソート
6. UI表示 → ユーザーへ結果提示
```

## 🔧 **技術実装詳細**

### 1. FAISSRAGSystemクラス設計

```python
class FAISSRAGSystem:
    def __init__(self, openai_api_key=None):
        """
        RAGシステム初期化
        
        Args:
            openai_api_key: OpenAI APIキー
        """
        self.openai_api_key = openai_api_key
        self.index = None
        self.documents = []
        self.metadata = []
        self.embeddings_model = None
        
        # キャッシュファイルパス
        self.cache_paths = {
            'index': 'data/faiss_index.bin',
            'documents': 'data/documents.pkl',
            'metadata': 'data/metadata.pkl',
            'mapping': 'data/faiss_mapping.json'
        }
    
    def initialize_openai(self):
        """OpenAI Embeddings初期化"""
        if self.openai_api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.openai_api_key)
            return True
        return False
    
    def build_index(self, products_df):
        """FAISSインデックス構築"""
        documents = []
        metadata = []
        
        # 商品データからドキュメント生成
        for idx, row in products_df.iterrows():
            doc_text = self._create_document_text(row)
            documents.append(doc_text)
            metadata.append({
                'index': idx,
                '商品名': row['商品名'],
                'カテゴリ': row['カテゴリ']
            })
        
        # 埋め込みベクトル生成
        embeddings = self._generate_embeddings(documents)
        
        # FAISSインデックス構築
        import faiss
        dimension = len(embeddings[0])
        self.index = faiss.IndexFlatIP(dimension)  # 内積類似度
        self.index.add(np.array(embeddings).astype('float32'))
        
        self.documents = documents
        self.metadata = metadata
        
        # キャッシュ保存
        self._save_cache()
        
        return True
```

### 2. 埋め込みベクトル生成

```python
def _create_document_text(self, row):
    """
    商品データからドキュメントテキスト生成
    
    Args:
        row: 商品データ行（pandas Series）
    
    Returns:
        str: 構造化されたドキュメントテキスト
    """
    doc_parts = []
    
    # 商品名（重要度: 高）
    if pd.notna(row['商品名']):
        doc_parts.append(f"商品名: {row['商品名']}")
    
    # 効果（重要度: 高）
    if pd.notna(row['効果']):
        doc_parts.append(f"効果: {row['効果']}")
    
    # カテゴリ（重要度: 中）
    if pd.notna(row['カテゴリ']):
        doc_parts.append(f"カテゴリ: {row['カテゴリ']}")
    
    # 成分（重要度: 中）
    if pd.notna(row['成分']):
        doc_parts.append(f"成分: {row['成分']}")
    
    # 説明（重要度: 低）
    if pd.notna(row['説明']):
        doc_parts.append(f"説明: {row['説明']}")
    
    return "\n".join(doc_parts)

def _generate_embeddings(self, texts):
    """
    テキストリストから埋め込みベクトル生成
    
    Args:
        texts: テキストのリスト
    
    Returns:
        List[List[float]]: 埋め込みベクトルのリスト
    """
    embeddings = []
    
    for text in texts:
        try:
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"  # 高速・軽量モデル
            )
            embedding = response.data[0].embedding
            embeddings.append(embedding)
            
        except Exception as e:
            print(f"埋め込み生成エラー: {e}")
            # フォールバック: ゼロベクトル
            embeddings.append([0.0] * 1536)
    
    return embeddings
```

### 3. 検索実行機能

```python
def search(self, query, k=5):
    """
    ベクトル検索実行
    
    Args:
        query: 検索クエリ文字列
        k: 取得件数（デフォルト: 5）
    
    Returns:
        List[Dict]: 検索結果リスト
    """
    if not self.index or not self.openai_api_key:
        return []
    
    try:
        # クエリの埋め込み生成
        query_embedding = self._generate_embeddings([query])[0]
        query_vector = np.array([query_embedding]).astype('float32')
        
        # FAISS検索実行
        scores, indices = self.index.search(query_vector, k)
        
        # 結果構築
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.metadata):
                result = {
                    'rank': i + 1,
                    'score': float(score),
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx]
                }
                results.append(result)
        
        return results
        
    except Exception as e:
        print(f"RAG検索エラー: {e}")
        return []
```

## 🗄️ **データ構造設計**

### ドキュメント構造
```python
# 商品ドキュメント例
document_structure = {
    "text": """
商品名: スペマン
効果: 精力増強、滋養強壮、疲労回復
カテゴリ: 男性向けサプリ
成分: 高麗人参、マカ、亜鉛、アルギニン
説明: 天然成分を配合した男性向けの滋養強壮サプリメント
""",
    "embedding": [0.123, -0.456, 0.789, ...],  # 1536次元ベクトル
    "metadata": {
        "index": 0,
        "商品名": "スペマン",
        "カテゴリ": "男性向けサプリ"
    }
}
```

### FAISSインデックス設計
```python
# インデックス設定
index_config = {
    "type": "IndexFlatIP",        # 内積類似度インデックス
    "dimension": 1536,            # OpenAI text-embedding-3-small
    "metric": "inner_product",    # 内積類似度測定
    "size": "35_products",        # 35商品分のベクトル
    "memory_usage": "~200MB"      # 推定メモリ使用量
}

# キャッシュファイル構成
cache_files = {
    "faiss_index.bin": "FAISSインデックス本体",
    "documents.pkl": "元文書テキスト",
    "metadata.pkl": "商品メタデータ", 
    "faiss_mapping.json": "設定情報"
}
```

## 🔍 **検索アルゴリズム**

### 類似度計算手法
```python
# 1. コサイン類似度（正規化済み）
def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# 2. 内積類似度（FAISS使用）
def inner_product_similarity(query_vec, doc_vecs):
    return np.dot(query_vec, doc_vecs.T)

# 3. ユークリッド距離（距離ベース）
def euclidean_distance(vec1, vec2):
    return np.linalg.norm(vec1 - vec2)
```

### ランキングアルゴリズム
```python
def rank_results(search_results, query):
    """
    検索結果のランキング調整
    
    Args:
        search_results: FAISS検索結果
        query: 元クエリ
    
    Returns:
        List: 調整済み結果リスト
    """
    ranked_results = []
    
    for result in search_results:
        # 基本スコア（FAISS類似度）
        base_score = result['score']
        
        # ブーストファクター適用
        boosted_score = base_score
        
        # 商品名完全一致ブースト
        if query.lower() in result['metadata']['商品名'].lower():
            boosted_score *= 1.5
        
        # カテゴリ一致ブースト  
        if query.lower() in result['metadata']['カテゴリ'].lower():
            boosted_score *= 1.2
        
        result['final_score'] = boosted_score
        ranked_results.append(result)
    
    # 最終スコア順でソート
    return sorted(ranked_results, key=lambda x: x['final_score'], reverse=True)
```

## ⚡ **パフォーマンス最適化**

### キャッシュ戦略
```python
class CacheManager:
    def __init__(self):
        self.embedding_cache = {}  # クエリ埋め込みキャッシュ
        self.result_cache = {}     # 検索結果キャッシュ
        self.max_cache_size = 1000
    
    def get_cached_embedding(self, text):
        """埋め込みキャッシュ取得"""
        return self.embedding_cache.get(text)
    
    def cache_embedding(self, text, embedding):
        """埋め込みキャッシュ保存"""
        if len(self.embedding_cache) < self.max_cache_size:
            self.embedding_cache[text] = embedding
    
    def get_cached_results(self, query_hash):
        """検索結果キャッシュ取得"""
        return self.result_cache.get(query_hash)
```

### インデックス最適化
```python
def optimize_index():
    """FAISSインデックス最適化"""
    # PCA次元削減（メモリ削減）
    pca_dimension = 512  # 1536 -> 512次元
    
    # 量子化（精度 vs 速度トレードオフ）
    quantizer = faiss.IndexFlatIP(pca_dimension)
    index = faiss.IndexIVFPQ(quantizer, pca_dimension, 8, 8, 8)
    
    return index
```

## 📊 **評価・メトリクス**

### 検索精度評価
```python
evaluation_metrics = {
    # 精度指標
    "precision_at_k": "上位K件中の関連商品割合",
    "recall_at_k": "関連商品の検索ヒット率", 
    "mrr": "Mean Reciprocal Rank",
    "ndcg": "正規化割引累積利得",
    
    # パフォーマンス指標
    "response_time": "平均応答時間",
    "throughput": "1秒あたり処理クエリ数",
    "memory_usage": "メモリ使用量",
    "index_size": "インデックスサイズ"
}
```

### テストケース設計
```python
test_cases = [
    # 症状ベース検索
    {
        "query": "頭痛",
        "expected": ["解熱鎮痛薬", "風邪薬"],
        "category": "symptom_search"
    },
    
    # 成分ベース検索
    {
        "query": "高麗人参",
        "expected": ["スペマン", "その他高麗人参商品"],
        "category": "ingredient_search"
    },
    
    # 効果ベース検索
    {
        "query": "精力増強",
        "expected": ["男性向けサプリ"],
        "category": "effect_search"
    }
]
```

## 🔧 **設定・調整パラメータ**

### 検索パラメータ
```python
search_config = {
    # 検索結果数
    "top_k": 5,                    # 上位5件取得
    "min_score_threshold": 0.7,    # 最低類似度閾値
    
    # 埋め込みモデル
    "embedding_model": "text-embedding-3-small",
    "embedding_dimension": 1536,
    
    # FAISS設定
    "index_type": "IndexFlatIP",
    "metric_type": "inner_product",
    
    # キャッシュ設定
    "enable_cache": True,
    "cache_ttl": 3600,             # 1時間
    "max_cache_entries": 1000
}
```

### ブーストファクター
```python
boost_factors = {
    "exact_product_match": 1.5,    # 商品名完全一致
    "category_match": 1.2,         # カテゴリ一致
    "ingredient_match": 1.1,       # 成分一致
    "recent_product": 1.05,        # 新商品ブースト
    "popular_product": 1.03        # 人気商品ブースト
}
```

## 🛡️ **エラーハンドリング・フォールバック**

### フォールバック戦略
```python
def search_with_fallback(query, k=5):
    """
    RAG検索 + フォールバック検索
    
    1. RAG検索実行
    2. 失敗時 → 基本検索にフォールバック
    3. 結果マージ・重複除去
    """
    try:
        # RAG検索実行
        rag_results = rag_system.search(query, k)
        
        if rag_results:
            return rag_results
        
    except Exception as e:
        print(f"RAG検索失敗: {e}")
    
    # フォールバック: 基本検索
    print("基本検索にフォールバック")
    return basic_search(query, "症状")

def hybrid_search(query, k=5):
    """
    ハイブリッド検索（RAG + 基本検索）
    
    両方の結果を統合して最適な結果を提供
    """
    rag_results = rag_system.search(query, k)
    basic_results = basic_search(query, "症状")
    
    # 結果統合・重複除去
    combined_results = merge_and_deduplicate(rag_results, basic_results)
    
    return combined_results[:k]
```

### エラーハンドリング
```python
class RAGException(Exception):
    """RAGシステム専用例外"""
    pass

def robust_rag_search(query):
    """堅牢なRAG検索実装"""
    try:
        # 入力検証
        if not query or len(query.strip()) == 0:
            raise RAGException("空のクエリです")
        
        # API制限チェック
        if not check_api_limits():
            raise RAGException("API制限に達しました")
        
        # 検索実行
        results = rag_system.search(query)
        
        # 結果検証
        if not results:
            raise RAGException("検索結果が見つかりません")
        
        return results
        
    except RAGException as e:
        print(f"RAGエラー: {e}")
        return fallback_search(query)
    
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return []
```

## 🚀 **デプロイ・運用設定**

### 環境別設定
```python
# 開発環境
dev_config = {
    "use_rag": True,
    "cache_enabled": False,
    "debug_logging": True,
    "api_timeout": 30
}

# 本番環境  
prod_config = {
    "use_rag": True,
    "cache_enabled": True,
    "debug_logging": False,
    "api_timeout": 10
}
```

### 監視・ログ
```python
import logging

# RAGシステム専用ログ
rag_logger = logging.getLogger('rag_system')
rag_logger.setLevel(logging.INFO)

def log_search_metrics(query, results, execution_time):
    """検索メトリクスのログ記録"""
    rag_logger.info(f"検索実行: query='{query}', "
                   f"results={len(results)}, "
                   f"time={execution_time:.3f}s")
```

## 📈 **今後の改善計画**

### Phase 1: 精度向上
- ファインチューニング済み埋め込みモデル
- カスタム類似度計算手法
- ドメイン特化辞書

### Phase 2: スケーリング  
- 分散FAISSインデックス
- Redis結果キャッシュ
- ロードバランサ対応

### Phase 3: 高度機能
- 多段階検索（coarse-to-fine）
- リランキングモデル
- ユーザーフィードバック学習

**RAGシステム設計完了**: 2025年11月11日