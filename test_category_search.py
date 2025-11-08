#!/usr/bin/env python3
"""
カテゴリ検索テスト - ダイエットサプリと美容サプリ
"""

import sys
import os

# パス設定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import basic_search

def test_category_search():
    """カテゴリ検索をテスト"""
    print("=== カテゴリ検索テスト開始 ===\n")
    
    # テストケース
    test_cases = [
        {
            'query': 'ダイエットサプリ',
            'expected_products': ['アーユスリム', 'トリファラ'],
            'expected_count': 2
        },
        {
            'query': '美容サプリ',
            'expected_products': ['プエラリアミリフィカタブレット', 'L-グルタチオン（バイタルミー）'],
            'expected_count': 2
        },
        {
            'query': 'EDサプリ',
            'expected_products': ['スペマン'],
            'expected_count': 1
        },
        {
            'query': '薄毛サプリ',
            'expected_products': ['プレミアムリジン'],
            'expected_count': 1
        }
    ]
    
    for test_case in test_cases:
        query = test_case['query']
        expected_products = test_case['expected_products']
        expected_count = test_case['expected_count']
        
        print(f"🔍 検索クエリ: '{query}'")
        results = basic_search(query, top_k=10)
        
        if len(results) == expected_count:
            print(f"   ✅ {len(results)}件の結果が見つかりました:")
            found_products = []
            for i, result in enumerate(results):
                print(f"   {i+1}. {result.product_name} (スコア: {result.similarity_score})")
                found_products.append(result.product_name)
            
            # 期待される商品が含まれているかチェック
            all_found = True
            for expected_product in expected_products:
                product_found = any(expected_product in product for product in found_products)
                if not product_found:
                    print(f"   ❌ 期待される商品 '{expected_product}' が見つかりませんでした")
                    all_found = False
            
            if all_found:
                print(f"   ✅ すべての期待される商品が見つかりました")
            
        else:
            print(f"   ❌ 期待される件数: {expected_count}, 実際の件数: {len(results)}")
            for i, result in enumerate(results):
                print(f"   {i+1}. {result.product_name} (スコア: {result.similarity_score})")
        
        print()
    
    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_category_search()