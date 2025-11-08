#!/usr/bin/env python3

from src.faiss_rag_system import FAISSRAGSystem

def test_beauty_keyword_search():
    """「美容」キーワード検索での全美容商品表示テスト"""
    rag = FAISSRAGSystem()
    
    print("🔍 「美容」キーワード検索テスト")
    print("=" * 50)
    
    # 美容で検索（より多くの結果を要求）
    results = rag.search_products("美容", top_k=15)
    
    print(f"検索結果数: {len(results)}件\n")
    
    # 目標の4商品をチェック
    target_products = [
        "DNSローラー",
        "L-グルタチオン（バイタルミー）", 
        "プロポリス石鹸",
        "ケアプロスト"
    ]
    
    found_targets = []
    
    for i, result in enumerate(results, 1):
        category_mark = "✅" if "美容" in str(result.category) else "❌"
        print(f"{i:2d}. {category_mark} {result.product_name}")
        print(f"    📂 カテゴリ: {result.category}")
        print(f"    🎯 スコア: {result.similarity_score:.3f}")
        
        # ターゲット商品かチェック
        if result.product_name in target_products:
            found_targets.append(result.product_name)
            print(f"    🌟 ターゲット商品発見！")
        
        if result.metadata and 'subcategory' in result.metadata:
            print(f"    📋 サブカテゴリ: {result.metadata['subcategory']}")
        print()
    
    print(f"\n📊 ターゲット商品の発見状況:")
    print(f"発見済み: {len(found_targets)}/4件")
    
    for product in target_products:
        status = "✅ 発見" if product in found_targets else "❌ 未発見"
        print(f"  {status}: {product}")
    
    if len(found_targets) < 4:
        print(f"\n⚠️  問題: {4 - len(found_targets)}件の商品が「美容」検索で表示されていません")
        
        # 個別検索で確認
        print(f"\n🔍 個別検索での確認:")
        for product in target_products:
            if product not in found_targets:
                individual_result = rag.search_products(product, top_k=1)
                if individual_result:
                    print(f"  {product}: 個別検索では発見可能 (カテゴリ: {individual_result[0].category})")
                else:
                    print(f"  {product}: 個別検索でも発見不可")

if __name__ == "__main__":
    test_beauty_keyword_search()