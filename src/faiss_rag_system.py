# -*- coding: utf-8 -*-
"""
FAISS RAGシステム
"""
import json
import os
import pickle
import csv
import sys
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass

try:
    import faiss
    import numpy as np
    from openai import OpenAI
    
    # OpenAIバージョン確認
    import openai
    OPENAI_VERSION = getattr(openai, '__version__', 'unknown')
    print(f"OpenAI version: {OPENAI_VERSION}")
    
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    OPENAI_VERSION = None
    print(f"必要なライブラリがありません: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """検索結果データクラス"""
    product_name: str
    url: str
    price: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    similarity_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class FAISSRAGSystem:
    """FAISS RAGシステム"""
    
    def __init__(self):
        """初期化"""
        if not DEPENDENCIES_AVAILABLE:
            raise RuntimeError("依存関係がありません")
            
        logger.info("=== FAISSRAGSystem初期化開始 ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"OpenAI version: {OPENAI_VERSION}")
        
        # 環境変数の確認
        logger.info("環境変数確認:")
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            value = os.getenv(var)
            if value:
                logger.info(f"  {var}: {value}")
            else:
                logger.info(f"  {var}: (未設定)")
        
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEYが必要です。環境変数またはStreamlit Secretsに設定してください。")
        
        # APIキーの妥当性チェック
        if len(openai_api_key) < 10:
            raise ValueError("OPENAI_API_KEYが短すぎます。正しいAPIキーを設定してください。")
        
        logger.info(f"OpenAI APIキー確認: {'*' * (len(openai_api_key) - 8) + openai_api_key[-8:]}")
        logger.info(f"OpenAI library version: {OPENAI_VERSION}")
        
        # プロキシと環境変数クリア
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        cleared_count = 0
        for key in proxy_vars:
            if key in os.environ:
                old_value = os.environ[key]
                del os.environ[key]
                logger.info(f"削除した環境変数: {key}={old_value}")
                cleared_count += 1
        
        if cleared_count > 0:
            logger.info(f"合計 {cleared_count} 個のプロキシ関連環境変数を削除しました")
        else:
            logger.info("削除対象のプロキシ環境変数はありませんでした")
        
        # OpenAIクライアント初期化（段階的アプローチ）
        self.client = None
        init_success = False
        
        logger.info("=== OpenAIクライアント初期化開始 ===")
        
        # 方法1: 最もシンプルな初期化（推奨）
        try:
            logger.info("試行 1/3: 基本的なOpenAIクライアント作成...")
            # OpenAI 1.x系での標準的な初期化
            self.client = OpenAI(api_key=openai_api_key)
            logger.info("クライアント作成完了、接続テスト実行中...")
            
            # 簡単な接続テスト
            test_response = self.client.models.list()
            if test_response and hasattr(test_response, 'data'):
                model_count = len(test_response.data)
                logger.info(f"接続テスト成功: {model_count} モデル確認")
                init_success = True
                logger.info("✅ OpenAIクライアント初期化成功（基本方式）")
            else:
                logger.warning("接続テストでモデル一覧の取得に失敗")
        except Exception as e1:
            logger.warning(f"❌ 基本方式初期化失敗: {type(e1).__name__}: {str(e1)}")
            
            # 方法2: 明示的な設定での初期化
            try:
                logger.info("試行 2/3: 明示的設定でのOpenAIクライアント作成...")
                # より明示的な設定
                self.client = OpenAI(
                    api_key=openai_api_key,
                    base_url="https://api.openai.com/v1",
                    timeout=60.0,
                    max_retries=3
                )
                logger.info("クライアント作成完了、接続テスト実行中...")
                
                # 接続テスト
                test_response = self.client.models.list()
                if test_response and hasattr(test_response, 'data'):
                    model_count = len(test_response.data)
                    logger.info(f"接続テスト成功: {model_count} モデル確認")
                    init_success = True
                    logger.info("✅ OpenAIクライアント初期化成功（明示設定方式）")
                else:
                    logger.warning("接続テストでモデル一覧の取得に失敗")
            except Exception as e2:
                logger.warning(f"❌ 明示設定方式初期化失敗: {type(e2).__name__}: {str(e2)}")
                
                # 方法3: 最小設定での初期化
                try:
                    logger.info("試行 3/3: 最小設定でのOpenAIクライアント作成...")
                    
                    # 最小限の設定で再試行
                    self.client = OpenAI(
                        api_key=openai_api_key,
                        timeout=30.0
                    )
                    logger.info("クライアント作成完了、簡易テスト実行中...")
                    
                    # 簡易接続テスト（モデル一覧取得をスキップ）
                    try:
                        # より軽い処理でテスト
                        test_response = self.client.models.list()
                        if test_response and hasattr(test_response, 'data'):
                            model_count = len(test_response.data)
                            logger.info(f"接続テスト成功: {model_count} モデル確認")
                        else:
                            logger.info("モデル一覧は取得できませんが、クライアントは作成されました")
                        
                        init_success = True
                        logger.info("✅ OpenAIクライアント初期化成功（最小設定方式）")
                        
                    except Exception as test_e:
                        logger.warning(f"接続テストは失敗しましたが、クライアント作成は成功: {test_e}")
                        # テストに失敗してもクライアントは作成されているので続行
                        init_success = True
                        logger.info("✅ OpenAIクライアント初期化成功（テスト無し）")
                        
                except Exception as e3:
                    logger.error(f"❌ 全ての初期化方法が失敗:")
                    logger.error(f"  方法1 (基本): {type(e1).__name__}: {str(e1)}")
                    logger.error(f"  方法2 (明示): {type(e2).__name__}: {str(e2)}")
                    logger.error(f"  方法3 (最小): {type(e3).__name__}: {str(e3)}")
                    
                    # 最終的なエラーメッセージ
                    final_error = f"OpenAI接続に失敗しました。"
                    if "proxies" in str(e1).lower() or "proxies" in str(e2).lower() or "proxies" in str(e3).lower():
                        final_error += " プロキシ設定に問題があります。"
                    elif "api_key" in str(e1).lower() or "api_key" in str(e2).lower() or "api_key" in str(e3).lower():
                        final_error += " APIキーを確認してください。"
                    else:
                        final_error += " ネットワーク接続を確認してください。"
                    
                    raise RuntimeError(final_error)
        
        if not init_success or self.client is None:
            logger.error("OpenAIクライアントの初期化に完全に失敗しました")
            raise RuntimeError("OpenAIクライアントの初期化に失敗しました。APIキーまたはネットワーク接続を確認してください。")
        
        logger.info("=== OpenAIクライアント初期化完了 ===")
        logger.info(f"クライアント状態: {type(self.client).__name__}")
        
        # FAISS設定
        self.index = None
        self.metadata_list = []
        self.documents = []
        self.dimension = 1536
        
        # パス設定
        self.data_dir = "./data"
        self.csv_file = os.path.join(self.data_dir, "product_recommend.csv")
        self.index_file = os.path.join(self.data_dir, "faiss_index.bin")
        self.metadata_file = os.path.join(self.data_dir, "metadata.pkl")
        self.documents_file = os.path.join(self.data_dir, "documents.pkl")
        
        logger.info("=== FAISSRAGSystem初期化完了 ===")
        
        self._initialize()

    def _initialize(self):
        """初期化"""
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            self._load_index()
        else:
            self._build_index()

    def _load_csv_data(self) -> List[Dict]:
        """CSV読み込み"""
        products = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    products.append(row)
            return products
        except Exception as e:
            logger.error(f"CSV読み込みエラー: {e}")
            return []

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """エンベディング取得"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"エンベディングエラー: {e}")
            return None

    def search_products(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """商品検索"""
        if not self.index or not self.metadata_list:
            return []

        try:
            query_embedding = self._get_embedding(query)
            if query_embedding is None:
                return []

            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)
            scores, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.metadata_list):
                    metadata = self.metadata_list[idx]
                    result = SearchResult(
                        product_name=metadata['product_name'],
                        category=metadata['category'],
                        description=metadata['description'],
                        url=metadata['url'],
                        similarity_score=float(score)
                    )
                    results.append(result)
            return results
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []

    def _build_index(self):
        """インデックス構築"""
        products = self._load_csv_data()
        if not products:
            return

        self.documents = []
        self.metadata_list = []
        embeddings = []
        
        for product in products:
            doc_parts = []
            if product.get('商品名'):
                doc_parts.append(f"商品名: {product['商品名']}")
            if product.get('カテゴリ名'):
                doc_parts.append(f"カテゴリ: {product['カテゴリ名']}")
            if product.get('効果'):
                doc_parts.append(f"効果: {product['効果']}")
            
            doc = "\n".join(doc_parts)
            embedding = self._get_embedding(doc)
            
            if embedding is not None:
                self.documents.append(doc)
                metadata = {
                    'product_name': product.get('商品名', ''),
                    'category': product.get('カテゴリ名', ''),
                    'description': product.get('説明文', ''),
                    'url': product.get('商品URL', ''),
                }
                self.metadata_list.append(metadata)
                embeddings.append(embedding)

        if embeddings:
            embeddings_matrix = np.vstack(embeddings)
            self.index = faiss.IndexFlatIP(self.dimension)
            faiss.normalize_L2(embeddings_matrix)
            self.index.add(embeddings_matrix)
            self._save_index()

    def _save_index(self):
        """インデックス保存"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            faiss.write_index(self.index, self.index_file)
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata_list, f)
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
        except Exception as e:
            logger.error(f"保存エラー: {e}")

    def _load_index(self):
        """インデックス読み込み"""
        try:
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_file, 'rb') as f:
                self.metadata_list = pickle.load(f)
            with open(self.documents_file, 'rb') as f:
                self.documents = pickle.load(f)
        except Exception as e:
            logger.error(f"読み込みエラー: {e}")