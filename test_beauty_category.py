#!/usr/bin/env python3

from src.faiss_rag_system import FAISSRAGSystem

def test_beauty_category():
    rag = FAISSRAGSystem()
    
    print("🔍 美容・スキンケア商品のカテゴリー確認")
    print("="*50)
    
    # 美容商品名で個別検索
    beauty_products = [
        "イソトロイン", "ケアプロスト", "トラセミド", 
        "プラセントレックス", "ヘリオケア", "プエラリア",
        "DNSローラー", "L-グルタチオン", "プロポリス石鹸"
    ]
    
    for product_name in beauty_products:
        results = rag.search_products(product_name, top_k=1)
        if results:
            product = results[0]
            print(f"✅ {product.product_name}")
            print(f"   カテゴリー: '{product.category}'")
            print(f"   メタデータ: {product.metadata}")
            print()
    
    # 全商品リストから美容商品をフィルタリング
    print("\n🌟 全商品リストから美容商品を確認")
    print("="*50)
    
    results = rag.search_products("検索", top_k=50)  # ダミー検索
    beauty_count = 0
    
    for product in results:
        if "美容" in str(product.category):
            beauty_count += 1
            print(f"{beauty_count}. {product.product_name} - カテゴリー: '{product.category}'")
    
    print(f"\n美容商品合計: {beauty_count}件")

if __name__ == "__main__":
    test_beauty_category()