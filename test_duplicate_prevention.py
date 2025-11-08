#!/usr/bin/env python3
"""
重複検索テスト - 商品が重複して表示されないことを確認
"""

import sys
import os

# パス設定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import basic_search

def test_duplicate_prevention():
    """重複防止機能をテスト"""
    print("=== 重複防止テスト開始 ===\n")
    
    # 一般的な検索クエリで重複が起こりやすいケース
    test_cases = [
        {
            'query': 'サプリメント',
            'description': '一般的なサプリメント検索で重複が発生しやすい'
        },
        {
            'query': '性病',
            'description': '性病関連での重複チェック'
        },
        {
            'query': '治療薬',
            'description': '治療薬での重複チェック'
        },
        {
            'query': 'ダイエット',
            'description': 'ダイエット関連での重複チェック'
        }
    ]
    
    for test_case in test_cases:
        query = test_case['query']
        description = test_case['description']
        
        print(f"🔍 検索クエリ: '{query}'")
        print(f"   説明: {description}")
        
        results = basic_search(query, top_k=10)
        
        # 商品名を収集
        product_names = [result.product_name for result in results]
        
        # 重複チェック
        unique_products = set(product_names)
        
        print(f"   結果数: {len(results)}件")
        print(f"   ユニーク商品数: {len(unique_products)}件")
        
        if len(results) == len(unique_products):
            print("   ✅ 重複なし - 正常")
        else:
            print("   ❌ 重複発見!")
            # 重複した商品を特定
            seen = set()
            duplicates = set()
            for product in product_names:
                if product in seen:
                    duplicates.add(product)
                seen.add(product)
            
            if duplicates:
                print(f"   重複商品: {list(duplicates)}")
        
        # 上位5件の商品名を表示
        print("   上位商品:")
        for i, result in enumerate(results[:5]):
            print(f"   {i+1}. {result.product_name} (スコア: {result.similarity_score})")
        
        print()
    
    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_duplicate_prevention()