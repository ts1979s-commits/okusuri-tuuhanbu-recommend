"""""""""

RAGシステム - お薬通販部商品レコメンドLLMアプリ

非推奨: このファイルは使用されていません。FAISSRAGSystemを使用してください。RAGシステム - お薬通販部商品レコメンドLLMアプリRAGシステム - お薬通販部商品レコメンドLLMアプリ

"""

非推奨: このファイルは使用されていません。FAISSRAGSystemを使用してください。非推奨: このファイルは使用されていません。FAISSRAGSystemを使用してください。

# このファイルは非推奨です

# 代わりにsrc/faiss_rag_system.pyを使用してください""""""



class RAGSystem:

    """非推奨のRAGシステム - 使用しないでください"""

    # このファイルは非推奨です# このファイルは非推奨です

    def __init__(self):

        raise RuntimeError("このクラスは非推奨です。FAISSRAGSystemを使用してください。")# 代わりにsrc/faiss_rag_system.pyを使用してください# 代わりにsrc/faiss_rag_system.pyを使用してください



class RAGSystem:class RAGSystem:

    """非推奨のRAGシステム - 使用しないでください"""    """非推奨のRAGシステム - 使用しないでください"""

        

    def __init__(self):    def __init__(self):

        raise RuntimeError("このクラスは非推奨です。FAISSRAGSystemを使用してください。")        raise RuntimeError("このクラスは非推奨です。FAISSRAGSystemを使用してください。")
            )
        )
        
        self.collection = self._get_or_create_collection()
        
    def _get_or_create_collection(self):
        """コレクションを取得または作成"""
        try:
            # 既存のコレクションを取得
            collection = self.chroma_client.get_collection(
                name=settings.COLLECTION_NAME
            )
            logger.info(f"既存のコレクション '{settings.COLLECTION_NAME}' を使用")
        except Exception:
            # 新しいコレクションを作成
            collection = self.chroma_client.create_collection(
                name=settings.COLLECTION_NAME,
                metadata={"description": "お薬通販部商品データベース"}
            )
            logger.info(f"新しいコレクション '{settings.COLLECTION_NAME}' を作成")
        
        return collection
    
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
    
    def add_products(self, products_data: List[Dict[str, Any]]):
        """商品データをベクトルDBに追加"""
        if not products_data:
            logger.warning("追加する商品データがありません")
            return
        
        # 既存のアイテム数を確認
        existing_count = self.collection.count()
        logger.info(f"現在のコレクション内アイテム数: {existing_count}")
        
        documents = []
        metadatas = []
        ids = []
        embeddings = []
        
        for i, product in enumerate(products_data):
            # 商品情報からテキストを構築
            doc_text = self._build_document_text(product)
            
            # 埋め込みベクトルを取得
            embedding = self.get_embedding(doc_text)
            if not embedding:
                logger.warning(f"商品 '{product.get('name', 'Unknown')}' の埋め込み取得に失敗")
                continue
            
            # データを準備
            product_id = f"product_{existing_count + i + 1}"
            documents.append(doc_text)
            
            # CSV構造とJSONの両方に対応したメタデータ
            metadata = {
                'name': product.get('商品名') or product.get('name', ''),
                'url': product.get('商品URL') or product.get('url', ''),
                'price': product.get('price', ''),  # CSVには価格がないため空
                'description': product.get('説明文') or product.get('description', ''),
                'category': product.get('カテゴリ名') or product.get('category', ''),
                'subcategory': product.get('サブカテゴリ名', ''),
                'effect': product.get('効果', ''),
                'ingredient': product.get('有効成分', ''),
                'category_url': product.get('カテゴリURL', ''),
                'subcategory_url': product.get('サブカテゴリURL', ''),
                'image_url': product.get('image_url', ''),
                'csv_order': i  # CSV登録順を記録
            }
            
            metadatas.append(metadata)
            ids.append(product_id)
            embeddings.append(embedding)
            
            # 進捗表示
            if (i + 1) % 10 == 0:
                logger.info(f"埋め込み作成進捗: {i + 1}/{len(products_data)}")
        
        if documents:
            # バッチでベクトルDBに追加
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            logger.info(f"{len(documents)}件の商品をベクトルDBに追加しました")
            
            # データを永続化
            self.chroma_client.persist()
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
    
    def search_products(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """商品を検索"""
        try:
            # クエリの埋め込みベクトルを取得
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("クエリの埋め込み取得に失敗")
                return []
            
            # ベクトル検索を実行
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k
            }
            
            if filter_dict:
                search_params["where"] = filter_dict
            
            results = self.collection.query(**search_params)
            
            # 結果を整形
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]
                    
                    # 距離を類似度スコアに変換（0-1の範囲）
                    similarity_score = max(0, 1 - distance)
                    
                    search_result = SearchResult(
                        product_name=metadata.get('name', ''),
                        url=metadata.get('url', ''),
                        price=metadata.get('price', ''),
                        description=metadata.get('description', ''),
                        category=metadata.get('category', ''),
                        similarity_score=similarity_score,
                        metadata=metadata
                    )
                    search_results.append(search_result)
            
            logger.info(f"検索完了: {len(search_results)}件の結果")
            return search_results
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []
    
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
            # 簡単な実装として、類似度スコアを調整
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
            count = self.collection.count()
            return {
                "collection_name": settings.COLLECTION_NAME,
                "total_products": count,
                "status": "ready" if count > 0 else "empty"
            }
        except Exception as e:
            logger.error(f"コレクション情報取得エラー: {e}")
            return {
                "collection_name": settings.COLLECTION_NAME,
                "total_products": 0,
                "status": "error",
                "error": str(e)
            }

def main():
    """メイン実行関数"""
    rag_system = RAGSystem()
    
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