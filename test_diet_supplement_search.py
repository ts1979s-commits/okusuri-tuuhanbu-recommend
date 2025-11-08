#!/usr/bin/env python3

from src.faiss_rag_system import FAISSRAGSystem

def test_diet_supplement_search():
    """「ダイエットサプリ」検索テスト"""
    rag = FAISSRAGSystem()
    
    print("🔍 「ダイエットサプリ」検索テスト")
    print("=" * 50)
    
    results = rag.search_products("ダイエットサプリ", top_k=5)
    
    print(f"検索結果数: {len(results)}件\n")
    
    for i, result in enumerate(results, 1):
        category_mark = "✅" if "ダイエット" in str(result.category) else "❌"
        print(f"{i}. {category_mark} {result.product_name}")
        print(f"   📂 カテゴリ: {result.category}")
        print(f"   🎯 スコア: {result.similarity_score:.3f}")
        
        if result.metadata and 'subcategory' in result.metadata:
            print(f"   📋 サブカテゴリ: {result.metadata['subcategory']}")
        print()
    
    print("🔍 期待される結果:")
    print("1位: アーユスリム (サブカテゴリ: ダイエットサプリ)")
    print("オルリガルは「ゼニカル・ダイエットピル」なので表示されるべきではない")

if __name__ == "__main__":
    test_diet_supplement_search()