#!/usr/bin/env python3
"""便秘関連検索の詳細テスト"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.faiss_rag_system import FAISSRAGSystem

def test_constipation_keywords():
    """便秘関連キーワード検索のテスト"""
    rag_system = FAISSRAGSystem()
    
    test_queries = [
        "便秘",
        "便秘薬", 
        "便秘改善",
        "お腹のハリ",
        "便通",
        "腸内環境",
        "デトックス"
    ]
    
    for query in test_queries:
        print(f"\n🔍 「{query}」検索テスト")
        print("=" * 50)
        
        results = rag_system.search_products(query, top_k=5)
        
        print(f"検索結果数: {len(results)}件\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.product_name}")
            print(f"   カテゴリ: {result.category}")
            print(f"   スコア: {result.similarity_score:.3f}")
            subcategory = result.metadata.get('subcategory', '') if result.metadata else ''
            print(f"   サブカテゴリ: {subcategory}")
            print()

if __name__ == "__main__":
    test_constipation_keywords()