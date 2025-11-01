"""
お薬通販部ウェブスクレイパー
商品情報を取得するためのスクレイピング機能
"""
import requests
from bs4 import BeautifulSoup
import time
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from urllib.parse import urljoin, urlparse
import re

from config.settings import get_settings

settings = get_settings()

# ログ設定
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class Product:
    """商品データクラス"""
    name: str
    url: str
    price: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    ingredients: Optional[str] = None
    usage: Optional[str] = None
    image_url: Optional[str] = None

class OkusuriScraper:
    """お薬通販部スクレイパー"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.USER_AGENT
        })
        self.base_url = settings.OKUSURI_BASE_URL
        
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """ページを取得してBeautifulSoupオブジェクトを返す"""
        try:
            time.sleep(settings.REQUEST_DELAY)
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"ページ取得エラー {url}: {e}")
            return None
    
    def extract_product_links(self, soup: BeautifulSoup) -> List[str]:
        """商品ページのリンクを抽出"""
        product_links = []
        
        # 商品リンクを探す（実際のサイト構造に応じて調整が必要）
        # 一般的なパターンを想定
        selectors = [
            'a[href*="/products/"]',
            'a[href*="/item/"]',
            '.product-link',
            '.item-link'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in product_links:
                        product_links.append(full_url)
        
        return product_links
    
    def extract_product_info(self, soup: BeautifulSoup, url: str) -> Optional[Product]:
        """商品詳細情報を抽出"""
        try:
            # 商品名を抽出
            name_selectors = ['h1', '.product-title', '.item-title', 'title']
            name = None
            for selector in name_selectors:
                element = soup.select_one(selector)
                if element:
                    name = element.get_text(strip=True)
                    break
            
            if not name:
                logger.warning(f"商品名が見つかりません: {url}")
                return None
            
            # 価格を抽出
            price_selectors = ['.price', '.product-price', '[class*="price"]']
            price = None
            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text(strip=True)
                    # 価格の数字部分を抽出
                    price_match = re.search(r'[\d,]+', price_text)
                    if price_match:
                        price = price_match.group()
                    break
            
            # 商品説明を抽出
            desc_selectors = ['.description', '.product-description', '.item-desc']
            description = None
            for selector in desc_selectors:
                element = soup.select_one(selector)
                if element:
                    description = element.get_text(strip=True)[:500]  # 最初の500文字
                    break
            
            # カテゴリを抽出
            category_selectors = ['.category', '.breadcrumb', '.product-category']
            category = None
            for selector in category_selectors:
                element = soup.select_one(selector)
                if element:
                    category = element.get_text(strip=True)
                    break
            
            # 画像URLを抽出
            image_selectors = ['.product-image img', '.item-image img', 'img[alt*="商品"]']
            image_url = None
            for selector in image_selectors:
                element = soup.select_one(selector)
                if element:
                    src = element.get('src')
                    if src:
                        image_url = urljoin(url, src)
                        break
            
            return Product(
                name=name,
                url=url,
                price=price,
                description=description,
                category=category,
                image_url=image_url
            )
            
        except Exception as e:
            logger.error(f"商品情報抽出エラー {url}: {e}")
            return None
    
    def scrape_category_page(self, category_url: str) -> List[str]:
        """カテゴリページから商品リンクを取得"""
        soup = self.get_page(category_url)
        if not soup:
            return []
        
        return self.extract_product_links(soup)
    
    def scrape_product(self, product_url: str) -> Optional[Product]:
        """単一商品の詳細情報を取得"""
        soup = self.get_page(product_url)
        if not soup:
            return None
        
        return self.extract_product_info(soup, product_url)
    
    def scrape_products(self, max_products: int = 100) -> List[Product]:
        """複数商品の情報を取得"""
        products = []
        
        # メインページから開始
        soup = self.get_page(self.base_url)
        if not soup:
            logger.error("メインページの取得に失敗しました")
            return products
        
        # 商品リンクを取得
        product_links = self.extract_product_links(soup)
        
        # カテゴリページも探索
        category_selectors = ['a[href*="/category/"]', 'a[href*="/categories/"]']
        for selector in category_selectors:
            category_links = soup.select(selector)
            for link in category_links[:5]:  # 最初の5カテゴリ
                href = link.get('href')
                if href:
                    category_url = urljoin(self.base_url, href)
                    category_product_links = self.scrape_category_page(category_url)
                    product_links.extend(category_product_links)
        
        # 重複を除去
        product_links = list(set(product_links))
        
        logger.info(f"取得した商品リンク数: {len(product_links)}")
        
        # 各商品の詳細情報を取得
        for i, product_url in enumerate(product_links[:max_products]):
            logger.info(f"商品情報取得中: {i+1}/{min(len(product_links), max_products)}")
            
            product = self.scrape_product(product_url)
            if product:
                products.append(product)
            
            # 進捗表示
            if (i + 1) % 10 == 0:
                logger.info(f"取得完了: {len(products)}件")
        
        logger.info(f"スクレイピング完了: {len(products)}件の商品情報を取得")
        return products
    
    def save_products(self, products: List[Product], filepath: str):
        """商品データをJSONファイルに保存"""
        data = []
        for product in products:
            data.append({
                'name': product.name,
                'url': product.url,
                'price': product.price,
                'description': product.description,
                'category': product.category,
                'ingredients': product.ingredients,
                'usage': product.usage,
                'image_url': product.image_url
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"商品データを保存しました: {filepath}")

def main():
    """メイン実行関数"""
    scraper = OkusuriScraper()
    
    # 商品情報を取得
    products = scraper.scrape_products(max_products=50)  # テスト用に50件
    
    # データを保存
    if products:
        scraper.save_products(products, './data/products.json')
    else:
        logger.warning("商品データが取得できませんでした")

if __name__ == "__main__":
    main()