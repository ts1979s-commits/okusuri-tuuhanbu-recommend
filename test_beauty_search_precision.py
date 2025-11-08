#!/usr/bin/env python3

from src.faiss_rag_system import FAISSRAGSystem

def test_beauty_search_precision():
    """美容商品の検索精度テスト"""
    rag = FAISSRAGSystem()
    
    test_queries = [
        "シミを薄くしたい",
        "まつ毛を伸ばしたい", 
        "ニキビを治したい",
        "日焼けを防ぎたい",
        "むくみを取りたい",
        "バストアップしたい",
        "美白したい",
        "美容"
    ]
    
    print("🔍 美容関連検索精度テスト")
    print("="*60)
    
    for query in test_queries:
        print(f"\n🔍 検索: 「{query}」")
        print("-" * 40)
        
        results = rag.search_products(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            category_display = result.category if result.category else "❌その他"
            beauty_mark = "✅" if "美容" in str(result.category) else "❌"
            
            print(f"{i}. {beauty_mark} {result.product_name}")
            print(f"   📂 カテゴリ: {category_display}")
            print(f"   🎯 スコア: {result.similarity_score:.3f}")
            
            # メタデータからサブカテゴリーを確認
            if result.metadata and 'subcategory' in result.metadata:
                print(f"   📋 サブカテゴリ: {result.metadata['subcategory']}")
            
            print()

if __name__ == "__main__":
    test_beauty_search_precision()