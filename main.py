"""
お薬通販部商品レコメンドLLMアプリ - 本番運用版
フェーズ1実装: RAGベースの商品検索・レコメンドシステム
"""
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """メインエントリーポイント - 本番運用版"""
    print("🏥 お薬通販部商品レコメンドLLMアプリ - 本番運用版")
    print("=" * 60)
    
    # 初期化チェック
    if not initialize_system():
        print("❌ システム初期化に失敗しました")
        return
    
    while True:
        print("\n" + "="*60)
        print("📋 メインメニュー")
        print("="*60)
        print("1. 🕷️  商品データ収集 (スクレイピング)")
        print("2. � データ処理・エクスポート")
        print("3. �🔍 商品検索・レコメンド (CLI)")
        print("4. 🌐 Web UI起動 (Streamlit)")
        print("5. 🔧 システム状態確認")
        print("6. 💾 データバックアップ")
        print("7. 📈 データ分析・統計")
        print("8. ⚙️  システム設定")
        print("0. 終了")
        
        choice = input("\n番号を入力: ").strip()
        
        try:
            if choice == "1":
                run_data_collection()
            elif choice == "2":
                run_data_processing()
            elif choice == "3":
                run_cli_recommendation()
            elif choice == "4":
                run_web_ui()
            elif choice == "5":
                check_system_status()
            elif choice == "6":
                run_backup()
            elif choice == "7":
                run_data_analysis()
            elif choice == "8":
                show_system_settings()
            elif choice == "0":
                print("🔚 アプリケーションを終了します")
                logger.info("アプリケーション終了")
                break
            else:
                print("❌ 無効な選択です")
        except KeyboardInterrupt:
            print("\n⚠️ 操作がキャンセルされました")
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            logger.error(f"メニュー実行エラー: {e}")

def initialize_system():
    """システム初期化"""
    try:
        # 必要なディレクトリを作成
        directories = ['data', 'logs', 'backups', 'reports']
        for dir_name in directories:
            Path(dir_name).mkdir(exist_ok=True)
        
        # 設定ファイルの確認
        from config.settings import get_settings
        settings = get_settings()
        
        if not settings.OPENAI_API_KEY:
            print("⚠️ OPENAI_API_KEYが設定されていません")
            print("   .envファイルを作成してAPI Keyを設定してください")
            return False
        
        print("✅ システム初期化完了")
        logger.info("システム初期化完了")
        return True
        
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")
        logger.error(f"システム初期化エラー: {e}")
        return False

