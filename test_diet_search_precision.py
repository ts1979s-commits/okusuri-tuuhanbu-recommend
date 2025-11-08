#!/usr/bin/env python3

from src.faiss_rag_system import FAISSRAGSystem

def test_diet_search_precision():
    """ダイエット関連検索精度テスト"""
    rag = FAISSRAGSystem()
    
    test_queries = [
        "痩せたい", 
        "ダイエット",
        "食欲を抑えたい",
        "脂肪を減らしたい", 
        "体重を落としたい",
        "便秘を解消したい",
        "太った",
        "脂っこい食事"
    ]
    
    print("🔍 ダイエット関連検索精度テスト")
    print("="*60)
    
    for query in test_queries:
        print(f"\n🔍 検索: 「{query}」")
        print("-" * 40)
        
        results = rag.search_products(query, top_k=5)
        
        for i, result in enumerate(results, 1):
            category_display = result.category if result.category else "❌その他"
            diet_mark = "✅" if "ダイエット" in str(result.category) else "❌"
            
            print(f"{i}. {diet_mark} {result.product_name}")
            print(f"   📂 カテゴリ: {category_display}")
            print(f"   🎯 スコア: {result.similarity_score:.3f}")
            
            # メタデータからサブカテゴリーを確認
            if result.metadata and 'subcategory' in result.metadata:
                print(f"   📋 サブカテゴリ: {result.metadata['subcategory']}")
            print()

if __name__ == "__main__":
    test_diet_search_precision()