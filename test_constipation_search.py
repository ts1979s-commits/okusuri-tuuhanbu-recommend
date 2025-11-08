#!/usr/bin/env python3
"""便秘改善検索テスト"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.faiss_rag_system import FAISSRAGSystem

def test_constipation_search():
    """便秘改善検索のテスト"""
    rag_system = FAISSRAGSystem()
    
    print("🔍 「便秘改善」検索テスト")
    print("=" * 50)
    
    # 便秘改善で検索
    results = rag_system.search_products("便秘改善", top_k=10)
    
    print(f"検索結果数: {len(results)}件\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. ✅ {result.product_name}")
        print(f"   📂 カテゴリ: {result.category}")
        print(f"   🎯 スコア: {result.similarity_score:.3f}")
        subcategory = result.metadata.get('subcategory', '') if result.metadata else ''
        print(f"   📋 サブカテゴリ: {subcategory}")
        print()
    
    print("🔍 期待される結果:")
    print("1位: トリファラ (サブカテゴリ: 便秘薬)")
    print("他の商品は便秘改善に関連性が低いため表示されるべきではない")

if __name__ == "__main__":
    test_constipation_search()