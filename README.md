# 🏥 お薬通販部商品レコメンドLLMアプリ

フェーズ1実装: RAGベースの商品検索・レコメンドシステム

## 🎯 概要

お薬通販部サイトの商品情報を活用したAI駆動の商品レコメンドシステムです。RAG（Retrieval-Augmented Generation）技術を使用して、ユーザーの症状や要求に基づいて最適な商品を推薦します。

## ✨ 主な機能

- 🕷️ **Webスクレイピング**: お薬通販部サイトから商品情報を自動取得
- 🧠 **RAG システム**: ChromaDB + OpenAI Embeddingsによる高精度検索
- 🎯 **インテリジェントレコメンド**: 症状・商品名・カテゴリ別の最適化検索
- 💬 **自然言語処理**: 自然な日本語でのクエリ理解
- 🌐 **Web UI**: Streamlitによるユーザーフレンドリーなインターフェース

## 🛠️ 技術スタック

- **Python 3.11+**
- **OpenAI GPT-3.5-turbo + Embeddings**
- **ChromaDB** (ベクトルデータベース)
- **Streamlit** (Web UI)
- **BeautifulSoup** (スクレイピング)
- **FastAPI** (API開発準備)

## 📁 プロジェクト構造

```
okusuri-tuuhanbu-recommend/
├── main.py                    # メインエントリーポイント
├── app.py                     # Streamlit Web UI
├── requirements.txt           # 依存パッケージ
├── .env                      # 環境変数設定
├── config/
│   ├── __init__.py
│   └── settings.py           # アプリケーション設定
├── src/
│   ├── __init__.py
│   ├── scraper.py            # Webスクレイピング機能
│   ├── rag_system.py         # RAGシステム実装
│   └── recommendation_engine.py  # レコメンドエンジン
├── data/
│   ├── products.json         # 取得した商品データ
│   └── chroma_db/           # ChromaDBデータ
├── tests/                    # テストコード
└── youken/                   # 要件資料
```

## 🚀 セットアップ

### 1. 環境準備

```bash
# 仮想環境有効化
.\env\Scripts\Activate.ps1

# パッケージインストール（既に完了済み）
python -m pip install -r requirements.txt
```

### 2. 環境変数設定

`.env` ファイルにOpenAI APIキーを設定:

```env
OPENAI_API_KEY=your_openai_api_key_here
LOG_LEVEL=INFO
```

## 📖 使用方法

### メインアプリケーション起動

```bash
python main.py
```

メニューから以下の機能を選択できます:

1. **商品データ取得** - お薬通販部サイトからスクレイピング
2. **商品検索・レコメンド** - コマンドライン版
3. **Web UI起動** - ブラウザでの操作
4. **システム状態確認** - データベース状況確認

### Web UI起動 (推奨)

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセス

## 🔍 検索例

### 症状ベース検索
- "抜け毛が増えた"
- "足のむくみが取れない"
- "喉の痛みが治らない"

### 商品名検索
- "カマグラゴールド"
- "フィナクス+ミノクソール"

### カテゴリ検索
- "ED治療薬"
- "AGA治療薬"

## 🎯 フェーズ1実装内容

### ✅ 完了した機能

1. **プロジェクト構造の作成** - フォルダ構成、設定ファイル
2. **必要パッケージの追加** - requirements.txt、ライブラリインストール
3. **設定ファイルの作成** - API設定、URL管理
4. **ウェブスクレイピング機能** - 商品情報自動取得
5. **RAGシステムの構築** - ChromaDB + OpenAI Embeddings
6. **レコメンド機能の実装** - 高度な検索・推薦アルゴリズム
7. **Streamlit UI作成** - Web インターフェース

### 🚧 今後の拡張 (フェーズ2以降)

- より高度なスクレイピング最適化
- リアルタイム価格比較
- ユーザー履歴ベースの個人化
- ファインチューニングモデル
- API公開機能
- モバイル対応

## ⚠️ 注意事項

1. **APIコスト**: OpenAI APIの使用量に注意してください
2. **スクレイピング頻度**: サイトへの負荷を考慮し、適切な間隔で実行
3. **データ精度**: 実際の商品情報は公式サイトで確認してください
4. **医薬品情報**: レコメンドは参考情報であり、専門家への相談を推奨

## 📊 システム要件

- Python 3.11以上
- メモリ: 4GB以上推奨
- ストレージ: 1GB以上の空き容量
- インターネット接続 (OpenAI API、スクレイピング用)

## 🤝 コントリビューション

フィードバックや改善提案を歓迎します！

## 📄 ライセンス

このプロジェクトは教育・研究目的で開発されています。

## 🔗 参考リンク

- [お薬通販部](https://okusuritsuhan.shop/)
- [お薬通販部メディカルガイド](https://okusuritsuhan.shop/column/)
- [OpenAI API](https://openai.com/api/)
- [ChromaDB](https://www.trychroma.com/)
- [Streamlit](https://streamlit.io/)
