"""
設定ファイル - お薬通販部商品レコメンドLLMアプリ
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # OpenAI API設定
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # お薬通販部サイトURL
    OKUSURI_BASE_URL: str = "https://okusuritsuhan.shop/"
    OKUSURI_COLUMN_URL: str = "https://okusuritsuhan.shop/column/"
    
    # ChromaDB設定
    CHROMA_DB_PATH: str = "./data/chroma_db"
    COLLECTION_NAME: str = "okusuri_products"
    
    # スクレイピング設定
    REQUEST_DELAY: float = 1.0  # リクエスト間隔（秒）
    MAX_PAGES: int = 100  # 最大ページ数
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # ログレベル
    LOG_LEVEL: str = "INFO"
    
    # Streamlit設定
    STREAMLIT_PORT: int = 8501
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

# 設定インスタンス
settings = Settings()

def get_settings() -> Settings:
    """設定を取得"""
    return settings