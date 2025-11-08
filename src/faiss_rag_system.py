# -*- coding: utf-8 -*-
"""
FAISS RAGシステム
"""
import json
import os
import pickle
import csv
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass

try:
    import faiss
    import numpy as np
    from openai import OpenAI
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
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
            
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEYが必要")
        
        # プロキシクリア
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                del os.environ[key]
        
        # OpenAIクライアント初期化（複数の方法を試行）
        self.client = None
        
        # 方法1: 基本的な初期化
        try:
            self.client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAIクライアント初期化成功（基本）")
        except Exception as e1:
            logger.warning(f"基本初期化失敗: {e1}")
            
            # 方法2: タイムアウト付き
            try:
                self.client = OpenAI(api_key=openai_api_key, timeout=30.0)
                logger.info("OpenAIクライアント初期化成功（タイムアウト付き）")
            except Exception as e2:
                logger.warning(f"タイムアウト付き初期化失敗: {e2}")
                
                # 方法3: 最小限の設定
                try:
                    import openai
                    openai.api_key = openai_api_key
                    self.client = OpenAI(api_key=openai_api_key)
                    logger.info("OpenAIクライアント初期化成功（最小限）")
                except Exception as e3:
                    logger.error(f"全ての初期化方法が失敗: {e1}, {e2}, {e3}")
                    raise RuntimeError(f"OpenAIクライアント初期化失敗: {e3}")
        
        if self.client is None:
            raise RuntimeError("OpenAIクライアントの初期化に失敗しました")
        
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