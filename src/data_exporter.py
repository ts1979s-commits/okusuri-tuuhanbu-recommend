"""
商品データの最適化されたスキーマ定義とエクスポート機能
取得した実際のデータを基に設計
"""
import json
import csv
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class ProductSchema:
    """商品データの標準スキーマ"""
    id: str                    # 一意識別子（URL or ハッシュベース）
    name: str                  # 商品名
    url: str                   # 商品詳細URL
    category: str              # カテゴリー（ED治療薬、AGA治療薬など）
    category_url: str          # カテゴリーページURL
    price: Optional[str] = None              # 価格
    description: Optional[str] = None        # 商品説明
    short_description: Optional[str] = None  # 短い説明（検索用）
    image_url: Optional[str] = None          # 画像URL
    ingredients: Optional[str] = None        # 有効成分
    dosage: Optional[str] = None             # 用法・用量
    manufacturer: Optional[str] = None       # 製造会社
    stock_status: Optional[str] = None       # 在庫状況
    tags: List[str] = None                   # タグ（検索用）
    scraped_at: str = None                   # 取得日時（ISO8601）
    source: str = "okusuritsuhan.shop"       # データソース
    raw_data: Optional[Dict] = None          # 生データ（デバッグ用）

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow().isoformat()

class ProductDataExporter:
    """商品データの各種形式エクスポート機能"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def normalize_product_data(self, raw_products: List[Dict]) -> List[ProductSchema]:
        """生データを標準スキーマに変換"""
        normalized = []
        
        for raw in raw_products:
            # IDの生成（URLまたは名前のハッシュベース）
            id_source = raw.get('url', raw.get('name', ''))
            product_id = hashlib.md5(id_source.encode('utf-8')).hexdigest()[:12]
            
            # カテゴリー名の抽出
            category = raw.get('name', '').replace('治療薬', '').replace('薬', '').strip()
            
            # 説明文のクリーニング
            description = raw.get('description', '')
            if description:
                # 改行と余分な空白を整理
                description = ' '.join(description.split())
                
            # 短い説明の生成（最初の100文字）
            short_desc = description[:100] if description else None
            
            # タグの生成（カテゴリーと説明から）
            tags = [category]
            if description:
                # 簡単なキーワード抽出
                keywords = ['治療', '効果', '成分', '服用', '症状']
                for keyword in keywords:
                    if keyword in description:
                        tags.append(keyword)
            
            product = ProductSchema(
                id=product_id,
                name=raw.get('name', ''),
                url=raw.get('url', ''),
                category=category,
                category_url=raw.get('category_url', ''),
                description=description,
                short_description=short_desc,
                image_url=raw.get('image_url'),
                tags=list(set(tags)),  # 重複除去
                raw_data=raw
            )
            
            normalized.append(product)
        
        return normalized
    
    def export_to_json(self, products: List[ProductSchema], filename: str = "products.json"):
        """JSON形式で出力"""
        filepath = self.data_dir / filename
        
        products_dict = [asdict(product) for product in products]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(products_dict, f, ensure_ascii=False, indent=2)
        
        print(f"💾 JSON形式で保存: {filepath}")
        return filepath
    
    def export_to_ndjson(self, products: List[ProductSchema], filename: str = "products.ndjson"):
        """NDJSON（行指向JSON）形式で出力"""
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for product in products:
                f.write(json.dumps(asdict(product), ensure_ascii=False) + '\n')
        
        print(f"💾 NDJSON形式で保存: {filepath}")
        return filepath
    
    def export_to_csv(self, products: List[ProductSchema], filename: str = "products.csv"):
        """CSV形式で出力（ネストフィールドはJSON文字列化）"""
        filepath = self.data_dir / filename
        
        if not products:
            print("⚠️ エクスポートする商品データがありません")
            return None
        
        # フィールド名を取得
        fieldnames = list(asdict(products[0]).keys())
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                row = asdict(product)
                # リストや辞書はJSON文字列に変換
                for key, value in row.items():
                    if isinstance(value, (list, dict)):
                        row[key] = json.dumps(value, ensure_ascii=False)
                
                writer.writerow(row)
        
        print(f"💾 CSV形式で保存: {filepath}")
        return filepath
    
    def export_to_sqlite(self, products: List[ProductSchema], filename: str = "products.db"):
        """SQLite形式で出力"""
        filepath = self.data_dir / filename
        
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        # テーブル作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT,
            category TEXT,
            category_url TEXT,
            price TEXT,
            description TEXT,
            short_description TEXT,
            image_url TEXT,
            ingredients TEXT,
            dosage TEXT,
            manufacturer TEXT,
            stock_status TEXT,
            tags TEXT,  -- JSON配列として保存
            scraped_at TEXT,
            source TEXT,
            raw_data TEXT,  -- JSON文字列として保存
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # データ挿入
        for product in products:
            data = asdict(product)
            # JSONフィールドを文字列化
            data['tags'] = json.dumps(data['tags'], ensure_ascii=False)
            data['raw_data'] = json.dumps(data['raw_data'], ensure_ascii=False) if data['raw_data'] else None
            
            cursor.execute('''
            INSERT OR REPLACE INTO products 
            (id, name, url, category, category_url, price, description, short_description,
             image_url, ingredients, dosage, manufacturer, stock_status, tags, 
             scraped_at, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['id'], data['name'], data['url'], data['category'], 
                data['category_url'], data['price'], data['description'], 
                data['short_description'], data['image_url'], data['ingredients'],
                data['dosage'], data['manufacturer'], data['stock_status'],
                data['tags'], data['scraped_at'], data['source'], data['raw_data']
            ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 SQLite形式で保存: {filepath}")
        return filepath
    
    def load_from_ndjson(self, filename: str = "products.ndjson") -> List[ProductSchema]:
        """NDJSONファイルから商品データを読み込み"""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            print(f"⚠️ ファイルが見つかりません: {filepath}")
            return []
        
        products = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                product = ProductSchema(**data)
                products.append(product)
        
        print(f"📂 NDJSONから {len(products)} 件の商品データを読み込み: {filepath}")
        return products
    
    def create_faiss_metadata_mapping(self, products: List[ProductSchema]) -> Dict[int, Dict]:
        """FAISSの埋め込みIDと商品メタデータのマッピングを作成"""
        mapping = {}
        
        for i, product in enumerate(products):
            mapping[i] = {
                'product_id': product.id,
                'name': product.name,
                'category': product.category,
                'url': product.url,
                'short_description': product.short_description
            }
        
        # マッピングをJSONで保存
        mapping_file = self.data_dir / "faiss_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        print(f"🔗 FAISSマッピングを保存: {mapping_file}")
        return mapping

def demo_export_pipeline():
    """実際のデータを使ったエクスポートのデモ"""
    print("📊 商品データエクスポートパイプラインのデモ")
    print("="*60)
    
    # 取得済みの実データを読み込み
    try:
        with open('data/sample_products_real.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print("❌ sample_products_real.json が見つかりません")
        return
    
    # エクスポーターを初期化
    exporter = ProductDataExporter()
    
    # データを正規化
    print("🔄 生データを標準スキーマに変換中...")
    normalized_products = exporter.normalize_product_data(raw_data)
    
    print(f"✅ {len(normalized_products)} 件の商品データを正規化")
    
    # 各形式でエクスポート
    print("\n📤 各形式でエクスポート中...")
    exporter.export_to_json(normalized_products, "normalized_products.json")
    exporter.export_to_ndjson(normalized_products, "normalized_products.ndjson")
    exporter.export_to_csv(normalized_products, "normalized_products.csv")
    exporter.export_to_sqlite(normalized_products, "normalized_products.db")
    
    # FAISSマッピング作成
    print("\n🔗 FAISSマッピング作成中...")
    mapping = exporter.create_faiss_metadata_mapping(normalized_products)
    
    # 結果サマリー表示
    print(f"\n📋 正規化後のデータサンプル:")
    print("="*60)
    
    for i, product in enumerate(normalized_products):
        print(f"\n🔸 商品 {i+1}:")
        print(f"  ID: {product.id}")
        print(f"  名前: {product.name}")
        print(f"  カテゴリー: {product.category}")
        print(f"  URL: {product.url}")
        print(f"  説明: {product.short_description}")
        print(f"  タグ: {product.tags}")
        print(f"  取得日時: {product.scraped_at}")

if __name__ == "__main__":
    demo_export_pipeline()