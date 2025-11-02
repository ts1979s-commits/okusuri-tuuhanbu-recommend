"""
設定ファイル - お薬通販部商品レコメンドLLMアプリ
"""
import os
import streamlit as st
from typing import Optional

class Settings:
    """アプリケーション設定"""
    
    def __init__(self):
        # OpenAI API設定 - Streamlit Secretsまたは環境変数から取得
        self.OPENAI_API_KEY = self._get_secret("OPENAI_API_KEY")
        self.OPENAI_MODEL = self._get_secret("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
        self.OPENAI_EMBEDDING_MODEL = self._get_secret("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        
        # その他の設定
        self.MAX_TOKENS = int(self._get_secret("MAX_TOKENS", "500"))
        self.TEMPERATURE = float(self._get_secret("TEMPERATURE", "0.7"))
        
        # お薬通販部サイトURL
        self.OKUSURI_BASE_URL = "https://okusuritsuhan.shop/"
        self.OKUSURI_COLUMN_URL = "https://okusuritsuhan.shop/column/"
        
        # ChromaDB設定
        self.CHROMA_DB_PATH = "./data/chroma_db"
        self.COLLECTION_NAME = "okusuri_products"
        
        # スクレイピング設定
        self.REQUEST_DELAY = 1.0  # リクエスト間隔（秒）
        self.MAX_PAGES = 100  # 最大ページ数
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # ログレベル
        self.LOG_LEVEL = self._get_secret("LOG_LEVEL", "INFO")
        
        # Streamlit設定
        self.STREAMLIT_PORT = 8501
    
    def _get_secret(self, key: str, default: str = None) -> str:
        """Streamlit SecretsまたはOS環境変数から値を取得"""
        try:
            # Streamlit Secretsから取得を試行
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
        
        # OS環境変数から取得
        return os.getenv(key, default)

# 設定インスタンス
_settings = None

def get_settings() -> Settings:
    """設定を取得（シングルトンパターン）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings