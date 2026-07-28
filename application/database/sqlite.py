import json
import re
import sqlite3
from sqlite3 import Error
from typing import Optional, Any
from logger.logger import setup_logger
from ._resources import current_timestamp

logger = setup_logger('scraper.log', __name__)


class SQLiteDB:
    """Wrap SQLite operations for product storage."""

    def __init__(self, db_file: str = "scraped_data.db") -> None:
        self.db_file: str = db_file
        self.connection: Optional[sqlite3.Connection] = self.create_connection()
        if self.connection is not None:
            self.create_product_table()
            self.create_price_history_table()

    def create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a SQLite database connection."""
        try:
            conn = sqlite3.connect(self.db_file, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except Error as e:
            logger.error("SQLite database connection failed")
            print(f"SQLite database connection error: {e}")
            return None

    def create_product_table(self) -> None:
        """Create the products table if it does not exist."""
        if self.connection is None:
            return

        sql = '''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            price INTEGER,
            description TEXT,
            images TEXT,
            name TEXT,
            company_name TEXT,
            category TEXT,
            currency TEXT,
            availability TEXT,
            sku TEXT,
            mpn TEXT,
            rating REAL,
            review_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );'''
        try:
            self.connection.execute(sql)
            self.connection.commit()
        except Error as e:
            logger.error(f"Failed to create products table")
            print(f"Error creating products table: {e}")

    def create_price_history_table(self) -> None:
        """Create the price_history table if it does not exist."""
        if self.connection is None:
            return

        sql = '''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            price INTEGER,
            currency TEXT,
            availability TEXT,
            scraped_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );'''
        try:
            self.connection.execute(sql)
            self.connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);'
            )
            self.connection.commit()
        except Error as e:
            logger.error("Failed to create price_history table")
            print(f"Error creating price_history table: {e}")

    def upsert_product(self, product_data: dict) -> bool:
        """Insert or update a product record based on URL."""
        if self.connection is None:
            logger.error("Cannot upsert product without a database connection.")
            return False

        normalized = self._normalize_product_data(product_data)
        if not normalized["url"]:
            logger.error("Cannot upsert product without a URL.")
            return False
        sql = '''
        INSERT INTO products (
            url, title, price, description, images, name, company_name,
            category, currency, availability, sku, mpn, rating, review_count,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title = excluded.title,
            price = excluded.price,
            description = excluded.description,
            images = excluded.images,
            name = excluded.name,
            company_name = excluded.company_name,
            category = excluded.category,
            currency = excluded.currency,
            availability = excluded.availability,
            sku = excluded.sku,
            mpn = excluded.mpn,
            rating = excluded.rating,
            review_count = excluded.review_count,
            updated_at = excluded.updated_at;'''
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, (
                normalized["url"],
                normalized["title"],
                normalized["price"],
                normalized["description"],
                normalized["images"],
                normalized["name"],
                normalized["company_name"],
                normalized["category"],
                normalized["currency"],
                normalized["availability"],
                normalized["sku"],
                normalized["mpn"],
                normalized["rating"],
                normalized["review_count"],
                normalized["created_at"],
                normalized["updated_at"],
            ))
            product_id = self._get_product_id(normalized["url"])
            if not product_id:
                raise Error("Failed to resolve product id after upsert")
            self._insert_price_history(
                product_id,
                normalized["price"],
                normalized["currency"],
                normalized["availability"],
                normalized["updated_at"],
            )
            self.connection.commit()
            return True
        except Error as e:
            logger.error("Error upserting product")
            print(f"Error upserting product: {e}")
            return False

    def _get_product_id(self, url: str) -> Optional[int]:
        """Return a product's internal ID from its URL."""
        if self.connection is None:
            return None

        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT id FROM products WHERE url = ?', (url,))
            row = cursor.fetchone()
            return row['id'] if row else None
        except Error as e:
            logger.error("Error fetching product URL=%s" % url)
            print(f"Error fetching product URL={url}:\n{e}")
            return None

    def _insert_price_history(
        self,
        product_id: int,
        price: int,
        currency: Optional[str],
        availability: Optional[str],
        scraped_at: str,
    ) -> None:
        """Insert a price history record for a product."""
        if self.connection is None:
            return

        sql = '''
        INSERT INTO price_history (
            product_id, price, currency, availability, scraped_at
        ) VALUES (?, ?, ?, ?, ?)'''
        cursor = self.connection.cursor()
        cursor.execute(sql, (product_id, price, currency, availability, scraped_at))

    def get_price_history(self, product_id: int) -> list[dict]:
        """Return all price history records for a product."""
        if self.connection is None:
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                'SELECT * FROM price_history WHERE product_id = ? ORDER BY scraped_at DESC',
                (product_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Error as e:
            logger.error("Error fetching price history for product_id=%s" % product_id)
            print(f"Error fetching price history: {e}")
            return []

    def get_product(self, url: str = '', product_id: int = 0) -> Optional[dict]:
        """Get a single product by URL or product ID."""
        if self.connection is None:
            return None
        if not url and not product_id:
            logger.error("get_product requires either a url or a product_id")
            return None

        try:
            cursor = self.connection.cursor()
            if product_id:
                cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            else:
                cursor.execute('SELECT * FROM products WHERE url = ?', (url,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
        except Error as e:
            logger.error("Error getting product")
            print(f"Error getting product: {e}")
            return None

    def list_products(self) -> list[dict]:
        """Return all products in the database."""
        if self.connection is None:
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM products')
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except Error as e:
            logger.error(f"Error listing products")
            print(f"Error listing products: {e}")
            return []

    def delete_product(self, product_id: int) -> bool:
        """Delete a product row by its ID."""
        if self.connection is None:
            return False

        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logger.error(f"Error deleting product with id={product_id}")
            print(f"Error deleting product: {e}")
            return False

    def _normalize_product_data(self, product_data: dict) -> dict:
        """Normalize product data before storing in SQLite."""
        url = str(product_data.get('url', '')).strip()
        title = clean_text(str(product_data.get('title', '') or ''))
        description = clean_text(str(product_data.get('description', '') or ''))
        name = clean_text(str(product_data.get('name', '') or title))
        company_name = clean_text(str(product_data.get('company_name', '') or ''))

        images = product_data.get('images', []) or []
        category = product_data.get('category', []) or []
        if isinstance(images, str):
            images = [images]
        if isinstance(category, str):
            category = [category]

        return {
            'url': url,
            'title': title,
            'price': self._normalize_price(product_data.get('price', 0)),
            'description': description,
            'images': self._serialize_list(images),
            'name': name,
            'company_name': company_name,
            'category': self._serialize_list(category),
            'currency': product_data.get('currency'),
            'availability': product_data.get('availability'),
            'sku': product_data.get('sku'),
            'mpn': product_data.get('mpn'),
            'rating': self._normalize_float(product_data.get('rating')),
            'review_count': self._normalize_int(product_data.get('review_count')),
            'created_at': current_timestamp(),
            'updated_at': current_timestamp(),
        }

    def _normalize_price(self, value: Any) -> int:
        try:
            if value is None or value == '':
                return 0
            return int(float(value))
        except Exception:
            return 0

    def _normalize_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == '':
                return None
            return int(value)
        except Exception:
            return None

    def _normalize_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == '':
                return None
            return float(value)
        except Exception:
            return None

    def _serialize_list(self, value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return json.dumps([])

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        # Convert a SQLite row to a dictionary, deserializing JSON fields.
        if not row:
            return {}
        data = dict(row)
        for key in ('images', 'category'):
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except Exception:
                    data[key] = []
        return data


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and control characters."""
    return re.sub(r'\s+', ' ', str(text)).strip()
