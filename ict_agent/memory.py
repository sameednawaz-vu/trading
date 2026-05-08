import sqlite3
import json
from datetime import datetime

DB_NAME = r'./ict_agent\mempalace.db'

class MemPalace:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
    
    def execute_query(self, query, params=()):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def fetch_query(self, query, params=()):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def log_trade(self, pair, timeframe, direction, setup_thesis, entry_price, sl, tp, result, rr, agent_reflection, date):
        query = '''
            INSERT INTO trades 
            (pair, timeframe, direction, setup_thesis, entry_price, sl, tp, result, rr, agent_reflection, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        # result is usually 'WIN' or 'LOSS'
        params = (pair, timeframe, direction, setup_thesis, entry_price, sl, tp, result, rr, agent_reflection, date)
        return self.execute_query(query, params)

    def log_reflection(self, trade_id, reflection_text, success_factor=None, failure_reason=None):
        query = 'INSERT INTO reflections (trade_id, reflection_text, success_factor, failure_reason) VALUES (?, ?, ?, ?)'
        return self.execute_query(query, (trade_id, reflection_text, success_factor, failure_reason))

    def add_to_mempalace(self, pattern_name, pattern_description):
        query = 'INSERT INTO mempalace (pattern_name, pattern_description, created_at) VALUES (?, ?, ?)'
        return self.execute_query(query, (pattern_name, pattern_description, datetime.now().isoformat()))

    def get_mempalace_rules(self):
        query = 'SELECT pattern_name, pattern_description FROM mempalace ORDER BY id DESC'
        rows = self.fetch_query(query)
        return [{"name": r[0], "description": r[1]} for r in rows]

    def query_failed_setups(self, pair=None, timeframe=None, limit=5):
        # Result can be 'LOSS' or 'FAIL'
        query = "SELECT setup_thesis, agent_reflection FROM trades WHERE (result = 'FAIL' OR result = 'LOSS')"
        params = []
        if pair:
            query += " AND pair = ?"
            params.append(pair)
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        return self.fetch_query(query, tuple(params))
    
    def query_successful_setups(self, pair=None, timeframe=None, limit=5):
        # Result can be 'SUCCESS' or 'WIN'
        query = "SELECT setup_thesis, agent_reflection FROM trades WHERE (result = 'SUCCESS' OR result = 'WIN')"
        params = []
        if pair:
            query += " AND pair = ?"
            params.append(pair)
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        return self.fetch_query(query, tuple(params))

    def get_recent_reflections(self, limit=10):
        query = '''
            SELECT t.pair, t.result, r.reflection_text, r.failure_reason 
            FROM reflections r 
            JOIN trades t ON r.trade_id = t.id 
            ORDER BY r.id DESC LIMIT ?
        '''
        return self.fetch_query(query, (limit,))
