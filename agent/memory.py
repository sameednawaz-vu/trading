from datetime import timezone
import sqlite3
import json
import os
from datetime import datetime

class MemoryManager:
    def __init__(self, db_path='./logs/trading_memory.db', mempalace_path='./mempalace'):
        self.db_path = db_path
        self.mempalace_path = mempalace_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for trade logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                timeframe TEXT,
                side TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                result TEXT, -- 'success', 'failure', 'pending'
                pnl REAL,
                setup_details TEXT, -- JSON string
                reflection TEXT
            )
        ''')
        
        # Table for agent reflections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                timestamp TEXT,
                query TEXT,
                response TEXT,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_trade(self, trade_data):
        """Logs a trade to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (timestamp, symbol, timeframe, side, entry_price, stop_loss, take_profit, result, pnl, setup_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            trade_data['symbol'],
            trade_data['timeframe'],
            trade_data['side'],
            trade_data['entry_price'],
            trade_data['stop_loss'],
            trade_data['take_profit'],
            trade_data.get('result', 'pending'),
            trade_data.get('pnl', 0.0),
            json.dumps(trade_data.get('setup_details', {}))
        ))
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

    def update_trade_result(self, trade_id, result, pnl, reflection=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE trades SET result = ?, pnl = ?, reflection = ? WHERE id = ?
        ''', (result, pnl, reflection, trade_id))
        conn.commit()
        conn.close()

    def store_pattern(self, category, name, data):
        """Stores a pattern (setup) in the hierarchical mempalace."""
        category_path = os.path.join(self.mempalace_path, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)
        
        file_path = os.path.join(category_path, f"{name}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Stored pattern {name} in {category}")

    def query_patterns(self, category):
        """Retrieves all patterns in a category."""
        category_path = os.path.join(self.mempalace_path, category)
        patterns = []
        if os.path.exists(category_path):
            for filename in os.listdir(category_path):
                if filename.endswith('.json'):
                    with open(os.path.join(category_path, filename), 'r') as f:
                        patterns.append(json.load(f))
        return patterns

if __name__ == "__main__":
    mem = MemoryManager()
    # Test logging
    # mem.log_trade({'symbol': 'BTC/USDT', 'timeframe': '5m', 'side': 'long', 'entry_price': 60000, 'stop_loss': 59500, 'take_profit': 61000})
