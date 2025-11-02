#!/usr/bin/env python3
"""
検索テスト用スクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.faiss_rag_system import FAISSRAGSystem

def test_search():
    """検索テスト"""
    print("=== 検索システムテスト ===")
    
    try:
        # システム初期化
        rag_system = FAISSRAGSystem()
        rag_system.load_or_create_index()
        
        print(f"データ数: {len(rag_system.metadata_list)}")
        
        if rag_system.metadata_list:
            print("\n=== 最初の3件のメタデータ ===")
            for i, metadata in enumerate(rag_system.metadata_list[:3]):
                print(f"商品{i+1}: {metadata}")
        
        # 検索テスト
        test_queries = ["シルデナフィル", "カマグラ", "AGA", "ED"]
        
        for query in test_queries:
            print(f"\n=== '{query}' 検索結果 ===")
            results = rag_system.search_products(query, top_k=3)
            print(f"結果数: {len(results)}")
            
            for i, result in enumerate(results):
                print(f"  {i+1}. {result.product_name} (スコア: {result.similarity_score:.3f})")
    
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()