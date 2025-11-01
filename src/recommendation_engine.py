"""
商品レコメンドエンジン - お薬通販部商品レコメンドLLMアプリ
ユーザークエリに基づいたインテリジェントな商品レコメンド機能
"""
from typing import List, Dict, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import re

from src.faiss_rag_system import FAISSRAGSystem, SearchResult
from config.settings import get_settings

settings = get_settings()

# ログ設定
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

class QueryType(Enum):
    """クエリタイプの分類"""
    SYMPTOM = "symptom"  # 症状関連
    PRODUCT_NAME = "product_name"  # 商品名検索
    CATEGORY = "category"  # カテゴリ検索
    INGREDIENT = "ingredient"  # 成分検索
    GENERAL = "general"  # 一般的な質問

@dataclass
class RecommendationContext:
    """レコメンドコンテキスト"""
    user_query: str
    query_type: QueryType
    extracted_keywords: List[str]
    user_preferences: Optional[Dict[str, Any]] = None
    previous_purchases: Optional[List[str]] = None

class QueryAnalyzer:
    """クエリ解析クラス"""
    
    def __init__(self):
        # 症状関連キーワード
        self.symptom_keywords = [
            "痛い", "痛み", "頭痛", "腹痛", "風邪", "熱", "咳", "鼻水",
            "下痢", "便秘", "疲れ", "だるい", "眠れない", "不眠",
            "ストレス", "肩こり", "腰痛", "めまい", "吐き気"
        ]
        
        # カテゴリキーワード
        self.category_keywords = {
            "風邪薬": ["風邪", "かぜ", "感冒"],
            "解熱鎮痛剤": ["頭痛", "熱", "痛み", "解熱", "鎮痛"],
            "胃腸薬": ["胃", "腹痛", "下痢", "便秘", "消化"],
            "目薬": ["目", "眼", "ドライアイ"],
            "湿布": ["湿布", "肩こり", "腰痛", "筋肉痛"],
            "ビタミン": ["ビタミン", "栄養", "サプリ"],
            "漢方": ["漢方", "和漢"]
        }
        
        # 成分キーワード
        self.ingredient_keywords = [
            "アセトアミノフェン", "イブプロフェン", "ロキソプロフェン",
            "アスピリン", "カフェイン", "ビタミンC", "ビタミンB"
        ]
    
    def analyze_query(self, query: str) -> RecommendationContext:
        """クエリを解析してコンテキストを作成"""
        query_lower = query.lower()
        keywords = self._extract_keywords(query)
        query_type = self._classify_query_type(query_lower, keywords)
        
        return RecommendationContext(
            user_query=query,
            query_type=query_type,
            extracted_keywords=keywords
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """クエリからキーワードを抽出"""
        keywords = []
        query_lower = query.lower()
        
        # 症状キーワードを検索
        for symptom in self.symptom_keywords:
            if symptom in query_lower:
                keywords.append(symptom)
        
        # カテゴリキーワードを検索
        for category, category_keywords in self.category_keywords.items():
            for keyword in category_keywords:
                if keyword in query_lower:
                    keywords.append(category)
                    break
        
        # 成分キーワードを検索
        for ingredient in self.ingredient_keywords:
            if ingredient.lower() in query_lower:
                keywords.append(ingredient)
        
        return list(set(keywords))  # 重複を除去
    
    def _classify_query_type(self, query_lower: str, keywords: List[str]) -> QueryType:
        """クエリタイプを分類"""
        # 症状関連の判定
        symptom_matches = any(symptom in query_lower for symptom in self.symptom_keywords)
        if symptom_matches:
            return QueryType.SYMPTOM
        
        # 商品名の判定（具体的な商品名パターン）
        product_patterns = [r"[ァ-ヶー]+[A-Za-z]*", r"[A-Za-z]+\d*"]
        for pattern in product_patterns:
            if re.search(pattern, query_lower):
                return QueryType.PRODUCT_NAME
        
        # カテゴリの判定
        category_matches = any(cat in keywords for cat in self.category_keywords.keys())
        if category_matches:
            return QueryType.CATEGORY
        
        # 成分の判定
        ingredient_matches = any(ing in keywords for ing in self.ingredient_keywords)
        if ingredient_matches:
            return QueryType.INGREDIENT
        
        return QueryType.GENERAL

class RecommendationEngine:
    """メインのレコメンドエンジン"""
    
    def __init__(self):
        self.rag_system = FAISSRAGSystem()
        self.query_analyzer = QueryAnalyzer()
        
    def recommend_products(
        self, 
        user_query: str,
        max_results: int = 5,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[SearchResult], RecommendationContext]:
        """商品をレコメンド"""
        try:
            # クエリを解析
            context = self.query_analyzer.analyze_query(user_query)
            logger.info(f"クエリ解析結果: タイプ={context.query_type.value}, キーワード={context.extracted_keywords}")
            
            # クエリタイプに応じた検索戦略を選択
            search_results = self._execute_search_strategy(context, max_results)
            
            # 結果の後処理とフィルタリング
            filtered_results = self._post_process_results(search_results, context)
            
            logger.info(f"レコメンド完了: {len(filtered_results)}件の結果")
            return filtered_results[:max_results], context
            
        except Exception as e:
            logger.error(f"レコメンドエラー: {e}")
            return [], context
    
    def _execute_search_strategy(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """クエリタイプに応じた検索戦略を実行"""
        if context.query_type == QueryType.SYMPTOM:
            return self._search_by_symptom(context, max_results)
        elif context.query_type == QueryType.PRODUCT_NAME:
            return self._search_by_product_name(context, max_results)
        elif context.query_type == QueryType.CATEGORY:
            return self._search_by_category(context, max_results)
        elif context.query_type == QueryType.INGREDIENT:
            return self._search_by_ingredient(context, max_results)
        else:
            return self._general_search(context, max_results)
    
    def _search_by_symptom(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """症状ベースの検索"""
        # 症状に対応する商品カテゴリを推定
        enhanced_query = f"{context.user_query} 薬 治療"
        
        return self.rag_system.get_recommendations(
            enhanced_query,
            context="症状に効果的な医薬品を探しています",
            top_k=max_results
        )
    
    def _search_by_product_name(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """商品名ベースの検索"""
        return self.rag_system.search_products(
            context.user_query,
            top_k=max_results
        )
    
    def _search_by_category(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """カテゴリベースの検索"""
        # FAISS版では単純な検索を実行（フィルタリング機能は後で実装）
        return self.rag_system.search_products(
            context.user_query,
            top_k=max_results
        )
    
    def _search_by_ingredient(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """成分ベースの検索"""
        enhanced_query = f"{context.user_query} 成分 配合"
        
        return self.rag_system.search_products(
            enhanced_query,
            top_k=max_results
        )
    
    def _general_search(
        self, 
        context: RecommendationContext, 
        max_results: int
    ) -> List[SearchResult]:
        """一般的な検索"""
        return self.rag_system.search_products(
            context.user_query,
            top_k=max_results
        )
    
    def _post_process_results(
        self, 
        results: List[SearchResult], 
        context: RecommendationContext
    ) -> List[SearchResult]:
        """結果の後処理"""
        if not results:
            return results
        
        # 重複除去
        seen_products = set()
        filtered_results = []
        
        for result in results:
            if result.product_name not in seen_products:
                seen_products.add(result.product_name)
                filtered_results.append(result)
        
        # スコア調整
        adjusted_results = self._adjust_scores(filtered_results, context)
        
        # スコア順でソート
        adjusted_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return adjusted_results
    
    def _adjust_scores(
        self, 
        results: List[SearchResult], 
        context: RecommendationContext
    ) -> List[SearchResult]:
        """コンテキストに基づいてスコアを調整"""
        for result in results:
            # キーワードマッチによるブースト
            for keyword in context.extracted_keywords:
                if keyword.lower() in result.product_name.lower():
                    result.similarity_score *= 1.2
                if keyword.lower() in (result.description or "").lower():
                    result.similarity_score *= 1.1
                if keyword.lower() in (result.category or "").lower():
                    result.similarity_score *= 1.15
            
            # スコアを0-1の範囲に正規化
            result.similarity_score = min(1.0, result.similarity_score)
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状態を取得"""
        rag_info = self.rag_system.get_collection_info()
        
        return {
            "recommendation_engine": "ready",
            "rag_system": rag_info,
            "supported_query_types": [qt.value for qt in QueryType],
            "features": [
                "症状ベース検索",
                "商品名検索", 
                "カテゴリ検索",
                "成分検索",
                "インテリジェント再ランキング"
            ]
        }

def main():
    """メイン実行関数"""
    engine = RecommendationEngine()
    
    # システム状態を表示
    status = engine.get_system_status()
    print("=== レコメンドエンジン状態 ===")
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # テスト用クエリ
    test_queries = [
        "頭痛がひどいので何か良い薬はありますか",
        "風邪薬を探しています",
        "ロキソニン",
        "ビタミンCが入った商品"
    ]
    
    print("\n=== テスト検索 ===")
    for query in test_queries:
        print(f"\n検索クエリ: {query}")
        results, context = engine.recommend_products(query, max_results=3)
        print(f"クエリタイプ: {context.query_type.value}")
        print(f"抽出キーワード: {context.extracted_keywords}")
        print(f"結果数: {len(results)}")
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.product_name} (スコア: {result.similarity_score:.3f})")

if __name__ == "__main__":
    main()