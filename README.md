# 💊 お薬通販部 商品レコメンドAI

お薬通販部の商品データを活用した、ユーザーフレンドリーなWeb商品検索・レコメンドアプリです。

---

## 📝 概要

- 症状や商品名、カテゴリ、サプリメント名などから、最適な商品を素早く検索・レコメンド
- シンプルなUI・ブランドカラー（#073084ブルー、#1CA936グリーン）・ダークモード対応
- 開発者向け情報や不要な案内は非表示、一般ユーザー向けに最適化

---

## 🚀 主な機能

- **症状ベース検索**：自然な日本語で症状を入力して検索
- **性病・感染症専用検索**：クラミジア、ヘルペス、カンジダ等の厳密マッチ
- **商品名・カテゴリ検索**：部分一致・完全一致対応
- **サプリメント専用検索**：EDサプリ、薄毛サプリ、ダイエットサプリ、美容サプリ
- **重複防止**：同一商品の重複表示なし
- **ブランドカラーUI**：お薬通販部公式カラーに準拠
- **ダークモード対応**：自動切替
- **エラーハンドリング**：ユーザー向けに簡潔なエラー表示

---

## 🛠️ 技術スタック

- Python 3.11+
- Streamlit（Web UI）
- pandas（データ処理）
- FAISS（ベクトル検索、現状は未使用/オプション）

---

## 📁 プロジェクト構成

```
okusuri-tuuhanbu-recommend/
├── app.py                # メインStreamlitアプリ
├── requirements.txt      # 依存パッケージ
├── .env.example         # 環境変数テンプレート（AI機能用、通常不要）
├── config/
│   └── settings.py       # アプリ設定
├── src/
│   ├── faiss_rag_system.py   # FAISS連携（オプション）
│   └── ...
├── data/
│   └── product_recommend.csv # 商品データベース
└── .streamlit/
    └── config.toml       # Streamlit設定
```

---

## ⚡ セットアップ・起動方法

### 1. 必要環境
- Python 3.11以上
- pip

### 2. インストール

```bash
# リポジトリ取得
git clone https://github.com/ts1979s-commits/okusuri-tuuhanbu-recommend.git
cd okusuri-tuuhanbu-recommend

# 仮想環境（推奨）
python -m venv env
env\Scripts\activate  # Windows
# source env/bin/activate  # Mac/Linux

# 依存パッケージ
pip install -r requirements.txt
```

### 3. アプリ起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセス

---

## 🔍 使い方・検索例

- 検索フォームに「症状」「商品名」「カテゴリ」「サプリ名」などを日本語で入力し、検索ボタンを押すだけ
- 例：
  - 「抜け毛が増えた」
  - 「クラミジア」
  - 「EDサプリ」
  - 「ダイエットサプリ」
  - 「カマグラゴールド」
  - 「ED治療薬」

---

## ✅ 実装済み・UI/UXの特徴

- ブランドカラー（#073084ブルー、#1CA936グリーン）を各所に反映
- 検索ボタンはブランドグリーン、見出し・リンクはブランドブルー
- 検索結果数はバッジ表示でコンパクトに
- ご利用ガイド等のexpander内見出しは日本語＋小さめ太字で統一
- 開発者向け情報や不要なメッセージは非表示
- ダークモード自動対応

---

## ⚠️ 注意事項

- 本アプリの情報は参考用です。医薬品の使用は必ず医師・薬剤師にご相談ください。
- 商品データは定期的な更新を推奨します。
- OpenAI API等のAI機能は現状デフォルト無効です（利用時のみ.env設定が必要）。

---

## 🤝 拡張・カスタマイズ

- 商品データ（CSV）の追加・更新で簡単に拡張可能
- サプリメントやカテゴリの追加も容易
- UI/UXやブランドカラーのカスタマイズも柔軟
- FAISSやAI連携は今後の拡張で対応可能

---

## 📄 ライセンス・リンク

- 本プロジェクトは教育・研究目的で公開しています
- [お薬通販部 公式サイト](https://okusuritsuhan.shop/)
- [Streamlit](https://streamlit.io/)
- [GitHubリポジトリ](https://github.com/ts1979s-commits/okusuri-tuuhanbu-recommend)

---

**お薬通販部 商品レコメンドAI - v1.0**  
Powered by Python + Streamlit