# API設計書 - お薬通販部商品レコメンドAI

## 📋 **API概要**

本アプリケーションは主にStreamlitのWeb UIを中心に動作します。
内部的には下記のAPI構造を持ちますが、FAISS/AI連携は現状「未使用/オプション」です。

---

## 🔍 **検索API仕様**

### 1. 基本検索API

#### `basic_search(query: str, search_type: str) -> pd.DataFrame`

**概要**: 商品データベースから条件に一致する商品を検索

**パラメータ**:
```python
query: str          # 検索クエリ
search_type: str    # 検索タイプ ("症状", "商品名", "カテゴリ")
```

**戻り値**:
```python
pd.DataFrame        # 検索結果（商品データフレーム）
```

**処理フロー**:
```python
1. supplement_mappingチェック
2. 検索タイプ別処理実行
3. 重複除去
4. 結果返却
```

**実装例**:
```python
def basic_search(query, search_type):
    global products_df
    
    # supplement_mappingチェック
    if query in supplement_mapping:
        category = supplement_mapping[query]
        results = products_df[products_df['カテゴリ'] == category]
        return results.drop_duplicates(subset=['商品名'])
    
    # 通常検索
    if search_type == "症状":
        results = products_df[products_df['効果'].str.contains(query, case=False, na=False)]
    elif search_type == "商品名":
        results = products_df[products_df['商品名'].str.contains(query, case=False, na=False)]
    
    return results.drop_duplicates(subset=['商品名'])
```

### 2. カテゴリ検索API

#### `category_search(selected_category: str) -> pd.DataFrame`

**概要**: 指定されたカテゴリの全商品を取得

**パラメータ**:
```python
selected_category: str    # 選択されたカテゴリ名
```

**戻り値**:
```python
pd.DataFrame             # カテゴリに属する商品一覧
```

**実装例**:
```python
def category_search(selected_category):
    global products_df
    
    if selected_category == "すべて":
        return products_df
    
    results = products_df[products_df['カテゴリ'] == selected_category]
    return results.drop_duplicates(subset=['商品名'])
```

## 🗄️ **データ操作API**

### 3. データロードAPI

#### `load_data() -> pd.DataFrame`

**概要**: 商品データベース（CSV）をロードして前処理

**戻り値**:
```python
pd.DataFrame    # 商品データフレーム
```

**エラーハンドリング**:
```python
try:
    df = pd.read_csv('data/product_recommend.csv')
    return df
except FileNotFoundError:
    st.error("データファイルが見つかりません")
    return pd.DataFrame()
except Exception as e:
    st.error(f"データロードエラー: {e}")
    return pd.DataFrame()
```

### 4. カテゴリ取得API

#### `get_categories() -> List[str]`

**概要**: 利用可能な全カテゴリリストを取得

**戻り値**:
```python
List[str]    # カテゴリ名のリスト
```

**実装例**:
```python
def get_categories():
    global products_df
    categories = ['すべて'] + sorted(products_df['カテゴリ'].unique().tolist())
    return categories
```

## ⚡ **FAISS/AI検索API（オプション/拡張用）**

- FAISS/AI連携は現状未使用・オプションです。今後の拡張用サンプルとして記載しています。

#### `setup_rag_system() -> Optional[FAISSRAGSystem]`
#### `faiss_search(rag_system: FAISSRAGSystem, query: str, k: int = 5) -> List[Dict]`

---

## 📊 **データ形式仕様**

### 商品データ形式（例）
```python
{
    "商品名": str,      # 商品名（必須）
    "効果": str,        # 効果・効能
    "成分": str,        # 主要成分
    "カテゴリ": str,    # 商品カテゴリ（必須）
    "説明": str,        # 詳細説明
    "URL": str          # 商品ページURL
}
```

---

## 🔧 **内部ユーティリティAPI**

### 入力検証API

#### `validate_input(query: str) -> bool`

**概要**: ユーザー入力の妥当性検証

**パラメータ**:
```python
query: str    # 検証対象文字列
```

**戻り値**:
```python
bool         # 妥当性（True: 有効, False: 無効）
```

**検証ルール**:
```python
def validate_input(query):
    # 文字列長チェック
    if len(query) > 100:
        return False
    
    # 空文字チェック
    if not query.strip():
        return False
    
    # 危険文字チェック
    dangerous_chars = ['<', '>', '"', "'", ';']
    if any(char in query for char in dangerous_chars):
        return False
    
    return True
```

### 重複除去API

#### `remove_duplicates(df: pd.DataFrame) -> pd.DataFrame`

**概要**: 検索結果の重複商品を除去

**パラメータ**:
```python
df: pd.DataFrame    # 検索結果データフレーム
```

**戻り値**:
```python
pd.DataFrame       # 重複除去後データフレーム
```

**実装例**:
```python
def remove_duplicates(df):
    return df.drop_duplicates(subset=['商品名'], keep='first')
```

## ⚙️ **設定管理API**

### 設定取得API

#### `get_config() -> Dict`

**概要**: アプリケーション設定を取得

**戻り値**:
```python
Dict    # 設定辞書
```

**設定項目**:
```python
{
    "use_faiss": bool,              # FAISS使用フラグ
    "max_results": int,             # 最大検索結果数
    "cache_enabled": bool,          # キャッシュ有効フラグ
    "debug_mode": bool,             # デバッグモード
    "openai_api_key": str          # OpenAI APIキー
}
```

### supplement_mapping取得API

#### `get_supplement_mapping() -> Dict[str, str]`

**概要**: サプリメント専用マッピングを取得

**戻り値**:
```python
Dict[str, str]    # サプリメントマッピング
```

**データ例**:
```python
{
    'スペマン': 'EDサプリ',
    'プレミアムリジン': 'AGA治療薬'
}
```

## 🛡️ **エラーハンドリング仕様**

### エラーレスポンス形式（例）
```python
{
    "error": bool,              # エラーフラグ
    "error_code": str,          # エラーコード
    "error_message": str,       # エラーメッセージ
    "details": Dict            # 詳細情報
}
```

**エラーコード一覧**:
```python
ERROR_CODES = {
    "DATA_NOT_FOUND": "データファイルが見つかりません",
    "INVALID_INPUT": "入力値が無効です", 
    "SEARCH_ERROR": "検索処理中にエラーが発生しました",
    "FAISS_ERROR": "FAISS検索でエラーが発生しました",
    "CONFIG_ERROR": "設定エラーです"
}
```

---

## 📊 **パフォーマンス・制限値（目安）**

- レスポンス時間目標や制限値は現状未設定。今後の運用・拡張で調整予定。

---

## 🔄 **API使用例**

### 基本的な検索フロー
```python
# 1. データロード
products_df = load_data()

# 2. 検索実行
query = "ED改善"
search_type = "症状"
results = basic_search(query, search_type)

# 3. 結果表示
for _, product in results.iterrows():
    print(f"商品名: {product['商品名']}")
    print(f"効果: {product['効果']}")
```

### カテゴリ検索フロー
```python
# 1. カテゴリ一覧取得
categories = get_categories()

# 2. カテゴリ検索
selected = "EDサプリ"
results = category_search(selected)

# 3. 結果処理
print(f"検索結果: {len(results)}件")
```

---

## 📝 **API変更履歴**

### v1.0.0 (2025/11/11)
- 基本検索API実装
- カテゴリ検索API実装
- supplement_mapping対応
- 重複除去機能追加
- FAISS検索API実装（オプション/拡張用）