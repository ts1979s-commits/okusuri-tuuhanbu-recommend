#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サプリメント検索機能のテストスクリプト
"""
import sys
import os
import pandas as pd

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# app.pyから必要な関数をインポート
from app import basic_search

def test_supplement_searches():
    """サプリメント検索のテスト"""
    print("=== サプリメント検索テスト開始 ===\n")
    
    # テスト対象の検索クエリ
    test_queries = [
        "サプリ",
        "サプリメント", 
        "EDサプリ",
        "薄毛サプリ",
        "ダイエットサプリ",
        "便秘サプリ",
        "バストアップサプリ",
        "美白サプリ",
        "トリファラ",
        "プエラリア",
        "グルタチオン"
    ]
    
    for query in test_queries:
        print(f"🔍 検索クエリ: '{query}'")
        try:
            results = basic_search(query, top_k=10)
            if results:
                print(f"   ✅ {len(results)}件の結果が見つかりました:")
                for i, result in enumerate(results[:3], 1):  # 最初の3件を表示
                    print(f"   {i}. {result.product_name} (スコア: {result.similarity_score:.1f})")
            else:
                print("   ❌ 結果が見つかりませんでした")
        except Exception as e:
            print(f"   ❌ エラーが発生しました: {e}")
        print()
    
    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_supplement_searches()