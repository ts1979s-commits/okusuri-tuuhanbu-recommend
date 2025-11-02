"""
FAISS ベースRAGシステム - お薬通販部商品レコメンドLLMアプリ
FAISSとOpenAI Embeddingsを使用した検索・レコメンド機能
"""
import json
import os
import pickle
import csv
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass

import faiss
import numpy as np
from openai import OpenAI

from config.settings import get_settings

settings = get_settings()

# ログ設定
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """検索結果データクラス"""
    product_name: str
    url: str
    price: Optional[str]
    description: Optional[str]
    category: Optional[str]
    similarity_score: float
    metadata: Dict[str, Any]

class FAISSRAGSystem:
    """FAISSベースの商品検索・レコメンドシステム"""
    
    def __init__(self):
        """RAGシステムの初期化"""
        # OpenAIクライアントの初期化
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            raise ValueError("OPENAI_API_KEYが必要です")
        
        # プロキシ環境変数をクリア
        import os
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                del os.environ[key]
        
        try:
            # 最小限のパラメータでクライアントを作成
            # proxies引数は明示的に使用しない
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=30.0
            )
            logger.info("OpenAIクライアントを初期化しました")
        except TypeError as te:
            if "proxies" in str(te):
                # プロキシエラーの場合、より基本的な初期化を試行
                logger.warning("プロキシエラーを検出。基本的な初期化を試行中...")
                try:
                    self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("基本的なOpenAIクライアント初期化に成功")
                except Exception as e2:
                    logger.error(f"基本的な初期化も失敗: {e2}")
                    raise
            else:
                logger.error(f"OpenAIクライアント初期化エラー: {te}")
                raise
        except Exception as e:
            logger.error(f"OpenAIクライアント初期化エラー: {e}")
            # 可能性のある問題をチェック
            if "proxies" in str(e):
                logger.error("プロキシ関連エラーが検出されました。環境変数を確認してください。")
            raise
        
        # FAISS設定
        self.index = None
        self.metadata_list = []
        self.documents = []
        self.dimension = 1536  # OpenAI embedding dimension
        
        # データ保存パス
        self.data_dir = "./data"
        self.index_path = os.path.join(self.data_dir, "faiss_index.bin")
        self.metadata_path = os.path.join(self.data_dir, "metadata.pkl")
        self.documents_path = os.path.join(self.data_dir, "documents.pkl")
        
        # 既存のインデックスを読み込み
        self._load_index()
        
    def _load_index(self):
        """既存のFAISSインデックスを読み込み"""
        try:
            if (os.path.exists(self.index_path) and 
                os.path.exists(self.metadata_path) and 
                os.path.exists(self.documents_path)):
                
                # FAISSインデックスを読み込み
                self.index = faiss.read_index(self.index_path)
                
                # メタデータを読み込み
                with open(self.metadata_path, 'rb') as f:
                    self.metadata_list = pickle.load(f)
                
                # ドキュメントを読み込み
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                logger.info(f"既存のインデックスを読み込みました: {len(self.metadata_list)}件")
            else:
                # 新しいインデックスを作成
                self._create_new_index()
                
        except Exception as e:
            logger.error(f"インデックス読み込みエラー: {e}")
            self._create_new_index()
    
    def _create_new_index(self):
        """新しいFAISSインデックスを作成"""
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product (Cosine similarity)
        self.metadata_list = []
        self.documents = []
        logger.info("新しいFAISSインデックスを作成しました")
    
    def _save_index(self):
        """FAISSインデックスとメタデータを保存"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            
            # FAISSインデックスを保存
            faiss.write_index(self.index, self.index_path)
            
            # メタデータを保存
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata_list, f)
            
            # ドキュメントを保存
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info("インデックスとメタデータを保存しました")
            
        except Exception as e:
            logger.error(f"インデックス保存エラー: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """テキストの埋め込みベクトルを取得"""
        try:
            # シンプルな方法でembeddingを取得
            response = self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"埋め込み取得エラー: {e}")
            return []
    
    def add_products(self, products_data: List[Dict[str, Any]]):
        """商品データをベクトルDBに追加"""
        if not products_data:
            logger.warning("追加する商品データがありません")
            return
        
        embeddings_to_add = []
        metadata_to_add = []
        documents_to_add = []
        
        for i, product in enumerate(products_data):
            # 商品情報からテキストを構築
            doc_text = self._build_document_text(product)
            
            # 埋め込みベクトルを取得
            embedding = self.get_embedding(doc_text)
            if not embedding:
                logger.warning(f"商品 '{product.get('name', 'Unknown')}' の埋め込み取得に失敗")
                continue
            
            # データを準備
            embeddings_to_add.append(embedding)
            
            # CSV構造とJSONの両方に対応したメタデータ
            metadata = {
                'name': product.get('商品名') or product.get('name', ''),
                'url': product.get('商品URL') or product.get('url', ''),
                'price': product.get('price', ''),  # CSVには価格がないため空
                'description': product.get('説明文') or product.get('description', ''),
                'category': product.get('カテゴリ名') or product.get('category', ''),
                'subcategory': product.get('サブカテゴリ名', ''),
                '効果': product.get('効果', ''),  # 効果をそのままのキー名で保存
                '有効成分': product.get('有効成分', ''),  # 有効成分をそのままのキー名で保存
                'category_url': product.get('カテゴリURL', ''),
                'subcategory_url': product.get('サブカテゴリURL', ''),
                'image_url': product.get('image_url', ''),
                'csv_order': i  # CSV登録順を記録
            }
            
            metadata_to_add.append(metadata)
            documents_to_add.append(doc_text)
            
            # 進捗表示
            if (i + 1) % 10 == 0:
                logger.info(f"埋め込み作成進捗: {i + 1}/{len(products_data)}")
        
        if embeddings_to_add:
            # FAISSインデックスに追加
            embeddings_array = np.array(embeddings_to_add, dtype=np.float32)
            
            # ベクトルを正規化（コサイン類似度のため）
            faiss.normalize_L2(embeddings_array)
            
            self.index.add(embeddings_array)
            self.metadata_list.extend(metadata_to_add)
            self.documents.extend(documents_to_add)
            
            # インデックスを保存
            self._save_index()
            
            logger.info(f"{len(embeddings_to_add)}件の商品をベクトルDBに追加しました")
        else:
            logger.warning("追加できる商品データがありませんでした")
    
    def _build_document_text(self, product: Dict[str, Any]) -> str:
        """商品情報からドキュメントテキストを構築（CSV構造対応）"""
        parts = []
        
        # 商品名
        if product.get('商品名') or product.get('name'):
            product_name = product.get('商品名') or product.get('name')
            parts.append(f"商品名: {product_name}")
        
        # カテゴリ（メインカテゴリ + サブカテゴリ）
        if product.get('カテゴリ名') or product.get('category'):
            category = product.get('カテゴリ名') or product.get('category')
            parts.append(f"カテゴリ: {category}")
        
        if product.get('サブカテゴリ名'):
            parts.append(f"サブカテゴリ: {product['サブカテゴリ名']}")
        
        # 効果
        if product.get('効果'):
            parts.append(f"効果: {product['効果']}")
        
        # 有効成分
        if product.get('有効成分'):
            parts.append(f"有効成分: {product['有効成分']}")
        
        # 説明文
        if product.get('説明文') or product.get('description'):
            description = product.get('説明文') or product.get('description')
            parts.append(f"説明: {description}")
        
        # 価格（後方互換性）
        if product.get('price'):
            parts.append(f"価格: {product['price']}円")
        
        # 旧フォーマット対応
        if product.get('ingredients'):
            parts.append(f"成分: {product['ingredients']}")
        
        if product.get('usage'):
            parts.append(f"用法: {product['usage']}")
        
        return " ".join(parts)
    
    def search_products(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """商品を検索（自然言語対応 + 完全一致検索 + ベクトル検索の組み合わせ）"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("インデックスが空です")
                return []
            
            # 0. 有効成分の厳密検索をチェック
            if self._is_ingredient_search(query):
                logger.info(f"有効成分検索モード: {query}")
                ingredient_results = self._ingredient_exact_search(query.strip(), top_k)
                
                # 有効成分検索で結果が見つからない場合、通常検索にフォールバック
                if not ingredient_results:
                    logger.warning(f"有効成分検索で結果なし。通常検索にフォールバック: {query}")
                    # 通常検索を実行
                    pass  # 下記の通常検索ロジックに続行
                else:
                    return ingredient_results
            
            # 1. 自然言語から検索キーワードを抽出
            extracted_keywords = self._extract_keywords_from_query(query)
            
            # 2. クエリから対象カテゴリーを特定
            target_category = self._get_target_category_from_query(query)
            logger.info(f"対象カテゴリー: {target_category}")
            
            # 3. 抽出されたキーワードで完全一致検索を実行
            exact_match_results = []
            for keyword in extracted_keywords:
                keyword_results = self._exact_match_search(keyword, top_k)
                exact_match_results.extend(keyword_results)
            
            # 4. 元のクエリでも完全一致検索を実行
            original_exact_results = self._exact_match_search(query.strip(), top_k)
            exact_match_results.extend(original_exact_results)
            
            # 5. ベクトル検索を実行（カテゴリー情報を渡す）
            vector_search_results = self._vector_search(query, top_k, target_category)
            
            # 6. カテゴリーフィルタリングを適用
            if target_category:
                exact_match_results = self._filter_by_category(exact_match_results, target_category)
                vector_search_results = self._filter_by_category(vector_search_results, target_category)
            
            # 7. 結果をマージして重複を除去し、CSV順でソート
            combined_results = self._merge_and_sort_results(
                exact_match_results, vector_search_results, top_k
            )
            
            logger.info(f"検索完了: {len(combined_results)}件の結果")
            return combined_results
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []
    
    def _is_ingredient_search(self, query: str) -> bool:
        """有効成分による検索かどうかを判定"""
        query_lower = query.lower().strip()
        
        # 既知の有効成分リスト
        known_ingredients = [
            'シルデナフィル', 'タダラフィル', 'バルデナフィル', 'アバナフィル', 'ウデナフィル',
            'ミノキシジル', 'フィナステリド', 'デュタステリド', 'ケトコナゾール',
            'アジスロマイシン', 'フルコナゾール', 'イソトレチノイン', 'ヒトプラセンタ',
            'ビマトプロスト', 'トラセミド', 'オルリスタット', 'プエラリアミリフィカ'
        ]
        
        # 完全一致または部分一致チェック（判定を緩和）
        for ingredient in known_ingredients:
            if ingredient.lower() in query_lower or query_lower in ingredient.lower():
                return True
        return False
    
    def _ingredient_exact_search(self, query: str, top_k: int) -> List[SearchResult]:
        """有効成分による厳密検索（シンプル版）"""
        results = []
        query_lower = query.lower().strip()
        logger.info(f"有効成分検索開始: クエリ='{query_lower}'")
        
        for i, metadata in enumerate(self.metadata_list):
            # 有効成分フィールドで検索
            ingredient = metadata.get('ingredient', '').lower().strip()
            
            # シンプルな含有チェック
            if ingredient and query_lower in ingredient:
                logger.info(f"マッチ: {metadata.get('name', '')} - {ingredient}")
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=1.0,
                    metadata=metadata
                )
                results.append(search_result)
        
        logger.info(f"有効成分検索結果: {len(results)}件")
        
        # CSV順でソート
        results.sort(key=lambda x: x.metadata.get('csv_order', 999))
        return results[:top_k]
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """自然言語クエリから検索キーワードを抽出"""
        keywords = []
        query_lower = query.lower()
        
        # 既知の有効成分リスト
        known_ingredients = [
            'シルデナフィル', 'タダラフィル', 'バルデナフィル', 'アバナフィル', 'ウデナフィル',
            'ミノキシジル', 'フィナステリド', 'デュタステリド', 'ケトコナゾール',
            'アジスロマイシン', 'フルコナゾール', 'イソトレチノイン', 'ヒトプラセンタ',
            'ビマトプロスト', 'トラセミド', 'オルリスタット', 'プエラリアミリフィカ'
        ]
        
        # 既知の効果・症状リスト
        known_effects = [
            'ED改善', '発毛促進', 'AGA改善', '美白', 'ニキビ治療', '不感症改善',
            'バストアップ', 'まつ毛育毛', 'むくみ改善', '便秘改善', '細菌感染症治療'
        ]
        
        # カテゴリーと症状のマッピング
        category_symptom_mapping = {
            'aga': ['AGA治療薬', 'AGA改善', '発毛促進', 'ミノキシジル', 'フィナステリド', 'デュタステリド'],
            'ed': ['ED治療薬', 'ED改善', 'シルデナフィル', 'タダラフィル', 'バルデナフィル', 'アバナフィル', 'ウデナフィル'],
            '美容': ['美容', '美白', 'まつ毛育毛', 'ニキビ治療'],
            'ダイエット': ['ダイエット', 'オルリスタット', 'トラセミド'],
        }
        
        # 既知のカテゴリリスト
        known_categories = [
            'ED治療薬', 'AGA治療薬', '美容・スキンケア', 'ダイエット', '性病・感染症の治療薬'
        ]
        
        # 症状や目的を表すキーワード
        symptom_mapping = {
            'ed': ['ED改善', 'シルデナフィル', 'タダラフィル'],
            '勃起': ['ED改善', 'シルデナフィル', 'タダラフィル'],
            '薄毛': ['AGA改善', 'ミノキシジル', 'フィナステリド'],
            'ハゲ': ['AGA改善', 'ミノキシジル', 'フィナステリド'],
            'aga': ['AGA改善', 'ミノキシジル', 'フィナステリド'],
            '発毛': ['AGA改善', 'ミノキシジル'],
            'ダイエット': ['オルリスタット'],
            '痩せ': ['オルリスタット'],
            'まつ毛': ['ビマトプロスト'],
            'ニキビ': ['イソトレチノイン'],
            '美白': ['ヒトプラセンタ'],
            'バスト': ['プエラリアミリフィカ'],
            'むくみ': ['トラセミド']
        }
        
        # すべての既知キーワードリスト
        all_known_keywords = known_ingredients + known_effects + known_categories
        
        # クエリ内に含まれる既知キーワードを抽出
        for keyword in all_known_keywords:
            if keyword.lower() in query_lower:
                keywords.append(keyword)
        
        # 症状マッピングから関連キーワードを抽出
        for symptom, related_keywords in symptom_mapping.items():
            if symptom in query_lower:
                keywords.extend(related_keywords)
        
        # 商品名の一部も抽出（一般的なもの）
        product_keywords = [
            'カマグラ', 'タダライズ', 'バリフ', 'アバナ', 'ザイスマ', 'スペマン', 'ラブグラ',
            'ミノクソール', 'フィナクス', 'デュタストロン', 'ニゾラール', 'プレミアムリジン'
        ]
        
        for keyword in product_keywords:
            if keyword.lower() in query_lower:
                keywords.append(keyword)
        
        # 質問パターンの解析（「○○のお薬」「○○の薬」など）
        import re
        # 「XXのお薬」「XXの薬」「XXの治療薬」パターン
        patterns = [
            r'(\w+)のお薬',
            r'(\w+)の薬', 
            r'(\w+)の治療薬',
            r'(\w+)を治す',
            r'(\w+)に効く'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                # マッチした単語が既知のキーワードと関連があるかチェック
                for keyword in all_known_keywords:
                    if match in keyword or keyword in match:
                        keywords.append(keyword)
                # 症状マッピングもチェック
                if match.lower() in symptom_mapping:
                    keywords.extend(symptom_mapping[match.lower()])
        
        return list(set(keywords))  # 重複を除去して返す
    
    def _get_target_category_from_query(self, query: str) -> Optional[str]:
        """クエリから対象カテゴリーを特定"""
        query_lower = query.lower().strip()
        
        # カテゴリーマッピング
        category_mapping = {
            'aga': ['aga', '薄毛', 'はげ', '抜け毛', '発毛', 'フィナステリド', 'ミノキシジル', 'デュタステリド', 'フィナクス', 'ミノクソール', 'デュタストロン'],
            'ed': ['ed', '勃起不全', 'インポテンツ', 'シルデナフィル', 'タダラフィル', 'バルデナフィル', 'アバナフィル', 'ウデナフィル', 'カマグラ', 'タダライズ', 'バリフ', 'アバナ', 'ザイスマ'],
            '美容': ['美容', '美白', 'ニキビ', 'まつ毛', 'スキンケア'],
            'ダイエット': ['ダイエット', '減量', 'オルリスタット', 'むくみ'],
        }
        
        # クエリと各カテゴリーキーワードをマッチング
        for category, keywords in category_mapping.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return category
        
        return None
    
    def _filter_by_category(self, results: List[SearchResult], target_category: str) -> List[SearchResult]:
        """カテゴリーでフィルタリング"""
        if not target_category:
            return results
        
        filtered_results = []
        for result in results:
            category = result.metadata.get('category', '').lower()
            
            # カテゴリーマッチング
            if target_category == 'aga' and 'aga' in category:
                filtered_results.append(result)
            elif target_category == 'ed' and 'ed' in category:
                filtered_results.append(result)
            elif target_category == '美容' and '美容' in category:
                filtered_results.append(result)
            elif target_category == 'ダイエット' and 'ダイエット' in category:
                filtered_results.append(result)
            else:
                # その他のカテゴリーや一般検索の場合は含める
                if target_category not in ['aga', 'ed']:
                    filtered_results.append(result)
        
        return filtered_results
    
    def _exact_match_search(self, query: str, top_k: int) -> List[SearchResult]:
        """完全一致検索（厳密な単語マッチング）"""
        results = []
        query_lower = query.lower().strip()
        
        for i, metadata in enumerate(self.metadata_list):
            score = 0
            
            # 各フィールドで完全一致をチェック
            fields_to_search = [
                ('category', metadata.get('category', '')),
                ('name', metadata.get('name', '')),
                ('effect', metadata.get('effect', '')),
                ('ingredient', metadata.get('ingredient', '')),
                ('description', metadata.get('description', ''))
            ]
            
            for field_name, field_value in fields_to_search:
                if field_value:
                    field_lower = field_value.lower().strip()
                    
                    # 完全一致検索（より厳密）
                    exact_match = False
                    
                    # 1. フィールド全体と完全一致
                    if query_lower == field_lower:
                        exact_match = True
                    else:
                        # 2. 区切り文字で分割して単語として完全一致
                        import re
                        # 日本語の区切り文字も含める
                        field_words = re.split(r'[、，,\s・]+', field_lower)
                        field_words = [word.strip() for word in field_words if word.strip()]
                        
                        # クエリが単語として完全一致するかチェック
                        if query_lower in field_words:
                            exact_match = True
                    
                    if exact_match:
                        # フィールドの重要度に応じてスコアを設定
                        if field_name == 'name':
                            score = max(score, 1.0)  # 商品名は最高スコア
                        elif field_name == 'ingredient':
                            score = max(score, 0.95)  # 有効成分も高スコア
                        elif field_name == 'effect':
                            score = max(score, 0.9)   # 効果も高スコア
                        elif field_name == 'category':
                            score = max(score, 0.85)  # カテゴリも高スコア
                        elif field_name == 'description':
                            score = max(score, 0.8)   # 説明文は少し低め
            
            # マッチした場合は結果に追加
            if score > 0:
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=score,
                    metadata=metadata
                )
                results.append(search_result)
        
        # CSV順でソート
        results.sort(key=lambda x: x.metadata.get('csv_order', 999))
        return results[:top_k]
    
    def _vector_search(self, query: str, top_k: int, target_category: Optional[str] = None) -> List[SearchResult]:
        """従来のベクトル検索（カテゴリーボーナス付き）"""
        try:
            # クエリの埋め込みベクトルを取得
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("クエリの埋め込み取得に失敗")
                return []
            
            # ベクトルを正規化
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # 検索を実行
            scores, indices = self.index.search(query_vector, min(top_k * 2, self.index.ntotal))  # より多く取得してフィルタリング
            
            # 結果を整形
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 無効なインデックス
                    continue
                    
                metadata = self.metadata_list[idx]
                
                # カテゴリーボーナススコアリング
                adjusted_score = float(score)
                if target_category:
                    category = metadata.get('category', '').lower()
                    if target_category == 'aga' and 'aga' in category:
                        adjusted_score += 0.2  # AGAカテゴリーボーナス
                    elif target_category == 'ed' and 'ed' in category:
                        adjusted_score += 0.2  # EDカテゴリーボーナス
                    elif target_category == '美容' and '美容' in category:
                        adjusted_score += 0.2  # 美容カテゴリーボーナス
                    elif target_category == 'ダイエット' and 'ダイエット' in category:
                        adjusted_score += 0.2  # ダイエットカテゴリーボーナス
                
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=adjusted_score,
                    metadata=metadata
                )
                results.append(search_result)
            
            # スコアでソートして上位を返す
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"ベクトル検索エラー: {e}")
            return []
    
    def _merge_and_sort_results(
        self, 
        exact_results: List[SearchResult], 
        vector_results: List[SearchResult], 
        top_k: int
    ) -> List[SearchResult]:
        """完全一致検索とベクトル検索の結果をマージしてソート"""
        
        # 完全一致の結果がある場合は、それらのみを返す（ベクトル検索結果は無視）
        if exact_results:
            # 完全一致結果をスコア順→CSV順でソート
            exact_results.sort(
                key=lambda x: (-x.similarity_score, x.metadata.get('csv_order', 999))
            )
            return exact_results[:top_k]
        
        # 完全一致結果がない場合のみベクトル検索結果を使用
        else:
            # ベクトル検索のスコアを調整（完全一致より低く）
            for result in vector_results:
                result.similarity_score = min(result.similarity_score, 0.75)
            
            # ベクトル検索結果をスコア順→CSV順でソート
            vector_results.sort(
                key=lambda x: (-x.similarity_score, x.metadata.get('csv_order', 999))
            )
            return vector_results[:top_k]
    
    def get_recommendations(
        self, 
        user_query: str, 
        context: Optional[str] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """LLMと組み合わせた高度なレコメンド"""
        try:
            # まず類似商品を検索
            search_results = self.search_products(user_query, top_k=top_k * 2)
            
            if not search_results:
                return []
            
            # LLMにコンテキストを与えてレコメンドを改善
            recommendation_prompt = self._build_recommendation_prompt(
                user_query, search_results, context
            )
            
            # LLMで結果を再ランキング
            refined_results = self._refine_with_llm(
                recommendation_prompt, search_results, top_k
            )
            
            return refined_results
            
        except Exception as e:
            logger.error(f"レコメンドエラー: {e}")
            return search_results[:top_k]  # フォールバック
    
    def _build_recommendation_prompt(
        self, 
        user_query: str, 
        search_results: List[SearchResult],
        context: Optional[str] = None
    ) -> str:
        """レコメンド用のプロンプトを構築"""
        prompt = f"""あなたは薬局の専門家です。以下のユーザーの要求に最適な商品をレコメンドしてください。

ユーザーの要求: {user_query}
"""
        
        if context:
            prompt += f"\n追加コンテキスト: {context}\n"
        
        prompt += "\n検索結果:\n"
        for i, result in enumerate(search_results[:10], 1):
            prompt += f"""
{i}. 商品名: {result.product_name}
   価格: {result.price}
   カテゴリ: {result.category}
   説明: {result.description[:200]}...
   類似度: {result.similarity_score:.3f}
"""
        
        prompt += """
上記の検索結果から、ユーザーの要求に最も適した商品を順位付けして推薦してください。
各商品の推薦理由も簡潔に説明してください。
"""
        
        return prompt
    
    def _refine_with_llm(
        self, 
        prompt: str, 
        search_results: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """LLMを使用して検索結果を改善"""
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "あなたは薬局の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # LLMの応答を解析して結果を再順序付け
            llm_response = response.choices[0].message.content
            logger.info(f"LLM推薦: {llm_response[:200]}...")
            
            # 上位の結果を返す
            return search_results[:top_k]
            
        except Exception as e:
            logger.error(f"LLM処理エラー: {e}")
            return search_results[:top_k]
    
    def load_products_from_csv(self, filepath: str):
        """CSVファイルから商品データを読み込み（BOM対応）"""
        try:
            products_data = []
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:  # BOM対応のためutf-8-sig
                reader = csv.DictReader(f)
                for row in reader:
                    # CSVの行データをproducts_dataリストに追加
                    products_data.append(row)
            
            logger.info(f"{len(products_data)}件の商品データをCSVから読み込みました")
            self.add_products(products_data)
            
        except FileNotFoundError:
            logger.error(f"CSVファイルが見つかりません: {filepath}")
        except Exception as e:
            logger.error(f"CSV商品データ読み込みエラー: {e}")
    
    def load_products_from_json(self, filepath: str):
        """JSONファイルから商品データを読み込み"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            
            logger.info(f"{len(products_data)}件の商品データを読み込みました")
            self.add_products(products_data)
            
        except FileNotFoundError:
            logger.error(f"ファイルが見つかりません: {filepath}")
        except json.JSONDecodeError:
            logger.error(f"JSONファイルの形式が不正です: {filepath}")
        except Exception as e:
            logger.error(f"商品データ読み込みエラー: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """コレクション情報を取得"""
        try:
            count = self.index.ntotal if self.index else 0
            return {
                "collection_name": "faiss_products",
                "total_products": count,
                "status": "ready" if count > 0 else "empty"
            }
        except Exception as e:
            logger.error(f"コレクション情報取得エラー: {e}")
            return {
                "collection_name": "faiss_products",
                "total_products": 0,
                "status": "error",
                "error": str(e)
            }

def main():
    """メイン実行関数"""
    rag_system = FAISSRAGSystem()
    
    # コレクション情報を表示
    info = rag_system.get_collection_info()
    print(f"コレクション情報: {info}")
    
    # CSVファイルを優先的に読み込み
    csv_file = "./data/product_recommend.csv"
    json_file = "./data/products.json"
    
    if os.path.exists(csv_file):
        print(f"CSVファイルから商品データを読み込み中: {csv_file}")
        rag_system.load_products_from_csv(csv_file)
    elif os.path.exists(json_file):
        print(f"JSONファイルから商品データを読み込み中: {json_file}")
        rag_system.load_products_from_json(json_file)
    else:
        logger.warning(f"商品データファイルが見つかりません")
        logger.warning(f"CSVファイル: {csv_file}")
        logger.warning(f"JSONファイル: {json_file}")
        logger.info("まずスクレイパーを実行して商品データを取得してください")

if __name__ == "__main__":
    main()