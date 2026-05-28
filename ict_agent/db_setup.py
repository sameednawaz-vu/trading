import sqlite3
import os

DB_NAME = './ict_agent/mempalace.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            direction TEXT NOT NULL,
            setup_thesis TEXT,
            entry_price REAL,
            sl REAL,
            tp REAL,
            result TEXT,
            rr REAL,
            agent_reflection TEXT,
            date TEXT
        )
    ''')
    
    # Create reflections table for extended analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            reflection_text TEXT,
            success_factor TEXT,
            failure_reason TEXT,
            FOREIGN KEY(trade_id) REFERENCES trades(id)
        )
    ''')

    # Create mempalace table for learned rules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mempalace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT,
            pattern_description TEXT,
            weight REAL DEFAULT 1.0,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_NAME}")

if __name__ == "__main__":
    init_db()
