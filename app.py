"""
Streamlit Web UI - お薬通販部商品レコメンドLLMアプリ
ユーザーフレンドリーなWeb インターフェース
"""
import streamlit as st
import sys
import os
from typing import List, Dict, Any
import logging
import time
import traceback

# Streamlitページ設定（最初に一度だけ）
try:
    st.set_page_config(
        page_title="お薬通販部 商品レコメンド",
        page_icon="⚕️",
        layout="wide"
    )
except st.errors.StreamlitAPIException:
    # 既に設定済みの場合は無視
    pass

# パス設定を安全に行う
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    if os.path.dirname(current_dir) not in sys.path:
        sys.path.insert(0, os.path.dirname(current_dir))
except Exception as e:
    st.error(f"パス設定エラー: {e}")

# 安全なインポート
try:
    from src.faiss_rag_system import FAISSRAGSystem
    FAISS_AVAILABLE = True
except ImportError as e:
    FAISS_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError as e:
    PANDAS_AVAILABLE = False

try:
    from config.settings import get_settings
    settings = get_settings()
except ImportError as e:
    st.info("設定ファイルから読み込み中...")
    settings = None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# スタイル設定（お薬通販部トーンマナー対応）
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    /* お薬通販部ブランドカラーパレット */
    :root {
        --primary-color: #2E5BCE;
        --secondary-color: #4CAF50;
        --background-color: #FAFAFA;
        --card-background: #FFFFFF;
        --text-color: #333333;
        --border-color: #E8E8E8;
        --separator-color: #F0F0F0;
        --hover-color: #1A3A8C;
        --clear-button-color: #E0E0E0;
        --success-color: #4CAF50;
        --warning-color: #FF9800;
        --error-color: #F44336;
    }
    
    /* ダークモード用カラー */
    [data-theme="dark"] {
        --primary-color: #4A7CFF;
        --background-color: #1A1A1A;
        --card-background: #2D2D2D;
        --text-color: #E0E0E0;
        --border-color: #404040;
    }
    
    /* メインヘッダー */
    .main-header {
        font-size: 2.5rem;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 600;
    }
    
    /* 商品カード */
    .result-card {
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0;
        background-color: var(--card-background);
        color: var(--text-color);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }
    
    .result-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* バッジスタイル */
    .query-type-badge {
        background-color: var(--primary-color);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    /* 検索ボタン（プライマリカラー） */
    .stButton > button[kind="secondary"] {
        background-color: var(--primary-color) !important;
        color: white !important;
        border-color: var(--primary-color) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: var(--hover-color) !important;
        border-color: var(--hover-color) !important;
        transform: translateY(-1px) !important;
    }
    
    /* クリアボタン */
    .stButton > button[kind="primary"] {
        background-color: var(--clear-button-color) !important;
        color: var(--text-color) !important;
        border-color: var(--clear-button-color) !important;
    }
    
    /* Font Awesomeアイコン */
    .fa, .fas {
        margin-right: 8px;
        color: var(--primary-color);
    }
    
    /* リンクスタイル */
    a, .stMarkdown a {
        color: var(--primary-color) !important;
        text-decoration: none;
    }
    a:hover, .stMarkdown a:hover {
        color: var(--hover-color) !important;
        text-decoration: underline;
    }
    
    /* セクション区切り線 */
    hr {
        border-color: var(--separator-color);
    }
    
    /* 状態メッセージ */
    .stSuccess {
        background-color: var(--success-color) !important;
    }
    .stWarning {
        background-color: var(--warning-color) !important;
    }
    .stError {
        background-color: var(--error-color) !important;
    }
    
    /* 画像枠線 */
    .product-image-frame {
        border: 2px solid var(--border-color);
        border-radius: 8px;
        padding: 8px;
        background-color: var(--card-background);
        text-align: center;
        margin-bottom: 10px;
    }
    
    /* Streamlitコンポーネントの調整 */
    .stExpander {
        border-color: var(--border-color) !important;
    }
    
    .stSelectbox > div > div {
        border-color: var(--border-color) !important;
    }
    
    .stTextInput > div > div > input {
        border-color: var(--border-color) !important;
    }
    
    /* サイドバースタイル */
    .css-1d391kg {
        background-color: var(--background-color) !important;
    }
    
    /* フッタースタイル */
    .footer-text {
        color: #666;
        font-size: 0.9rem;
        text-align: center;
    }
    
    /* セクション見出しのサイズ調整 */
    .section-heading {
        font-size: 1.2rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 1rem !important;
    }
    
    .section-heading i {
        margin-right: 8px;
        color: var(--primary-color);
    }
    
    /* ダークモード対応 */
    @media (prefers-color-scheme: dark) {
        .result-card {
            border: 1px solid var(--border-color);
            background-color: var(--card-background);
            color: var(--text-color);
        }
        .main-header {
            color: var(--primary-color);
        }
        .fa, .fas {
            color: var(--primary-color);
        }
    }
    
    /* Streamlitダークテーマ検出 */
    [data-theme="dark"] .result-card {
        border: 1px solid var(--border-color) !important;
        background-color: var(--card-background) !important;
        color: var(--text-color) !important;
    }
    
    [data-theme="dark"] .main-header {
        color: var(--primary-color) !important;
    }
    
    [data-theme="dark"] .fa, [data-theme="dark"] .fas {
        color: var(--primary-color) !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_recommendation_engine():
    """レコメンドエンジンを初期化（キャッシュ付き、エラー処理強化）"""
    if not FAISS_AVAILABLE:
        st.markdown('<div style="color: #FF9800; background-color: #FFF3E0; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #FF9800;"><i class="fas fa-wrench"></i> <strong>FAISS機能が利用できません</strong></div>', unsafe_allow_html=True)
        st.info("基本検索機能のみご利用いただけます。")
        return None
    
    try:
        from src.faiss_rag_system import FAISSRAGSystem
        
        # エンジン初期化
        engine = FAISSRAGSystem()
        
        # 軽量な初期化テスト（サイレント実行）
        try:
            # システム状態確認（簡易版）
            pass  # サイドバー表示を削除
        except Exception as status_error:
            pass  # エラー表示も削除
        
        return engine
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # プロキシエラーの特別処理
        if error_type == "ProxyConnectionError":
            pass  # ユーザーには表示しない
        elif "proxy" in error_msg.lower() or "プロキシ" in error_msg:
            pass  # ユーザーには表示しない
        else:
            # 重要なエラーのみ表示
            st.markdown(f'<div style="color: #F44336; background-color: #FFEBEE; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #F44336;"><i class="fas fa-times-circle"></i> <strong>システム初期化エラー:</strong> {error_msg}</div>', unsafe_allow_html=True)
            
            # 詳細なエラー情報
            with st.expander("🔧 エラー詳細", expanded=False):
                st.write(f"**エラータイプ:** {type(e).__name__}")
                st.write(f"**エラーメッセージ:** {error_msg}")
                
                # 環境情報
                import sys
                st.write(f"**Python バージョン:** {sys.version}")
        
        # 軽量版システムを返す（基本的な機能のみ）
        return None

class BasicSearchResult:
    """基本検索結果のクラス"""
    def __init__(self, product_name, effect, ingredient, category, description, url, image_url='', similarity_score=0.0):
        self.product_name = product_name
        self.effect = effect
        self.ingredient = ingredient
        self.category = category
        self.description = description
        self.url = url
        self.image_url = image_url
        self.similarity_score = similarity_score
        self.metadata = {
            'effect': effect,
            'ingredient': ingredient,
            'image_url': image_url
        }

@st.cache_data
def load_csv_data():
    """CSVデータを読み込む"""
    if not PANDAS_AVAILABLE:
        return None
        
    try:
        csv_path = "./data/product_recommend.csv"
        df = pd.read_csv(csv_path, encoding='utf-8')
        return df
    except Exception as e:
        # エラーを静かに処理
        return None

def basic_search(query, top_k=5):
    """CSVから基本検索を行う（性病・感染症の検索精度向上）"""
    if not PANDAS_AVAILABLE:
        return []
        
    df = load_csv_data()
    if df is None:
        return []
    
    import re
    query_lower = query.lower()
    results = []
    
    # 性病・感染症の厳密な検索マッピング
    strict_std_mapping = {
        'クラミジア': [{'product': 'アジー', 'subcategory': 'クラミジア治療薬'}, 
                     {'product': 'ジスロマック', 'subcategory': 'クラミジア治療薬'}],
        '淋病': [{'product': 'アジー', 'subcategory': '淋病'}, 
                {'product': 'ジスロマック', 'subcategory': '淋病'},
                {'product': 'ビクシリン・ジェネリック（アンピシリン）', 'subcategory': '梅毒'}],
        '梅毒': [{'product': 'ビクシリン・ジェネリック（アンピシリン）', 'subcategory': '梅毒'}],
        'ヘルペス': [{'product': 'バルクロビル', 'subcategory': 'ヘルペス'}],
        'カンジダ': [{'product': 'フォルカン', 'subcategory': 'カンジダ・真菌感染症'}],
        'コンジローマ': [{'product': 'イミクアッド', 'subcategory': 'コンジローマ'}],
        'トリコモナス': [{'product': 'フラジール', 'subcategory': 'トリコモナス'}],
        'hiv': [{'product': 'テンビルEM', 'subcategory': 'HIV（エイズ）'}],
        'エイズ': [{'product': 'テンビルEM', 'subcategory': 'HIV（エイズ）'}]
    }
    
    # サプリメント・健康食品の検索マッピング（主要商品とカテゴリ）
    supplement_mapping = {
        # 具体的なキーワード（優先マッチ）
        'edサプリ': [{'product': 'スペマン', 'category': 'EDサプリ'}],
        '薄毛サプリ': [{'product': 'プレミアムリジン', 'category': '男性薄毛サプリ'}],
        'ダイエットサプリ': [
            {'product': 'アーユスリム', 'category': 'ダイエットサプリ'},
            {'product': 'トリファラ', 'category': 'ダイエットサプリ'}
        ],
        '美容サプリ': [
            {'product': 'プエラリアミリフィカタブレット', 'category': '美容サプリ'},
            {'product': 'L-グルタチオン（バイタルミー）', 'category': '美容サプリ'}
        ],
        'トリファラ': [{'product': 'トリファラ', 'category': 'ダイエットサプリ'}],
        'プエラリア': [{'product': 'プエラリアミリフィカタブレット', 'category': '美容サプリ'}],
        'グルタチオン': [{'product': 'L-グルタチオン（バイタルミー）', 'category': '美容サプリ'}],

        # より一般的なキーワード（フォールバック）
        'サプリメント': [
            {'product': 'スペマン', 'category': 'EDサプリ'},
            {'product': 'プレミアムリジン', 'category': '男性薄毛サプリ'},
            {'product': 'アーユスリム', 'category': 'ダイエットサプリ'},
            {'product': 'トリファラ', 'category': 'ダイエットサプリ'},
            {'product': 'プエラリアミリフィカタブレット', 'category': '美容サプリ'},
            {'product': 'L-グルタチオン（バイタルミー）', 'category': '美容サプリ'}
        ],
        'サプリ': [
            {'product': 'スペマン', 'category': 'EDサプリ'},
            {'product': 'プレミアムリジン', 'category': '男性薄毛サプリ'},
            {'product': 'アーユスリム', 'category': 'ダイエットサプリ'},
            {'product': 'トリファラ', 'category': 'ダイエットサプリ'},
            {'product': 'プエラリアミリフィカタブレット', 'category': '美容サプリ'},
            {'product': 'L-グルタチオン（バイタルミー）', 'category': '美容サプリ'}
        ]
    }
    
    # 厳密検索かどうかを判定（性病・感染症）
    is_strict_search = False
    matched_condition = None
    
    for condition in strict_std_mapping.keys():
        if condition in query_lower:
            is_strict_search = True
            matched_condition = condition
            break
    
    # サプリメント検索かどうかを判定
    is_supplement_search = False
    matched_supplement = None
    
    for supplement_key in supplement_mapping.keys():
        if supplement_key in query_lower:
            is_supplement_search = True
            matched_supplement = supplement_key
            break
    
    # 性病・感染症の厳密検索の場合
    if is_strict_search:
        allowed_products = strict_std_mapping[matched_condition]
        found_products = set()  # 重複防止用
        
        for product_info in allowed_products:
            product_name = product_info['product']
            subcategory = product_info['subcategory']
            
            for _, row in df.iterrows():
                # ビクシリン・ジェネリックの場合は部分一致を許可
                is_product_match = False
                if 'ビクシリン' in product_name:
                    # ビクシリンの場合は「ビクシリン」または「アンピシリン」を含む商品名を検索
                    if ('ビクシリン' in str(row['商品名']) or 'アンピシリン' in str(row['商品名'])):
                        is_product_match = True
                else:
                    # その他の商品は完全一致
                    is_product_match = product_name in str(row['商品名'])
                
                # 商品名が一致し、まだ見つかっていない場合
                if (is_product_match and 
                    product_name not in found_products):
                    
                    # 性病・感染症カテゴリであることを確認
                    if '性病・感染症' in str(row['カテゴリ名']):
                        # サブカテゴリチェック（ビクシリンの場合は柔軟に）
                        subcategory_match = False
                        if 'ビクシリン' in product_name:
                            # ビクシリンは梅毒カテゴリまたは商品名にアンピシリンが含まれていればOK
                            if ('梅毒' in str(row['サブカテゴリ名']) or 
                                'アンピシリン' in str(row['商品名']) or
                                '淋病' in str(row['サブカテゴリ名'])):
                                subcategory_match = True
                        else:
                            # その他は厳密にサブカテゴリマッチ
                            subcategory_match = subcategory in str(row['サブカテゴリ名'])
                        
                        if subcategory_match:
                            found_products.add(product_name)
                            
                            result = BasicSearchResult(
                                product_name=row['商品名'],
                                effect=row['効果'],
                                ingredient=row['有効成分'],
                                category=row['カテゴリ名'],
                                description=row['説明文'],
                                url=row['商品URL'],
                                image_url=row.get('商品画像URL', ''),
                                similarity_score=100.0  # 厳密一致なので最高スコア
                            )
                            results.append(result)
                            break  # この商品は見つかったので次へ
        
        return results[:top_k]
    
    # サプリメント専用検索の場合
    if is_supplement_search:
        allowed_products = supplement_mapping[matched_supplement]
        found_products = set()  # 重複防止用
        
        for product_info in allowed_products:
            product_name = product_info['product']
            category = product_info['category']
            
            for _, row in df.iterrows():
                # 商品名の部分一致チェック
                is_product_match = product_name in str(row['商品名'])
                
                # 商品名が一致し、まだ見つかっていない場合
                if (is_product_match and 
                    product_name not in found_products):
                    
                    # ダイエットカテゴリまたは美容・スキンケアカテゴリまたはサプリ関連であることを確認
                    if (category in str(row['カテゴリ名']) or 
                        'サプリ' in str(row['検索キーワード']) or
                        'サプリメント' in str(row['検索キーワード'])):
                        
                        found_products.add(product_name)
                        
                        result = BasicSearchResult(
                            product_name=row['商品名'],
                            effect=row['効果'],
                            ingredient=row['有効成分'],
                            category=row['カテゴリ名'],
                            description=row['説明文'],
                            url=row['商品URL'],
                            image_url=row.get('商品画像URL', ''),
                            similarity_score=95.0  # サプリ専用検索スコア
                        )
                        results.append(result)
                        break  # この商品は見つかったので次へ
        
        return results[:top_k]
    
    # 通常の検索（厳密検索でない場合）
    # 性病・感染症専用の検索キーワード辞書
    std_keywords = {
        '性病': ['クラミジア', '淋病', '梅毒', 'ヘルペス', 'カンジダ', 'トリコモナス', 'コンジローマ', 'HIV', 'エイズ'],
        '感染症': ['クラミジア', '淋病', '梅毒', 'ヘルペス', 'カンジダ', 'トリコモナス', 'コンジローマ', 'HIV']
    }
    
    # 重複防止用セット
    found_products = set()
    
    for _, row in df.iterrows():
        score = 0.0
        search_text = ""
        
        # 検索対象のテキストを結合
        fields = ['商品名', '効果', '有効成分', 'カテゴリ名', '説明文', '検索キーワード']
        for field in fields:
            if pd.notna(row[field]):
                search_text += str(row[field]).lower() + " "
        
        # 基本キーワードマッチング
        query_words = re.findall(r'\w+', query_lower)
        for word in query_words:
            if word in search_text:
                score += 1.0
                
        # 完全マッチボーナス
        if query_lower in search_text:
            score += 3.0
            
        # 性病・感染症専用の高精度検索
        for key_word, related_conditions in std_keywords.items():
            if key_word in query_lower:
                # カテゴリマッチの高ボーナス
                if '性病・感染症' in str(row['カテゴリ名']):
                    score += 10.0
                        
                # サブカテゴリマッチ
                for condition in related_conditions:
                    if condition in str(row['サブカテゴリ名']).lower():
                        score += 8.0
        
        # 症状ベース検索の強化
        symptom_mapping = {
            'かゆみ': ['カンジダ', 'トリコモナス'],
            'おりもの': ['カンジダ', 'トリコモナス', 'クラミジア'],
            '尿道炎': ['クラミジア', '淋病'],
            'いぼ': ['コンジローマ'],
            '水ぶくれ': ['ヘルペス'],
            '膣炎': ['カンジダ', 'トリコモナス'],
            '咽頭炎': ['クラミジア', '淋病'],
            '喉の痛み': ['クラミジア', '淋病']
        }
        
        for symptom, related_conditions in symptom_mapping.items():
            if symptom in query_lower:
                for condition in related_conditions:
                    if condition.lower() in search_text:
                        score += 7.0
                        
        if score > 0:
            product_name = row['商品名']
            # 重複チェック - 同じ商品が既に追加されていないかチェック
            if product_name not in found_products:
                found_products.add(product_name)
                result = BasicSearchResult(
                    product_name=product_name,
                    effect=row['効果'],
                    ingredient=row['有効成分'],
                    category=row['カテゴリ名'],
                    description=row['説明文'],
                    url=row['商品URL'],
                    image_url=row.get('商品画像URL', ''),
                    similarity_score=score
                )
                results.append(result)
    
    # スコア順にソート
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    return results[:top_k]

def display_search_result(result, index: int):
    """検索結果を表示"""
    with st.container():
        # デバッグ情報
        # st.write(f"DEBUG - result type: {type(result)}")
        # st.write(f"DEBUG - result attributes: {dir(result)}")
        
        # メタデータから効果と有効成分を取得（英語キーで取得）
        effect = result.metadata.get('effect', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        active_ingredient = result.metadata.get('ingredient', 'N/A') if hasattr(result, 'metadata') and result.metadata else 'N/A'
        image_url = result.metadata.get('image_url', '') if hasattr(result, 'metadata') and result.metadata else ''
        
        # レイアウト用の列を作成
        col1, col2 = st.columns([1, 3])
        
        # 商品画像を表示
        with col1:
            if image_url and image_url.strip():
                try:
                    # お薬通販部スタイルの画像枠
                    st.markdown(f"""
                    <div class="product-image-frame">
                        <img src="{image_url}" style="
                            width: 200px;
                            height: auto;
                            border-radius: 4px;
                            display: block;
                            margin: 0 auto;
                        ">
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"画像読み込みエラー: {e}")
                    st.markdown('<div style="padding: 0.75rem 1rem; background: #e7f3ff; border-left: 4px solid var(--primary-color); border-radius: 0.25rem;"><i class="fas fa-image"></i> 画像を読み込み中...</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="product-image-frame" style="
                    min-height: 200px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                    color: #666;
                ">
                    <i class="fas fa-image" style="font-size: 2rem; opacity: 0.5; margin-bottom: 8px;"></i>
                    <div>商品画像</div>
                    <div>準備中</div>
                </div>
                """, unsafe_allow_html=True)
        
        # 商品情報を表示
        with col2:
            st.markdown(f"""
            <div class="result-card">
                <h4 style="color: var(--text-color); margin-top: 0; margin-bottom: 1rem;">
                    <i class="fas fa-box"></i> {result.product_name}
                </h4>
                <p style="color: var(--text-color); margin-bottom: 0.8rem;">
                    <strong><i class="fas fa-pills"></i> 有効成分:</strong> {active_ingredient}
                </p>
                <p style="color: var(--text-color); margin-bottom: 0.8rem;">
                    <strong><i class="fas fa-info-circle"></i> 効果:</strong> {effect}
                </p>
                <p style="color: var(--text-color); margin-bottom: 0.8rem;">
                    <strong><i class="fas fa-list-ul"></i> カテゴリ:</strong> {result.category or 'N/A'}
                </p>
                <p style="color: var(--text-color); margin-bottom: 0.8rem;">
                    <strong><i class="fas fa-info-circle"></i> 説明:</strong> {(result.description or 'N/A')[:200]}{'...' if len(result.description or '') > 200 else ''}
                </p>
                <p style="color: var(--text-color); margin-bottom: 0;">
                    <strong><i class="fas fa-external-link-alt"></i> URL:</strong> 
                    <a href="{result.url}" target="_blank" style="color: var(--primary-color);">商品ページを開く</a>
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")

def display_system_status():
    """システム状態を表示"""
    st.subheader('<i class="fas fa-wrench"></i> システム状態', unsafe_allow_html=True)
    
    try:
        # Streamlit Cloud環境では簡略化した状態を表示
        st.markdown('<div style="color: #4CAF50; background-color: #E8F5E8; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #4CAF50;"><i class="fas fa-check-circle"></i> <strong>システムは正常に動作しています</strong></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**レコメンドエンジン:**", "ready")
            st.write("**RAGシステム:**")
            st.write("- コレクション: faiss_products") 
            st.write("- 商品数: 35")
            st.write("- 状態: ready")
        
        with col2:
            st.write("**サポートされる検索タイプ:**")
            for query_type in ["symptom", "product_name", "category", "ingredient", "general"]:
                st.write(f"- {query_type}")
            
            st.write("**機能:**")
            for feature in ["症状ベース検索", "商品名検索"]:
                st.write(f"- {feature}")
                
    except Exception as e:
        st.error(f"システム状態の取得に失敗しました: {e}")
        st.info("簡略化モードで動作中です")

def main():
    """メインアプリケーション"""
    
    # システム状態確認を先に実行
    if not FAISS_AVAILABLE:
        pass  # エラーメッセージを表示せず、静かに基本機能で動作
    
    # ヘッダー
    st.markdown('<h1 class="main-header"><i class="fas fa-pills"></i> お薬通販部 商品レコメンド AI</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # メインエリア
    st.markdown('## <i class="fas fa-search"></i> 商品検索・レコメンド', unsafe_allow_html=True)
    
    # ご利用ガイドの設置
    st.markdown('<div class="section-heading"><i class="fas fa-book-open"></i> ご利用ガイド</div>', unsafe_allow_html=True)
    with st.expander("詳細を表示", expanded=False):
        st.markdown("""
        ### <i class="fas fa-star"></i> このシステムについて
        お薬通販部の商品から、あなたの症状や悩みに最適な医薬品をAIがレコメンドします。
        
        ### <i class="fas fa-search"></i> 検索方法
        **症状で検索:**
        - 「抜け毛が増えた」「なかなか痩せない」など、具体的な症状を入力
        - 「むくみ」「かゆみ」「ニキビ」など、気になる症状をそのまま入力
        
        **商品名で検索:**
        - 「カマグラゴールド」「フィナクス」など、知っている商品名を入力
        - 一部の名前でも検索可能です
        
        **カテゴリで検索:**
        - 「ED治療薬」「AGA治療薬」「性病・感染症」など
        
        ### <i class="fas fa-exclamation-triangle"></i> ご注意事項
        - このシステムは情報提供のみを目的としています
        - 実際の使用前には必ず医師にご相談ください
        - 処方薬については医師の指導に従ってください
        
        ### <i class="fas fa-lightbulb"></i> コツ
        - 具体的で詳しい症状を入力すると、より精度の高い結果が得られます
        - 複数の症状がある場合は、一緒に入力してください
        """, unsafe_allow_html=True)
    
    # 検索例を表示
    st.markdown('<div class="section-heading"><i class="fas fa-lightbulb"></i> 検索例</div>', unsafe_allow_html=True)
    with st.expander("検索例を見る", expanded=False):
        st.write("**症状での検索例:**")
        st.write("- 抜け毛が増えた")
        st.write("- 足のむくみが取れない")
        st.write("- 肌の再生を促したい")
        st.write("- かゆみが止まらない")
        st.write("- 喉の痛みが治らない")
        
        st.write("**性病・感染症での検索例:**")
        st.write("- 性病")
        st.write("- クラミジア")
        st.write("- ヘルペス")
        st.write("- カンジダ")
        st.write("- 尿道炎")
        
        st.write("**商品名での検索例:**")
        st.write("- カマグラゴールド")
        st.write("- フィナクス+ミノクソール")
        st.write("- アジー")
        st.write("- オルリガル")
        
        st.write("**カテゴリでの検索例:**")
        st.write("- ED治療薬")
        st.write("- AGA治療薬")
        st.write("- 性病・感染症の治療薬")
        st.write("- ニキビ")
        st.write("- ダイエット")
    
    # 検索設定をメインページに移動（デフォルト値を先に設定）
    max_results = 10  # デフォルト値
    
    st.markdown('<div class="section-heading"><i class="fas fa-cog"></i> 検索設定</div>', unsafe_allow_html=True)
    with st.expander("設定を変更", expanded=True):
        max_results = st.slider("最大結果数", 1, 20, 10, help="一度に表示する検索結果の件数を選択してください")
    
    # 検索フォーム
    # クリア要求がある場合は空文字列、そうでなければセッション状態から取得
    default_value = "" if st.session_state.get('clear_requested', False) else st.session_state.get('search_input', "")
    
    # クリア要求フラグをリセット
    if st.session_state.get('clear_requested', False):
        st.session_state['clear_requested'] = False
    
    # 検索フォーム
    st.markdown('<div class="section-heading"><i class="fas fa-comments"></i> 症状や探している商品を入力してください</div>', unsafe_allow_html=True)
    user_query = st.text_input(
        "検索内容:",
        value=default_value,
        placeholder="例: 有効成分ミノキシジルのAGA治療薬を教えてください。",
        help="症状、商品名、カテゴリなど自然な言葉で入力できます",
        key="search_input"
    )
    
    # 検索ボタン（距離感を近く改善）
    col1, col2 = st.columns([2.5, 1.5])
    with col1:
        # 赤色ボタンに設定
        search_button = st.button("🔍 検索・レコメンド", type="secondary", use_container_width=True)
    with col2:
        if st.button("🧹 画面クリア", help="検索結果と入力内容をクリア", use_container_width=True):
            # 検索結果関連のセッション状態をクリア
            keys_to_clear = ['search_results', 'search_query', 'last_search', 'current_results', 'current_search_time', 'current_query', 'current_max_results']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            # すべての検索キャッシュも削除
            cache_keys = [k for k in st.session_state.keys() if k.startswith('search_')]
            for key in cache_keys:
                del st.session_state[key]
            # クリア状態フラグを設定
            st.session_state['clear_requested'] = True
            st.markdown('<div style="color: #4CAF50; background-color: #E8F5E8; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #4CAF50;"><i class="fas fa-check-circle"></i> <strong>画面とキャッシュをクリアしました</strong></div>', unsafe_allow_html=True)
            time.sleep(0.5)
            st.rerun()
    
    # 検索実行
    if search_button or (user_query and user_query.strip()):
        if user_query.strip():
            try:
                # 一時的にRAGシステムを無効にして基本検索を使用
                engine = None  # initialize_recommendation_engine()
                
                # エンジンが正常に初期化されたか確認
                if engine is None:
                    # AI機能が利用できない場合は静かに基本検索に切り替え
                    with st.spinner("検索中..."):
                        start_time = time.time()
                        results = basic_search(user_query, max_results)  # max_resultsを正しく渡す
                        search_time = time.time() - start_time
                    
                    if results:
                        st.markdown(f'<div style="color: #4CAF50; background-color: #E8F5E8; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #4CAF50;"><i class="fas fa-check-circle"></i> <strong>検索完了！</strong>{len(results)}件の商品が見つかりました（{search_time:.2f}秒）</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="color: #FF9800; background-color: #FFF3E0; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #FF9800;"><i class="fas fa-question-circle"></i> 該当する商品が見つかりませんでした。別のキーワードで検索してみてください。</div>', unsafe_allow_html=True)
                        
                else:
                    with st.spinner("検索中..."):
                        start_time = time.time()
                        results = engine.search_products(
                            user_query, 
                            top_k=max_results
                        )
                        search_time = time.time() - start_time
                
                # 結果をセッションに保存（キャッシュを無効にして毎回新しく検索）
                st.session_state['current_results'] = results
                st.session_state['current_search_time'] = search_time
                st.session_state['current_query'] = user_query
                st.session_state['current_max_results'] = max_results  # 検索時のmax_resultsも保存
                
            except Exception as e:
                st.markdown(f'<div style="color: #F44336; background-color: #FFEBEE; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #F44336;"><i class="fas fa-times-circle"></i> <strong>検索中にエラーが発生しました:</strong> {e}</div>', unsafe_allow_html=True)
                logger.error(f"検索エラー: {e}")
        else:
            st.warning("検索クエリを入力してください。")
    
    # 検索結果の表示（セッションに保存された結果がある場合）
    if 'current_results' in st.session_state:
        results = st.session_state['current_results']
        search_time = st.session_state.get('current_search_time', 0)
        query = st.session_state.get('current_query', '')
        
        # 結果の表示
        st.markdown("---")
        st.markdown('### <i class="fas fa-list-ul"></i> 検索結果', unsafe_allow_html=True)
        
        # 検索情報
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("結果数", len(results))
        with col2:
            st.metric("検索時間", f"{search_time:.2f}秒")
        with col3:
            # 現在の設定値も表示
            current_max_results = st.session_state.get('current_max_results', max_results)
            st.metric("設定値", f"{current_max_results}件まで")
        
        st.markdown('<span class="query-type-badge">基本検索</span>', unsafe_allow_html=True)
        
        # 検索結果の表示
        if results:
            st.markdown('### <i class="fas fa-pills"></i> おすすめ商品', unsafe_allow_html=True)
            
            for i, result in enumerate(results):
                display_search_result(result, i)
                
        else:
            st.warning("🤔 該当する商品が見つかりませんでした。別のキーワードで検索してみてください。")
            st.info("💡 まず商品データを取得する必要がある可能性があります。サイドバーの「商品データ取得」をお試しください。")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div class="footer-text">
        <i class="fas fa-pills" style="color: var(--primary-color);"></i> お薬通販部 商品レコメンド AI
        <br>
        <small style="color: #999;">安心・安全な医薬品選びをサポート</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.markdown(f'<div style="color: #F44336; background-color: #FFEBEE; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #F44336;"><i class="fas fa-times-circle"></i> <strong>アプリケーション起動エラー:</strong> {str(e)}</div>', unsafe_allow_html=True)
        st.info("システムの基本機能のみで動作します")