def run_data_collection():
    """商品データ収集（スクレイピング）"""
    print("\n🕷️ 商品データ収集を開始...")
    logger.info("商品データ収集開始")
    
    try:
        from src.scraper import OkusuriScraper
        from src.data_exporter import ProductDataExporter
        import json
        
        scraper = OkusuriScraper()
        exporter = ProductDataExporter()
        
        print("📡 お薬通販部サイトからデータを取得中...")
        
        # 実際のスクレイピング実行（テスト用データを使用）
        print("⚠️ 現在はサンプルデータを使用します")
        
        # 既存のサンプルデータを読み込み
        sample_file = Path("data/sample_products_real.json")
        if sample_file.exists():
            with open(sample_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # データを正規化
            normalized = exporter.normalize_product_data(raw_data)
            
            # タイムスタンプ付きファイル名で保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 各種形式で保存
            exporter.export_to_ndjson(normalized, f"products_{timestamp}.ndjson")
            exporter.export_to_csv(normalized, f"products_{timestamp}.csv")
            exporter.export_to_sqlite(normalized, f"products_{timestamp}.db")
            
            # メイン用ファイルも更新
            exporter.export_to_ndjson(normalized, "products.ndjson")
            
            print(f"✅ {len(normalized)} 件の商品データを収集・保存完了")
            logger.info(f"商品データ収集完了: {len(normalized)} 件")
            
        else:
            print("❌ サンプルデータが見つかりません")
            
    except Exception as e:
        print(f"❌ データ収集エラー: {e}")
        logger.error(f"データ収集エラー: {e}")

def run_data_processing():
    """データ処理・エクスポート"""
    print("\n📊 データ処理・エクスポートメニュー")
    print("-" * 40)
    print("1. NDJSONからの各種形式エクスポート")
    print("2. FAISSインデックス再構築")
    print("3. データ品質チェック")
    print("4. 重複データ除去")
    
    choice = input("選択: ").strip()
    
    try:
        from src.data_exporter import ProductDataExporter
        from src.faiss_rag_system import FAISSRAGSystem
        
        exporter = ProductDataExporter()
        
        if choice == "1":
            print("\n📤 データエクスポート中...")
            
            # NDJSONから読み込み
            products = exporter.load_from_ndjson("products.ndjson")
            if not products:
                print("❌ 処理するデータがありません")
                return
            
            # 各種形式でエクスポート
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            exporter.export_to_json(products, f"export_{timestamp}.json")
            exporter.export_to_csv(products, f"export_{timestamp}.csv") 
            exporter.export_to_sqlite(products, f"export_{timestamp}.db")
            
            print(f"✅ {len(products)} 件のデータをエクスポート完了")
            
        elif choice == "2":
            print("\n🔧 FAISSインデックス再構築中...")
            
            products = exporter.load_from_ndjson("products.ndjson")
            if not products:
                print("❌ 処理するデータがありません")
                return
            
            rag = FAISSRAGSystem()
            
            # 商品データをFAISSに追加
            products_data = []
            for product in products:
                product_dict = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description or '',
                    'category': product.category,
                    'url': product.url,
                    'tags': product.tags or [],
                    'text': f"{product.name} {product.description or ''} {' '.join(product.tags or [])}"
                }
                products_data.append(product_dict)
            
            rag.add_products(products_data)
            print(f"✅ {len(products)} 件のFAISSインデックス再構築完了")
            
        elif choice == "3":
            print("\n🔍 データ品質チェック中...")
            products = exporter.load_from_ndjson("products.ndjson")
            
            if products:
                print(f"📊 総商品数: {len(products)}")
                categories = {}
                missing_fields = {'price': 0, 'description': 0, 'image_url': 0}
                
                for product in products:
                    # カテゴリー統計
                    cat = product.category or 'unknown'
                    categories[cat] = categories.get(cat, 0) + 1
                    
                    # 欠損フィールド統計
                    if not product.price:
                        missing_fields['price'] += 1
                    if not product.description:
                        missing_fields['description'] += 1
                    if not product.image_url:
                        missing_fields['image_url'] += 1
                
                print("\n📋 カテゴリー別商品数:")
                for cat, count in categories.items():
                    print(f"  {cat}: {count} 件")
                
                print("\n⚠️ 欠損フィールド統計:")
                for field, count in missing_fields.items():
                    print(f"  {field}: {count} 件 ({count/len(products)*100:.1f}%)")
            else:
                print("❌ 処理するデータがありません")
                
        else:
            print("❌ 無効な選択です")
            
    except Exception as e:
        print(f"❌ データ処理エラー: {e}")
        logger.error(f"データ処理エラー: {e}")

