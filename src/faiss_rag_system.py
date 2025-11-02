"""
FAISS ベースRAGシステム - お薬通販部商品レコメンドLLMアプリ（改良版）
キーワード完全一致優先の検索システム
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
    category: Optional[str] = None
    similarity_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class FAISSRAGSystem:
    """FAISSベースのRAGシステム（改良版）"""
    
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
        
        # データファイルパス
        self.data_dir = "./data"
        self.csv_file = os.path.join(self.data_dir, "product_recommend.csv")
        self.index_file = os.path.join(self.data_dir, "faiss_index.bin")
        self.metadata_file = os.path.join(self.data_dir, "metadata.pkl")
        self.documents_file = os.path.join(self.data_dir, "documents.pkl")

    def search_products(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """キーワードベース検索（全フィールド対象の正確な検索）"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("インデックスが空です")
                return []
            
            query = query.strip()
            logger.info(f"検索開始: '{query}'")
            
            # 1. キーワード完全一致検索を実行
            exact_results = self._keyword_exact_search(query, top_k)
            
            # 2. 完全一致で結果がある場合はそれを返す
            if exact_results:
                logger.info(f"完全一致検索で{len(exact_results)}件の結果を取得")
                return exact_results
            
            # 3. 完全一致で結果がない場合、ベクトル検索にフォールバック
            logger.info("完全一致なし。ベクトル検索にフォールバック")
            vector_results = self._vector_search(query, top_k)
            
            logger.info(f"検索完了: {len(vector_results)}件の結果")
            return vector_results
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []
    
    def _keyword_exact_search(self, query: str, top_k: int) -> List[SearchResult]:
        """キーワード完全一致検索（全フィールド対象）"""
        results = []
        query_lower = query.lower().strip()
        logger.info(f"キーワード完全一致検索: '{query_lower}'")
        logger.info(f"検索対象データ数: {len(self.metadata_list)}")
        
        if not self.metadata_list:
            logger.warning("メタデータリストが空です")
            return results
        
        for i, metadata in enumerate(self.metadata_list):
            # 検索対象フィールド
            search_fields = {
                'category': metadata.get('category', ''),           # カテゴリ名
                'subcategory': metadata.get('subcategory', ''),     # サブカテゴリ名  
                'name': metadata.get('name', ''),                   # 商品名
                'effect': metadata.get('effect', ''),               # 効果
                'ingredient': metadata.get('ingredient', ''),       # 有効成分
                'description': metadata.get('description', '')      # 説明文
            }
            
            # 各フィールドでの一致度をチェック
            match_score = 0
            match_fields = []
            
            for field_name, field_value in search_fields.items():
                if not field_value:
                    continue
                    
                field_lower = field_value.lower().strip()
                
                # 1. 完全一致（最高スコア）
                if query_lower == field_lower:
                    match_score = 1.0
                    match_fields = [field_name]
                    logger.info(f"完全一致: {metadata.get('name', '')} [{field_name}]")
                    break
                
                # 2. 単語として含まれている（高スコア）
                elif self._is_word_match(query_lower, field_lower):
                    current_score = self._get_field_score(field_name)
                    if current_score > match_score:
                        match_score = current_score
                        match_fields = [field_name]
                    elif current_score == match_score:
                        match_fields.append(field_name)
                    logger.info(f"単語一致: {metadata.get('name', '')} [{field_name}] スコア:{current_score}")
                
                # 3. 部分一致（特に有効成分や商品名で重要）
                elif query_lower in field_lower and field_name in ['ingredient', 'name']:
                    current_score = self._get_field_score(field_name) * 0.8  # 少し低めのスコア
                    if current_score > match_score:
                        match_score = current_score
                        match_fields = [field_name]
                    logger.info(f"部分一致: {metadata.get('name', '')} [{field_name}] スコア:{current_score}")
            
            # マッチした場合のみ結果に追加
            if match_score > 0:
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=match_score,
                    metadata=metadata
                )
                results.append(search_result)
        
        # スコア順でソート（高スコア順）
        results.sort(key=lambda x: (-x.similarity_score, x.metadata.get('csv_order', 999)))
        
        logger.info(f"キーワード検索結果: {len(results)}件")
        return results[:top_k]
    
    def _is_word_match(self, query: str, text: str) -> bool:
        """クエリがテキスト内に単語として含まれているかチェック"""
        import re
        
        # 1. 単純な含有チェック
        if query in text:
            # 2. 区切り文字で分割して単語一致をチェック
            words = re.split(r'[、，,\s・\+\-\(\)（）]+', text)
            words = [word.strip() for word in words if word.strip()]
            
            # 完全一致する単語があるかチェック
            return query in [word.lower() for word in words]
        
        return False
    
    def _get_field_score(self, field_name: str) -> float:
        """フィールドの重要度に応じたスコア"""
        field_scores = {
            'ingredient': 0.95,    # 有効成分（最重要）
            'name': 0.90,          # 商品名
            'effect': 0.85,        # 効果
            'category': 0.80,      # カテゴリ名
            'subcategory': 0.75,   # サブカテゴリ名
            'description': 0.70    # 説明文
        }
        return field_scores.get(field_name, 0.5)
    
    def _vector_search(self, query: str, top_k: int) -> List[SearchResult]:
        """ベクトル検索（フォールバック用）"""
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
            scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
            
            # 結果を整形
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 無効なインデックス
                    continue
                    
                metadata = self.metadata_list[idx]
                
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=float(score),
                    metadata=metadata
                )
                results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"ベクトル検索エラー: {e}")
            return []

    def get_embedding(self, text: str) -> List[float]:
        """テキストの埋め込みベクトルを取得"""
        try:
            response = self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"埋め込み取得エラー: {e}")
            return []

    def load_or_create_index(self):
        """インデックスをロードまたは作成"""
        if self._index_exists():
            logger.info("既存のインデックスをロード中...")
            self._load_index()
        else:
            logger.info("新しいインデックスを作成中...")
            self._create_index_from_csv()

    def _index_exists(self) -> bool:
        """インデックスファイルが存在するかチェック"""
        return (os.path.exists(self.index_file) and 
                os.path.exists(self.metadata_file) and 
                os.path.exists(self.documents_file))

    def _load_index(self):
        """既存のインデックスをロード"""
        try:
            # FAISSインデックスをロード
            self.index = faiss.read_index(self.index_file)
            
            # メタデータをロード
            with open(self.metadata_file, 'rb') as f:
                self.metadata_list = pickle.load(f)
            
            # ドキュメントをロード
            with open(self.documents_file, 'rb') as f:
                self.documents = pickle.load(f)
            
            logger.info(f"インデックスロード完了: {self.index.ntotal}件のドキュメント")
        except Exception as e:
            logger.error(f"インデックスロードエラー: {e}")
            raise

    def _create_index_from_csv(self):
        """CSVファイルからインデックスを作成"""
        try:
            if not os.path.exists(self.csv_file):
                logger.error(f"CSVファイルが見つかりません: {self.csv_file}")
                raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_file}")
            
            # CSVデータを読み込み
            products = []
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    # 各商品の情報をまとめる
                    product_text = f"""
                    カテゴリ: {row.get('カテゴリ名', '')}
                    サブカテゴリ: {row.get('サブカテゴリ名', '')}
                    商品名: {row.get('商品名', '')}
                    効果: {row.get('効果', '')}
                    有効成分: {row.get('有効成分', '')}
                    説明: {row.get('説明文', '')}
                    """
                    
                    # メタデータを準備
                    metadata = {
                        'category': row.get('カテゴリ名', ''),
                        'subcategory': row.get('サブカテゴリ名', ''),
                        'name': row.get('商品名', ''),
                        'effect': row.get('効果', ''),
                        'ingredient': row.get('有効成分', ''),
                        'description': row.get('説明文', ''),
                        'url': row.get('商品URL', ''),
                        'price': '',  # 価格情報は含めない
                        'csv_order': i
                    }
                    
                    products.append((product_text.strip(), metadata))
            
            if not products:
                logger.error("CSVからデータを読み込めませんでした")
                raise ValueError("CSVからデータを読み込めませんでした")
            
            logger.info(f"{len(products)}件の商品データを読み込みました")
            
            # 埋め込みベクトルを生成
            embeddings = []
            self.metadata_list = []
            self.documents = []
            
            for i, (text, metadata) in enumerate(products):
                logger.info(f"埋め込み生成中: {i+1}/{len(products)} - {metadata['name']}")
                
                embedding = self.get_embedding(text)
                if embedding:
                    embeddings.append(embedding)
                    self.metadata_list.append(metadata)
                    self.documents.append(text)
                else:
                    logger.warning(f"埋め込み生成失敗: {metadata['name']}")
            
            if not embeddings:
                logger.error("有効な埋め込みが生成されませんでした")
                raise ValueError("有効な埋め込みが生成されませんでした")
            
            # FAISSインデックスを作成
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)
            
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings_array)
            
            # インデックスを保存
            self._save_index()
            
            logger.info(f"インデックス作成完了: {self.index.ntotal}件のドキュメント")
            
        except Exception as e:
            logger.error(f"インデックス作成エラー: {e}")
            raise

    def _save_index(self):
        """インデックスを保存"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            
            # FAISSインデックスを保存
            faiss.write_index(self.index, self.index_file)
            
            # メタデータを保存
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata_list, f)
            
            # ドキュメントを保存
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info("インデックス保存完了")
            
        except Exception as e:
            logger.error(f"インデックス保存エラー: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """コレクション情報を取得（互換性のため）"""
        try:
            if self.index is None:
                return {
                    "status": "not_initialized",
                    "document_count": 0,
                    "index_exists": False
                }
            
            return {
                "status": "ready",
                "document_count": self.index.ntotal if self.index else 0,
                "index_exists": self.index is not None,
                "metadata_count": len(self.metadata_list),
                "index_dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"コレクション情報取得エラー: {e}")
            return {
                "status": "error",
                "error": str(e),
                "document_count": 0,
                "index_exists": False
            }

    def get_recommendations(self, query: str, context: str = "", top_k: int = 5) -> List[SearchResult]:
        """レコメンデーション（search_productsのエイリアス）"""
        # contextがある場合はクエリに追加
        if context:
            enhanced_query = f"{query} {context}"
        else:
            enhanced_query = query
        
        return self.search_products(enhanced_query, top_k)