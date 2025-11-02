#!/usr/bin/env python3
"""
検索デバッグスクリプト
"""
import csv
import os

def test_ingredient_search():
    """有効成分検索のテスト"""
    csv_path = "data/product_recommend.csv"
    
    if not os.path.exists(csv_path):
        print(f"CSV ファイルが見つかりません: {csv_path}")
        return
    
    query = "シルデナフィル"
    query_lower = query.lower().strip()
    
    print(f"検索クエリ: '{query}'")
    print("-" * 50)
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ingredient = row.get('有効成分', '').lower().strip()
            name = row.get('商品名', '')
            
            print(f"商品{i+1}: {name}")
            print(f"  有効成分: '{ingredient}'")
            
            # 一致チェック
            if query_lower == ingredient:
                print(f"  → 完全一致!")
            elif query_lower in ingredient:
                print(f"  → 含有一致!")
            else:
                print(f"  → マッチしない")
            print()

if __name__ == "__main__":
    test_ingredient_search()