def run_backup():
    """データバックアップ"""
    print("\n💾 データバックアップを実行中...")
    
    try:
        import shutil
        import zipfile
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_dir = Path("backups") / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # データフォルダをコピー
        if Path("data").exists():
            shutil.copytree("data", backup_dir / "data", dirs_exist_ok=True)
        
        # ログをコピー
        if Path("logs").exists():
            shutil.copytree("logs", backup_dir / "logs", dirs_exist_ok=True)
        
        # ZIPアーカイブ作成
        zip_path = Path("backups") / f"{backup_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in backup_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(backup_dir)
                    zipf.write(file_path, arcname)
        
        # 一時ディレクトリを削除
        shutil.rmtree(backup_dir)
        
        print(f"✅ バックアップ完了: {zip_path}")
        print(f"📂 ファイルサイズ: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"バックアップ作成: {zip_path}")
        
    except Exception as e:
        print(f"❌ バックアップエラー: {e}")
        logger.error(f"バックアップエラー: {e}")

def run_data_analysis():
    """データ分析・統計"""
    print("\n📈 データ分析・統計")
    
    try:
        from src.data_exporter import ProductDataExporter
        import json
        
        exporter = ProductDataExporter()
        products = exporter.load_from_ndjson("products.ndjson")
        
        if not products:
            print("❌ 分析するデータがありません")
            return
        
        print(f"\n📊 基本統計")
        print(f"総商品数: {len(products)}")
        print(f"データソース: {products[0].source if products else 'N/A'}")
        
        # カテゴリー分析
        categories = {}
        tag_counts = {}
        
        for product in products:
            # カテゴリー統計
            cat = product.category or 'その他'
            categories[cat] = categories.get(cat, 0) + 1
            
            # タグ統計
            for tag in product.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print(f"\n🏷️ カテゴリー別商品数:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(products) * 100
            print(f"  {cat}: {count} 件 ({percentage:.1f}%)")
        
        print(f"\n🔖 人気タグ TOP5:")
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for tag, count in sorted_tags:
            print(f"  {tag}: {count} 件")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_products': len(products),
            'categories': categories,
            'top_tags': dict(sorted_tags),
            'data_quality': {
                'with_price': len([p for p in products if p.price]),
                'with_description': len([p for p in products if p.description]),
                'with_image': len([p for p in products if p.image_url])
            }
        }
        
        report_file = Path("reports") / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細レポートを保存: {report_file}")
        
    except Exception as e:
        print(f"❌ データ分析エラー: {e}")
        logger.error(f"データ分析エラー: {e}")

def show_system_settings():
    """システム設定表示"""
    print("\n⚙️ システム設定")
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        print("\n📋 現在の設定:")
        print(f"OpenAI Model: {settings.OPENAI_MODEL}")
        print(f"Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
        print(f"Base URL: {settings.OKUSURI_BASE_URL}")
        print(f"Request Delay: {settings.REQUEST_DELAY}秒")
        print(f"Max Pages: {settings.MAX_PAGES}")
        print(f"Log Level: {settings.LOG_LEVEL}")
        print(f"Streamlit Port: {settings.STREAMLIT_PORT}")
        
        # ファイル存在確認
        print(f"\n📁 ファイル存在確認:")
        files_to_check = [
            "data/products.ndjson",
            "data/faiss_index.bin", 
            "data/metadata.pkl",
            ".env"
        ]
        
        for file_path in files_to_check:
            path = Path(file_path)
            status = "✅" if path.exists() else "❌"
            size = f"({path.stat().st_size} bytes)" if path.exists() else ""
            print(f"  {status} {file_path} {size}")
        
    except Exception as e:
        print(f"❌ 設定確認エラー: {e}")
        logger.error(f"設定確認エラー: {e}")

def run_scraper():
    """従来のスクレイパー実行（互換性のため残す）"""
    run_data_collection()

def run_cli_recommendation():
    """コマンドライン版レコメンド実行"""
    print("\n🔍 商品検索・レコメンドシステム")
    
    try:
        from src.faiss_rag_system import FAISSRAGSystem
        
        rag = FAISSRAGSystem()
        
        print("検索システムを初期化中...")
        
        while True:
            print("\n" + "-"*50)
            query = input("🔍 検索キーワードを入力 (空白で戻る): ").strip()
            
            if not query:
                break
            
            print(f"\n検索中: '{query}'")
            results = rag.search_products(query, top_k=5)
            
            if results:
                print(f"\n📋 検索結果 ({len(results)} 件):")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.product_name}")
                    print(f"   カテゴリー: {result.category}")
                    print(f"   類似度: {result.similarity_score:.3f}")
                    print(f"   説明: {result.description[:100]}...")
                    if result.url != "javascript:void(0)":
                        print(f"   URL: {result.url}")
            else:
                print("❌ 該当する商品が見つかりませんでした")
                
    except Exception as e:
        print(f"❌ 検索エラー: {e}")
        logger.error(f"検索エラー: {e}")

def run_web_ui():
    """Web UIを起動"""
    import subprocess
    print("\n🌐 StreamlitでWeb UIを起動します...")
    print("ブラウザで http://localhost:8501 にアクセスしてください")
    
    try:
        # Streamlitの起動確認
        try:
            import streamlit
        except ImportError:
            print("❌ Streamlitがインストールされていません")
            print("   pip install streamlit を実行してください")
            return
        
        # app.pyの存在確認
        if not Path("app.py").exists():
            print("❌ app.py が見つかりません")
            return
        
        logger.info("Streamlit Web UI起動")
        subprocess.run([
            "streamlit", "run", "app.py", 
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n🔚 Web UIを終了しました")
        logger.info("Streamlit Web UI終了")
    except Exception as e:
        print(f"❌ Web UI起動エラー: {e}")
        logger.error(f"Web UI起動エラー: {e}")

def check_system_status():
    """システム状態を確認"""
    print("\n🔧 システム状態確認")
    
    try:
        from src.faiss_rag_system import FAISSRAGSystem
        from src.data_exporter import ProductDataExporter
        from config.settings import get_settings
        
        settings = get_settings()
        
        print("\n=== システム状態 ===")
        
        # 設定確認
        print(f"✅ OpenAI API Key: {'設定済み' if settings.OPENAI_API_KEY else '❌ 未設定'}")
        print(f"✅ OpenAI Model: {settings.OPENAI_MODEL}")
        
        # データファイル確認
        exporter = ProductDataExporter()
        products = exporter.load_from_ndjson("products.ndjson")
        print(f"📊 商品データ: {len(products) if products else 0} 件")
        
        # FAISSインデックス確認
        try:
            rag = FAISSRAGSystem()
            if hasattr(rag, 'index') and rag.index is not None:
                index_count = rag.index.ntotal if hasattr(rag.index, 'ntotal') else 'Unknown'
                print(f"🔍 FAISSインデックス: {index_count} 件")
            else:
                print("🔍 FAISSインデックス: 未構築")
        except Exception as e:
            print(f"🔍 FAISSインデックス: エラー ({e})")
        
        # ディスク使用量
        data_dir = Path("data")
        if data_dir.exists():
            total_size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
            print(f"💾 データディスク使用量: {total_size / 1024 / 1024:.2f} MB")
        
        # 最新のログエントリ
        log_file = Path("logs/app.log")
        if log_file.exists():
            log_size = log_file.stat().st_size / 1024
            print(f"📝 ログファイル: {log_size:.2f} KB")
        
        print("\n=== 動作テスト ===")
        
        # 簡単な検索テスト
        if products:
            try:
                rag = FAISSRAGSystem()
                test_results = rag.search_products("治療", top_k=1)
                if test_results:
                    print(f"✅ 検索機能: 正常動作 (テスト結果: {test_results[0].product_name})")
                else:
                    print("⚠️ 検索機能: 結果なし")
            except Exception as e:
                print(f"❌ 検索機能: エラー ({e})")
        else:
            print("⚠️ 検索機能: データなし")
        
        print("\n=== 推奨アクション ===")
        if not products:
            print("1. まず「商品データ収集」を実行してください")
        if not settings.OPENAI_API_KEY:
            print("2. .envファイルにOPENAI_API_KEYを設定してください")
        if products and len(products) < 10:
            print("3. より多くの商品データを収集することを推奨します")
        
    except Exception as e:
        print(f"❌ システム状態確認エラー: {e}")
        logger.error(f"システム状態確認エラー: {e}")

if __name__ == "__main__":
    main()

def run_scraper():
    """スクレイパーを実行"""
    from src.scraper import main as scraper_main
    print("\n🕷️ 商品データ取得を開始...")
    scraper_main()

def run_cli_recommendation():
    """コマンドライン版レコメンド実行"""
    from src.recommendation_engine import main as recommendation_main
    print("\n🔍 コマンドライン版レコメンド実行...")
    recommendation_main()

def run_web_ui():
    """Web UIを起動"""
    import subprocess
    print("\n🌐 StreamlitでWeb UIを起動します...")
    print("ブラウザで http://localhost:8501 にアクセスしてください")
    
    try:
        subprocess.run([
            "streamlit", "run", "app.py", 
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\nWeb UIを終了しました")
    except Exception as e:
        print(f"Web UI起動エラー: {e}")

def check_system_status():
    """システム状態を確認"""
    try:
        from src.recommendation_engine import RecommendationEngine
        
        print("\n🔧 システム状態を確認中...")
        engine = RecommendationEngine()
        status = engine.get_system_status()
        
        print("\n=== システム状態 ===")
        for key, value in status.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"システム状態確認エラー: {e}")

if __name__ == "__main__":
    main()