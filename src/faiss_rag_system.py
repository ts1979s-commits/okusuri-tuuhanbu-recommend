"""
FAISS ベースRAGシステム - お薬通販部商品レコメンドLLMアプリ（改良版）
キーワード完全一致優先の検索システム
"""
import json
import os
import pickle
import csv
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass

import faiss
import numpy as np
from openai import OpenAI

from config.settings import get_settings

settings = get_settings()

# ログ設定
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """検索結果データクラス"""
    product_name: str
    url: str
    price: Optional[str]
    description: Optional[str]
    category: Optional[str] = None
    similarity_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class FAISSRAGSystem:
    """FAISSベースのRAGシステム（改良版）"""
    
    def __init__(self):
        """RAGシステムの初期化"""
        # OpenAIクライアントの初期化
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            raise ValueError("OPENAI_API_KEYが必要です")
        
        # プロキシ環境変数をクリア
        import os
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                del os.environ[key]
        
        try:
            # 最小限のパラメータでクライアントを作成
            # proxies引数は明示的に使用しない
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=30.0
            )
            logger.info("OpenAIクライアントを初期化しました")
        except TypeError as te:
            if "proxies" in str(te):
                # プロキシエラーの場合、より基本的な初期化を試行
                logger.warning("プロキシエラーを検出。基本的な初期化を試行中...")
                try:
                    self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("基本的なOpenAIクライアント初期化に成功")
                except Exception as e2:
                    logger.error(f"基本的な初期化も失敗: {e2}")
                    raise
            else:
                logger.error(f"OpenAIクライアント初期化エラー: {te}")
                raise
        except Exception as e:
            logger.error(f"OpenAIクライアント初期化エラー: {e}")
            # 可能性のある問題をチェック
            if "proxies" in str(e):
                logger.error("プロキシ関連エラーが検出されました。環境変数を確認してください。")
            raise
        
        # FAISS設定
        self.index = None
        self.metadata_list = []
        self.documents = []
        self.dimension = 1536  # OpenAI embedding dimension
        
        # データファイルパス
        self.data_dir = "./data"
        self.csv_file = os.path.join(self.data_dir, "product_recommend.csv")
        self.index_file = os.path.join(self.data_dir, "faiss_index.bin")
        self.metadata_file = os.path.join(self.data_dir, "metadata.pkl")
        self.documents_file = os.path.join(self.data_dir, "documents.pkl")
        
        # 既存のインデックスがあればロード
        if self._index_exists():
            logger.info("既存のインデックスをロード中...")
            self._load_index()
        else:
            logger.info("インデックスが存在しないため、CSVから新規作成します")
            self._create_index_from_csv()

    def search_products(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """キーワードベース検索（シンプルで確実な検索）"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("インデックスが空です")
                return []
            
            query = query.strip()
            logger.info(f"検索開始: '{query}'")
            
            # 1. まず基本的な文字列マッチング検索を試行
            simple_results = self._simple_text_search(query, top_k)
            
            # 2. 結果がある場合はそれを返す
            if simple_results:
                logger.info(f"文字列マッチング検索で{len(simple_results)}件の結果を取得")
                filtered_results = self._filter_search_results(query, simple_results)
                return filtered_results
            
            # 3. 結果がない場合、ベクトル検索にフォールバック
            logger.info("文字列マッチングなし。ベクトル検索にフォールバック")
            vector_results = self._vector_search(query, top_k)
            filtered_results = self._filter_search_results(query, vector_results)
            
            logger.info(f"検索完了: {len(filtered_results)}件の結果（フィルタリング適用後）")
            return filtered_results
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []

    def _filter_search_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """特定のクエリに対して不適切な結果を除外する"""
        if not results:
            return results
        
        query_lower = query.lower().strip()
        filtered_results = []
        
        # AGAや抜け毛関連の検索でケアプロストを除外
        aga_hair_keywords = [
            "抜け毛", "薄毛", "脱毛", "aga", "育毛", "発毛", 
            "髪", "頭髪", "ハゲ", "生え際", "頭頂部", "毛量",
            "フィナステリド", "ミノキシジル", "デュタステリド"
        ]
        
        # ED治療薬関連のキーワード
        ed_keywords = [
            "勃起", "ed", "erectile", "性機能", "中折れ", "勃起不全",
            "バイアグラ", "シアリス", "レビトラ", "ステンドラ", "ザイデナ",
            "シルデナフィル", "タダラフィル", "バルデナフィル", "アバナフィル", "ウデナフィル",
            "性行為", "勃起力", "硬さ", "持続", "男性機能", "ed薬", "ed治療",
            "即効性ed", "長時間持続", "副作用少ない", "アジア人向けed"
        ]
        
        # ダイエット関連のキーワード
        diet_keywords = [
            "ダイエット", "痩せ", "痩せたい", "体重", "減量", "肥満", "太っ", "太り",
            "食欲", "食べ過ぎ", "脂肪", "脂っこい", "カロリー", "メタボ",
            "便秘", "お通じ", "腸内環境", "デトックス", "排出", "便通",
            "糖質", "炭水化物", "糖分", "甘い物", "血糖値", "インスリン",
            "代謝", "燃焼", "エネルギー", "基礎代謝", "新陳代謝"
        ]
        
        # 美容・スキンケア関連のキーワード
        beauty_keywords = [
            "美容", "スキンケア", "美肌", "美白", "シミ", "シワ", "ニキビ", "吹き出物",
            "まつ毛", "まつげ", "日焼け", "紫外線", "むくみ", "バストアップ", "胸",
            "デトックス", "アンチエイジング", "エイジングケア", "肌荒れ", "毛穴",
            "コラーゲン", "美容液", "保湿", "乾燥肌", "敏感肌", "ターンオーバー",
            "肌質改善", "透明感", "くすみ", "たるみ", "小顔", "美しく", "きれい"
        ]
        
        # 便秘・消化器系関連キーワード
        constipation_keywords = [
            "便秘", "便通", "便秘改善", "便秘薬", "排便", "お腹のハリ", "腸内環境",
            "デトックス", "便が出ない", "排便困難", "便通改善", "消化不良", "整腸"
        ]
        
        # 性病・感染症治療薬関連キーワード
        std_infection_keywords = [
            "性病", "感染症", "クラミジア", "淋病", "梅毒", "ヘルペス", "カンジダ", 
            "トリコモナス", "コンジローマ", "hiv", "エイズ", 
            "抗生物質", "抗ウイルス薬", "抗原虫薬", "細菌感染",
            "ウイルス感染", "尿道炎", "膣炎", "帯状疱疹", "口唇ヘルペス", "性器ヘルペス",
            "おりもの", "かゆみ", "性感染症", "性行為感染症", "std", "sti"
        ]
        
        # 水虫・いんきんたむし専用キーワード
        fungal_infection_keywords = [
            "水虫", "いんきんたむし", "真菌感染", "かゆみ", "皮膚真菌", "白癬菌",
            "足の指", "股間", "陰部", "フルコナゾール", "抗真菌薬"
        ]
        
        # 女性向け・男性サプリ関連キーワード
        female_keywords = [
            "女性", "妊活", "不感症", "性的興奮", "濡れ", "女性用"
        ]
        
        male_supplement_keywords = [
            "精子", "精液", "男性不妊", "天然ハーブ", "サプリ"
        ]
        
        exclude_products_for_aga = ["ケアプロスト", "careplus"]
        exclude_categories_for_ed = ["女性向け薬品", "男性サプリ", "美容・コスメ", "美容・スキンケア", "性病・感染症の治療薬", "AGA治療薬", "ダイエット", "利尿剤", "バストアップ"]
        exclude_categories_for_female = ["ED治療薬", "AGA治療薬", "男性サプリ"]
        exclude_categories_for_supplement = ["ED治療薬", "女性向け薬品"]
        exclude_categories_for_constipation = ["ED治療薬", "AGA治療薬", "性病・感染症の治療薬", "美容・スキンケア"]
        exclude_categories_for_std = ["ED治療薬", "AGA治療薬", "美容・スキンケア", "ダイエット"]
        
        # 検索クエリの分類
        is_aga_query = any(keyword in query_lower for keyword in aga_hair_keywords)
        is_ed_query = any(keyword in query_lower for keyword in ed_keywords)
        is_diet_query = any(keyword in query_lower for keyword in diet_keywords)
        is_beauty_query = any(keyword in query_lower for keyword in beauty_keywords)
        is_constipation_query = any(keyword in query_lower for keyword in constipation_keywords)
        is_std_query = any(keyword in query_lower for keyword in std_infection_keywords)
        is_fungal_query = any(keyword in query_lower for keyword in fungal_infection_keywords)
        is_female_query = any(keyword in query_lower for keyword in female_keywords)
        is_supplement_query = any(keyword in query_lower for keyword in male_supplement_keywords)
        
        for result in results:
            should_exclude = False
            
            if is_aga_query:
                # AGA検索でまつ毛美容液を除外
                product_name = result.product_name.lower() if result.product_name else ""
                category = result.category.lower() if result.category else ""
                
                if (any(excluded in product_name for excluded in exclude_products_for_aga) or
                    "まつげ" in category or "まつ毛" in category):
                    should_exclude = True
                    logger.info(f"AGA検索でまつ毛美容液を除外: {result.product_name}")
            
            elif is_ed_query:
                # ED検索で女性用商品とサプリを除外
                category = result.category if result.category else ""
                if any(excluded_cat == category for excluded_cat in exclude_categories_for_ed):
                    should_exclude = True
                    logger.info(f"ED検索で不適切カテゴリを除外: {result.product_name} ({result.category})")
            
            elif is_female_query:
                # 女性向け検索で男性用商品を除外
                category = result.category if result.category else ""
                if any(excluded_cat == category for excluded_cat in exclude_categories_for_female):
                    should_exclude = True
                    logger.info(f"女性向け検索で男性用商品を除外: {result.product_name} ({result.category})")
                    
            elif is_supplement_query:
                # サプリ検索で医療用ED薬を除外
                category = result.category if result.category else ""
                if any(excluded_cat == category for excluded_cat in exclude_categories_for_supplement):
                    should_exclude = True
                    logger.info(f"サプリ検索で医療用薬品を除外: {result.product_name} ({result.category})")
                    
            elif is_constipation_query:
                # 便秘検索で関連性の低いカテゴリを除外
                category = result.category if result.category else ""
                if any(excluded_cat == category for excluded_cat in exclude_categories_for_constipation):
                    should_exclude = True
                    logger.info(f"便秘検索で関連性の低いカテゴリを除外: {result.product_name} ({result.category})")
                    
            elif is_std_query:
                # 性病・感染症検索で関連性の低いカテゴリを除外
                category = result.category if result.category else ""
                if any(excluded_cat == category for excluded_cat in exclude_categories_for_std):
                    should_exclude = True
                    logger.info(f"性病・感染症検索で関連性の低いカテゴリを除外: {result.product_name} ({result.category})")
                
            elif is_fungal_query:
                # 水虫・いんきんたむし検索：フォルカンのみ表示
                if result.product_name != "フォルカン":
                    should_exclude = True
                    logger.info(f"水虫・いんきんたむし検索でフォルカン以外を除外: {result.product_name} ({result.category})")
            
            if not should_exclude:
                filtered_results.append(result)
        
        # ED検索の場合、ED治療薬を優先的に上位表示
        if is_ed_query:
            # ED治療薬をCSV登録順にソート
            def ed_priority_sort(result):
                if result.category == "ED治療薬":
                    # CSVの登録順に基づいた優先度
                    ed_order = {
                        'カマグラゴールド': 1,
                        'タダライズ': 2,
                        'バリフ': 3,
                        'アバナ': 4,
                        'ザイスマ': 5
                    }
                    return ed_order.get(result.product_name, 99)  # ED薬は1-5、その他は99
                else:
                    return 100  # 非ED薬は最低優先度
            
            filtered_results.sort(key=ed_priority_sort)
            
            # フィルタリング後にED治療薬が少ない場合、追加で検索
            ed_drugs_found = [r for r in filtered_results if r.category == "ED治療薬"]
            if len(ed_drugs_found) < 5:  # 5種類のED薬が表示されていない場合
                all_ed_drugs = [r for r in results if r.category == "ED治療薬" and r not in filtered_results]
                # CSVの順序でソート
                all_ed_drugs.sort(key=lambda x: {
                    'カマグラゴールド': 1,
                    'タダライズ': 2,
                    'バリフ': 3,
                    'アバナ': 4,
                    'ザイスマ': 5
                }.get(x.product_name, 99))
                
                needed_count = min(5 - len(ed_drugs_found), len(all_ed_drugs))
                filtered_results.extend(all_ed_drugs[:needed_count])
        
        # 美容検索の場合、美容・スキンケア商品を優先的に上位表示
        elif is_beauty_query:
            def beauty_priority_sort(result):
                category = result.category if result.category else ""
                
                # 美容・スキンケア商品に高い優先度を与える
                if category == "美容・スキンケア":
                    # サブカテゴリー別の詳細優先度
                    subcategory = result.metadata.get('subcategory', '').strip() if result.metadata else ""
                    
                    # 検索クエリに応じたサブカテゴリー優先度
                    if any(kw in query_lower for kw in ["シミ", "美白", "エイジング", "アンチエイジング"]):
                        if "美白・エイジングケア" in subcategory:
                            return 1  # 美白関連の最優先
                        elif "美容サプリ" in subcategory:
                            return 2  # L-グルタチオン等
                    
                    elif any(kw in query_lower for kw in ["ニキビ", "吹き出物", "肌荒れ"]):
                        if "ニキビ" in subcategory:
                            return 1  # ニキビ治療薬最優先
                        elif "石鹸" in subcategory:
                            return 2  # プロポリス石鹸
                    
                    elif any(kw in query_lower for kw in ["まつ毛", "まつげ"]):
                        if "まつげ美容液" in subcategory:
                            return 1  # まつげ美容液最優先
                    
                    elif any(kw in query_lower for kw in ["日焼け", "紫外線", "uv"]):
                        if "日焼け止め" in subcategory:
                            return 1  # 日焼け止め最優先
                    
                    elif any(kw in query_lower for kw in ["むくみ", "利尿"]):
                        if "むくみ解消" in subcategory:
                            return 1  # むくみ解消薬最優先
                    
                    elif any(kw in query_lower for kw in ["バスト", "胸", "バストアップ"]):
                        if "バストアップ" in subcategory:
                            return 1  # バストアップ最優先
                    
                    # CSV順序に基づく基本優先度（美容商品内での順序）
                    csv_order = result.metadata.get('csv_order', 999) if result.metadata else 999
                    return 10 + csv_order  # 美容商品は10番台の優先度
                
                # 非美容商品は低い優先度
                return 500 + (result.metadata.get('csv_order', 999) if result.metadata else 999)
            
            # 美容優先でソート
            filtered_results.sort(key=beauty_priority_sort)
            
            logger.info(f"美容検索優先度適用: {len([r for r in filtered_results if r.category == '美容・スキンケア'])}件の美容商品を優先表示")
        
        # ダイエット検索の場合、ダイエット商品を優先的に上位表示
        elif is_diet_query:
            def diet_priority_sort(result):
                category = result.category if result.category else ""
                
                # ダイエット商品に高い優先度を与える
                if category == "ダイエット":
                    # サブカテゴリー別の詳細優先度
                    subcategory = result.metadata.get('subcategory', '').strip() if result.metadata else ""
                    
                    # 検索クエリに応じたサブカテゴリー優先度
                    if any(kw in query_lower for kw in ["食欲", "食べ過ぎ", "食べすぎ", "甘い物", "糖質", "炭水化物"]):
                        if "ダイエットサプリ" in subcategory:
                            return 1  # アーユスリム（食欲抑制）最優先
                        elif "便秘薬" in subcategory:
                            return 3  # トリファラ
                    
                    elif any(kw in query_lower for kw in ["脂肪", "脂っこい", "油", "太っ", "太り", "肥満", "体重"]):
                        if "ゼニカル・ダイエットピル" in subcategory:
                            return 1  # オルリガル（脂肪吸収阻害）最優先
                        elif "ダイエットサプリ" in subcategory:
                            return 2  # アーユスリム
                    
                    elif any(kw in query_lower for kw in ["便秘", "お通じ", "腸内", "デトックス", "排出", "便通"]):
                        if "便秘薬" in subcategory:
                            return 1  # トリファラ最優先
                        elif "ダイエットサプリ" in subcategory:
                            return 3  # アーユスリム
                    
                    elif any(kw in query_lower for kw in ["痩せ", "減量", "ダイエット"]):
                        # 一般的なダイエット検索ではバランス良く表示
                        if "ダイエットサプリ" in subcategory:
                            return 1  # アーユスリム
                        elif "ゼニカル・ダイエットピル" in subcategory:
                            return 2  # オルリガル
                        elif "便秘薬" in subcategory:
                            return 3  # トリファラ
                    
                    # CSV順序に基づく基本優先度（ダイエット商品内での順序）
                    csv_order = result.metadata.get('csv_order', 999) if result.metadata else 999
                    return 10 + csv_order  # ダイエット商品は10番台の優先度
                
                # 非ダイエット商品は低い優先度
                return 500 + (result.metadata.get('csv_order', 999) if result.metadata else 999)
            
            # ダイエット優先でソート
            filtered_results.sort(key=diet_priority_sort)
            
            logger.info(f"ダイエット検索優先度適用: {len([r for r in filtered_results if r.category == 'ダイエット'])}件のダイエット商品を優先表示")
        
        elif is_std_query:
            # 性病・感染症検索の優先度ソート
            def std_priority_sort(result):
                if result.category == "性病・感染症の治療薬":
                    subcategory = result.metadata.get('subcategory', '') if result.metadata else ''
                    
                    # 症状・病名別の詳細優先度
                    if any(kw in query_lower for kw in ["クラミジア"]):
                        if "クラミジア治療薬" in subcategory:
                            return 1  # クラミジア専用薬最優先
                        return 10  # その他感染症薬
                    
                    elif any(kw in query_lower for kw in ["淋病", "りんびょう"]):
                        if "淋病" in subcategory:
                            return 1  # 淋病専用薬最優先
                        elif "クラミジア治療薬" in subcategory:
                            return 2  # クラミジア薬（淋病にも有効）
                        return 10
                    
                    elif any(kw in query_lower for kw in ["梅毒", "ばいどく"]):
                        if "梅毒" in subcategory:
                            return 1  # 梅毒専用薬最優先
                        return 10
                    
                    elif any(kw in query_lower for kw in ["ヘルペス", "帯状疱疹", "水ぶくれ"]):
                        if "ヘルペス" in subcategory:
                            return 1  # ヘルペス専用薬最優先
                        return 10
                    
                    elif any(kw in query_lower for kw in ["カンジダ", "膣炎", "かゆみ"]):
                        if "カンジダ" in subcategory:
                            return 1  # カンジダ専用薬最優先
                        return 10
                    
                    elif any(kw in query_lower for kw in ["水虫", "いんきん", "真菌"]):
                        if "水虫・いんきんたむし" in subcategory:
                            return 1  # 水虫専用薬最優先
                        elif "カンジダ" in subcategory:
                            return 2  # 抗真菌薬
                        return 10
                    
                    elif any(kw in query_lower for kw in ["コンジローマ", "いぼ", "hpv"]):
                        if "コンジローマ" in subcategory:
                            return 1  # コンジローマ専用薬最優先
                        return 10
                    
                    elif any(kw in query_lower for kw in ["トリコモナス", "膣炎", "原虫"]):
                        if "トリコモナス" in subcategory:
                            return 1  # トリコモナス専用薬最優先
                        return 10
                    
                    elif any(kw in query_lower for kw in ["hiv", "エイズ", "prep"]):
                        if "HIV" in subcategory or "エイズ" in subcategory:
                            return 1  # HIV専用薬最優先
                        return 10
                    
                    # 一般的な性病・感染症検索：CSV順序に基づく優先度
                    csv_order = result.metadata.get('csv_order', 999) if result.metadata else 999
                    return csv_order
                
                # 非感染症薬は低い優先度
                return 500 + (result.metadata.get('csv_order', 999) if result.metadata else 999)
            
            # 感染症薬優先でソート
            filtered_results.sort(key=std_priority_sort)
            
            logger.info(f"性病・感染症検索優先度適用: {len([r for r in filtered_results if r.category == '性病・感染症の治療薬'])}件の感染症治療薬を優先表示")
        
        return filtered_results
    
    def _simple_text_search(self, query: str, top_k: int) -> List[SearchResult]:
        """シンプルな文字列検索（確実に動作する基本検索）"""
        results = []
        seen_products = set()  # 重複商品名を追跡
        query_lower = query.lower().strip()
        logger.info(f"シンプル文字列検索: '{query_lower}'")
        logger.info(f"検索対象データ数: {len(self.metadata_list)}")
        
        if not self.metadata_list:
            logger.warning("メタデータリストが空です")
            return results
        
        for i, metadata in enumerate(self.metadata_list):
            # 商品名の重複チェック
            product_name = metadata.get('name', '')
            if product_name in seen_products:
                logger.info(f"重複商品をスキップ: {product_name}")
                continue
            seen_products.add(product_name)
            # 全フィールドを文字列として結合（キーワードフィールドも含める）
            search_text = " ".join([
                metadata.get('category', ''),
                metadata.get('subcategory', ''),
                metadata.get('name', ''),
                metadata.get('effect', ''),
                metadata.get('ingredient', ''),
                metadata.get('description', ''),
                metadata.get('keywords', '')  # 検索キーワードも追加
            ]).lower().strip()
            
            # シンプルな含有チェック
            if query_lower in search_text:
                # より詳細なスコアリング
                score = 0.5  # 基本スコア
                
                # 重要フィールドでの一致をチェック
                if query_lower in metadata.get('ingredient', '').lower():
                    score = 0.95  # 有効成分一致
                elif query_lower in metadata.get('name', '').lower():
                    score = 0.90  # 商品名一致
                elif query_lower in metadata.get('effect', '').lower():
                    score = 0.85  # 効果一致
                elif query_lower in metadata.get('category', '').lower():
                    score = 0.80  # カテゴリ一致
                
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=score,
                    metadata=metadata
                )
                results.append(search_result)
                logger.info(f"マッチ: {metadata.get('name', '')} (スコア: {score})")
        
        # スコア順でソート
        results.sort(key=lambda x: (-x.similarity_score, x.metadata.get('csv_order', 999)))
        
        logger.info(f"シンプル検索結果: {len(results)}件")
        
        # ED検索の場合は最大5件まで返す（ED薬5種類すべてを表示するため）
        query_lower = query.lower()
        ed_keywords = [
            "勃起", "ed", "erectile", "性機能", "中折れ", "勃起不全",
            "バイアグラ", "シアリス", "レビトラ", "ステンドラ", "ザイデナ"
        ]
        is_ed_query = any(keyword in query_lower for keyword in ed_keywords)
        
        if is_ed_query and len(results) > 0:
            # ED検索の場合は最大5件まで返す
            return results[:min(5, len(results))]
        else:
            return results[:top_k]
    
    def _keyword_exact_search(self, query: str, top_k: int) -> List[SearchResult]:
        """キーワード完全一致検索（全フィールド対象）"""
        results = []
        seen_products = set()  # 重複商品名を追跡
        query_lower = query.lower().strip()
        logger.info(f"キーワード完全一致検索: '{query_lower}'")
        logger.info(f"検索対象データ数: {len(self.metadata_list)}")
        
        if not self.metadata_list:
            logger.warning("メタデータリストが空です")
            return results
        
        for i, metadata in enumerate(self.metadata_list):
            # 商品名の重複チェック
            product_name = metadata.get('name', '')
            if product_name in seen_products:
                logger.info(f"重複商品をスキップ: {product_name}")
                continue
            seen_products.add(product_name)
            # 検索対象フィールド
            search_fields = {
                'category': metadata.get('category', ''),           # カテゴリ名
                'subcategory': metadata.get('subcategory', ''),     # サブカテゴリ名  
                'name': metadata.get('name', ''),                   # 商品名
                'effect': metadata.get('effect', ''),               # 効果
                'ingredient': metadata.get('ingredient', ''),       # 有効成分
                'keywords': metadata.get('keywords', ''),           # 検索キーワード（新規追加）
                'description': metadata.get('description', '')      # 説明文
            }
            
            # 各フィールドでの一致度をチェック
            match_score = 0
            match_fields = []
            
            for field_name, field_value in search_fields.items():
                if not field_value:
                    continue
                    
                field_lower = field_value.lower().strip()
                
                # 1. 完全一致（最高スコア）
                if query_lower == field_lower:
                    match_score = 1.0
                    match_fields = [field_name]
                    logger.info(f"完全一致: {metadata.get('name', '')} [{field_name}]")
                    break
                
                # 2. 単語として含まれている（高スコア）
                elif self._is_word_match(query_lower, field_lower):
                    current_score = self._get_field_score(field_name)
                    if current_score > match_score:
                        match_score = current_score
                        match_fields = [field_name]
                    elif current_score == match_score:
                        match_fields.append(field_name)
                    logger.info(f"単語一致: {metadata.get('name', '')} [{field_name}] スコア:{current_score}")
                
                # 3. 部分一致（特に有効成分や商品名で重要）
                elif query_lower in field_lower and field_name in ['ingredient', 'name']:
                    current_score = self._get_field_score(field_name) * 0.8  # 少し低めのスコア
                    if current_score > match_score:
                        match_score = current_score
                        match_fields = [field_name]
                    logger.info(f"部分一致: {metadata.get('name', '')} [{field_name}] スコア:{current_score}")
            
            # マッチした場合のみ結果に追加
            if match_score > 0:
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=match_score,
                    metadata=metadata
                )
                results.append(search_result)
        
        # スコア順でソート（高スコア順）
        results.sort(key=lambda x: (-x.similarity_score, x.metadata.get('csv_order', 999)))
        
        logger.info(f"キーワード検索結果: {len(results)}件")
        return results[:top_k]
    
    def _is_word_match(self, query: str, text: str) -> bool:
        """クエリがテキスト内に単語として含まれているかチェック"""
        import re
        
        # 1. 単純な含有チェック
        if query in text:
            # 2. 区切り文字で分割して単語一致をチェック
            words = re.split(r'[、，,\s・\+\-\(\)（）]+', text)
            words = [word.strip() for word in words if word.strip()]
            
            # 完全一致する単語があるかチェック
            return query in [word.lower() for word in words]
        
        return False
    
    def _get_field_score(self, field_name: str) -> float:
        """フィールドの重要度に応じたスコア"""
        field_scores = {
            'keywords': 0.92,       # 検索キーワード（最重要級）
            'ingredient': 0.90,     # 有効成分
            'name': 0.88,           # 商品名
            'effect': 0.85,         # 効果
            'category': 0.80,       # カテゴリ名
            'subcategory': 0.75,    # サブカテゴリ名
            'description': 0.70     # 説明文
        }
        return field_scores.get(field_name, 0.5)
    
    def _vector_search(self, query: str, top_k: int) -> List[SearchResult]:
        """ベクトル検索（フォールバック用）"""
        try:
            # クエリの埋め込みベクトルを取得
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("クエリの埋め込み取得に失敗")
                return []
            
            # ベクトルを正規化
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # ED関連キーワードかチェック
            query_lower = query.lower()
            ed_keywords = [
                "勃起", "ed", "erectile", "性機能", "中折れ", "勃起不全",
                "バイアグラ", "シアリス", "レビトラ", "ステンドラ", "ザイデナ",
                "シルデナフィル", "タダラフィル", "バルデナフィル", "アバナフィル", "ウデナフィル",
                "性行為", "勃起力", "硬さ", "持続", "男性機能", "ed薬", "ed治療"
            ]
            is_ed_query = any(keyword in query_lower for keyword in ed_keywords)
            
            # ダイエット関連キーワードかチェック
            diet_keywords = [
                "ダイエット", "痩せ", "痩せたい", "体重", "減量", "肥満", "太っ", "太り",
                "食欲", "食べ過ぎ", "脂肪", "脂っこい", "便秘", "お通じ", "デトックス"
            ]
            is_diet_query = any(keyword in query_lower for keyword in diet_keywords)
            
            # 美容関連キーワードかチェック
            beauty_keywords = [
                "美容", "スキンケア", "美肌", "美白", "シミ", "シワ", "ニキビ", "吹き出物",
                "まつ毛", "まつげ", "日焼け", "紫外線", "むくみ", "バストアップ", "胸",
                "デトックス", "アンチエイジング", "エイジングケア", "肌荒れ", "毛穴"
            ]
            is_beauty_query = any(keyword in query_lower for keyword in beauty_keywords)
            
            # 便秘・消化器系関連キーワードかチェック
            constipation_keywords = [
                "便秘", "便通", "便秘改善", "便秘薬", "排便", "お腹のハリ", "腸内環境",
                "消化不良", "整腸", "便が出ない", "排便困難", "便通改善"
            ]
            is_constipation_query = any(keyword in query_lower for keyword in constipation_keywords)
            
            # 性病・感染症関連キーワードかチェック
            std_keywords = [
                "性病", "感染症", "クラミジア", "淋病", "梅毒", "ヘルペス", "カンジダ", 
                "トリコモナス", "コンジローマ", "hiv", "エイズ", "水虫", "いんきんたむし",
                "抗生物質", "抗ウイルス薬", "抗真菌薬", "std", "sti", "性感染症"
            ]
            is_std_query = any(keyword in query_lower for keyword in std_keywords)
            
            # 検索を実行（ED検索の場合はより多くの候補を取得）
            if is_ed_query or is_beauty_query or is_diet_query or is_constipation_query or is_std_query:
                search_k = min(self.index.ntotal, 35)  # カテゴリー特化検索では全商品を取得
            else:
                search_k = min(top_k * 3, self.index.ntotal)  # 通常は3倍の候補を取得
            scores, indices = self.index.search(query_vector, search_k)
            
            # 結果を整形
            results = []
            seen_products = set()  # 重複商品名を追跡
            
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 無効なインデックス
                    continue
                    
                metadata = self.metadata_list[idx]
                
                # 商品名の重複チェック
                product_name = metadata.get('name', '')
                if product_name in seen_products:
                    logger.info(f"重複商品をスキップ: {product_name}")
                    continue
                seen_products.add(product_name)
                
                # ダイエット検索の場合、ダイエット商品にスコアボーナス
                adjusted_score = float(score)
                if is_diet_query and metadata.get('category') == 'ダイエット':
                    # サブカテゴリー別の詳細ボーナス
                    subcategory = metadata.get('subcategory', '').strip()
                    
                    # 検索クエリに応じた追加ボーナス
                    if any(kw in query_lower for kw in ["食欲", "食べ過ぎ", "甘い物"]) and "ダイエットサプリ" in subcategory:
                        adjusted_score += 0.15  # 食欲抑制関連の大幅ボーナス
                    elif any(kw in query_lower for kw in ["脂肪", "脂っこい", "太っ"]) and "ゼニカル・ダイエットピル" in subcategory:
                        adjusted_score += 0.15  # 脂肪吸収阻害関連の大幅ボーナス
                
                # 便秘検索の場合、便秘薬にスコアボーナス
                elif is_constipation_query and metadata.get('category') == 'ダイエット':
                    subcategory = metadata.get('subcategory', '').strip()
                    if "便秘薬" in subcategory:
                        adjusted_score += 0.20  # 便秘薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["便秘", "お通じ", "腸内"]) and "便秘薬" in subcategory:
                        adjusted_score += 0.15  # 便秘改善関連の大幅ボーナス
                    else:
                        adjusted_score += 0.10  # ダイエット商品全般のボーナス
                    
                    logger.info(f"ダイエット商品スコアボーナス: {metadata.get('name')} {score:.3f} -> {adjusted_score:.3f}")
                
                # 美容検索の場合、美容・スキンケア商品にスコアボーナス
                elif is_beauty_query and metadata.get('category') == '美容・スキンケア':
                    # サブカテゴリー別の詳細ボーナス
                    subcategory = metadata.get('subcategory', '').strip()
                    keywords = metadata.get('keywords', '').lower()
                    
                    # 検索クエリに応じた追加ボーナス
                    if any(kw in query_lower for kw in ["シミ", "美白"]) and "美白" in subcategory:
                        adjusted_score += 0.15  # 美白関連の大幅ボーナス
                    elif any(kw in query_lower for kw in ["ニキビ", "吹き出物"]) and "ニキビ" in subcategory:
                        adjusted_score += 0.15  # ニキビ関連の大幅ボーナス
                    elif any(kw in query_lower for kw in ["まつ毛", "まつげ"]) and "まつげ" in subcategory:
                        adjusted_score += 0.15  # まつげ関連の大幅ボーナス
                    else:
                        adjusted_score += 0.10  # 美容商品全般のボーナス
                    
                    logger.info(f"美容商品スコアボーナス: {metadata.get('name')} {score:.3f} -> {adjusted_score:.3f}")
                
                # 性病・感染症検索の場合、感染症治療薬にスコアボーナス
                elif is_std_query and metadata.get('category') == '性病・感染症の治療薬':
                    # サブカテゴリー別の詳細ボーナス
                    subcategory = metadata.get('subcategory', '').strip()
                    
                    # 検索クエリに応じた症状別ボーナス
                    if any(kw in query_lower for kw in ["クラミジア"]) and "クラミジア治療薬" in subcategory:
                        adjusted_score += 0.20  # クラミジア専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["淋病", "りんびょう"]) and "淋病" in subcategory:
                        adjusted_score += 0.20  # 淋病専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["梅毒", "ばいどく"]) and "梅毒" in subcategory:
                        adjusted_score += 0.20  # 梅毒専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["ヘルペス", "帯状疱疹"]) and "ヘルペス" in subcategory:
                        adjusted_score += 0.20  # ヘルペス専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["カンジダ", "膣炎"]) and "カンジダ" in subcategory:
                        adjusted_score += 0.20  # カンジダ専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["水虫", "いんきん"]) and "水虫" in subcategory:
                        adjusted_score += 0.20  # 水虫専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["コンジローマ", "いぼ"]) and "コンジローマ" in subcategory:
                        adjusted_score += 0.20  # コンジローマ専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["トリコモナス", "原虫"]) and "トリコモナス" in subcategory:
                        adjusted_score += 0.20  # トリコモナス専用薬の大幅ボーナス
                    elif any(kw in query_lower for kw in ["hiv", "エイズ", "prep"]) and ("HIV" in subcategory or "エイズ" in subcategory):
                        adjusted_score += 0.20  # HIV専用薬の大幅ボーナス
                    else:
                        adjusted_score += 0.10  # 感染症薬全般のボーナス
                    
                    logger.info(f"感染症治療薬スコアボーナス: {metadata.get('name')} {score:.3f} -> {adjusted_score:.3f}")
                
                search_result = SearchResult(
                    product_name=metadata.get('name', ''),
                    url=metadata.get('url', ''),
                    price=metadata.get('price', ''),
                    description=metadata.get('description', ''),
                    category=metadata.get('category', ''),
                    similarity_score=adjusted_score,
                    metadata=metadata
                )
                results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"ベクトル検索エラー: {e}")
            return []

    def get_embedding(self, text: str) -> List[float]:
        """テキストの埋め込みベクトルを取得"""
        try:
            response = self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"埋め込み取得エラー: {e}")
            return []

    def load_or_create_index(self):
        """インデックスをロードまたは作成"""
        if self._index_exists():
            logger.info("既存のインデックスをロード中...")
            self._load_index()
        else:
            logger.info("新しいインデックスを作成中...")
            self._create_index_from_csv()

    def _index_exists(self) -> bool:
        """インデックスファイルが存在するかチェック"""
        return (os.path.exists(self.index_file) and 
                os.path.exists(self.metadata_file) and 
                os.path.exists(self.documents_file))

    def _load_index(self):
        """既存のインデックスをロード"""
        try:
            # FAISSインデックスをロード
            self.index = faiss.read_index(self.index_file)
            
            # メタデータをロード
            with open(self.metadata_file, 'rb') as f:
                self.metadata_list = pickle.load(f)
            
            # ドキュメントをロード
            with open(self.documents_file, 'rb') as f:
                self.documents = pickle.load(f)
            
            logger.info(f"インデックスロード完了: {self.index.ntotal}件のドキュメント")
        except Exception as e:
            logger.error(f"インデックスロードエラー: {e}")
            raise

    def _create_index_from_csv(self):
        """CSVファイルからインデックスを作成"""
        try:
            if not os.path.exists(self.csv_file):
                logger.error(f"CSVファイルが見つかりません: {self.csv_file}")
                raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_file}")
            
            # CSVデータを読み込み
            products = []
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    # 各商品の情報をまとめる
                    product_text = f"""
                    カテゴリ: {row.get('カテゴリ名', '')}
                    サブカテゴリ: {row.get('サブカテゴリ名', '')}
                    商品名: {row.get('商品名', '')}
                    効果: {row.get('効果', '')}
                    有効成分: {row.get('有効成分', '')}
                    説明: {row.get('説明文', '')}
                    検索キーワード: {row.get('検索キーワード', '')}
                    """
                    
                    # メタデータを準備
                    metadata = {
                        'category': row.get('カテゴリ名', ''),
                        'subcategory': row.get('サブカテゴリ名', ''),
                        'name': row.get('商品名', ''),
                        'effect': row.get('効果', ''),
                        'ingredient': row.get('有効成分', ''),
                        'description': row.get('説明文', ''),
                        'keywords': row.get('検索キーワード', ''),  # 新規追加
                        'url': row.get('商品URL', ''),
                        'price': '',  # 価格情報は含めない
                        'csv_order': i
                    }
                    
                    products.append((product_text.strip(), metadata))
            
            if not products:
                logger.error("CSVからデータを読み込めませんでした")
                raise ValueError("CSVからデータを読み込めませんでした")
            
            logger.info(f"{len(products)}件の商品データを読み込みました")
            
            # 埋め込みベクトルを生成
            embeddings = []
            self.metadata_list = []
            self.documents = []
            
            for i, (text, metadata) in enumerate(products):
                logger.info(f"埋め込み生成中: {i+1}/{len(products)} - {metadata['name']}")
                
                embedding = self.get_embedding(text)
                if embedding:
                    embeddings.append(embedding)
                    self.metadata_list.append(metadata)
                    self.documents.append(text)
                else:
                    logger.warning(f"埋め込み生成失敗: {metadata['name']}")
            
            if not embeddings:
                logger.error("有効な埋め込みが生成されませんでした")
                raise ValueError("有効な埋め込みが生成されませんでした")
            
            # FAISSインデックスを作成
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)
            
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings_array)
            
            # インデックスを保存
            self._save_index()
            
            logger.info(f"インデックス作成完了: {self.index.ntotal}件のドキュメント")
            
        except Exception as e:
            logger.error(f"インデックス作成エラー: {e}")
            raise

    def _save_index(self):
        """インデックスを保存"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            
            # FAISSインデックスを保存
            faiss.write_index(self.index, self.index_file)
            
            # メタデータを保存
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata_list, f)
            
            # ドキュメントを保存
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info("インデックス保存完了")
            
        except Exception as e:
            logger.error(f"インデックス保存エラー: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """コレクション情報を取得（互換性のため）"""
        try:
            if self.index is None:
                return {
                    "status": "not_initialized",
                    "document_count": 0,
                    "index_exists": False
                }
            
            return {
                "status": "ready",
                "document_count": self.index.ntotal if self.index else 0,
                "index_exists": self.index is not None,
                "metadata_count": len(self.metadata_list),
                "index_dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"コレクション情報取得エラー: {e}")
            return {
                "status": "error",
                "error": str(e),
                "document_count": 0,
                "index_exists": False
            }

    def get_recommendations(self, query: str, context: str = "", top_k: int = 5) -> List[SearchResult]:
        """レコメンデーション（search_productsのエイリアス）"""
        # contextがある場合はクエリに追加
        if context:
            enhanced_query = f"{query} {context}"
        else:
            enhanced_query = query
        
        return self.search_products(enhanced_query, top_k)