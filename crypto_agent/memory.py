import json
import os
import subprocess

class TradeMemory:
    def __init__(self, project_path):
        self.project_path = os.path.abspath(project_path)
        self.log_file = os.path.join(self.project_path, "trade_logs.txt")
        self._ensure_mempalace_init()

    def _ensure_mempalace_init(self):
        # We will use simple text logging first, then use mempalace to "mine" it
        if not os.path.exists(self.project_path):
            os.makedirs(self.project_path, exist_ok=True)

        # Initialize mempalace
        try:
            subprocess.run(["mempalace", "init", self.project_path], check=False, capture_output=True)
        except Exception as e:
            print(f"Warning: mempalace init failed or not installed properly: {e}")

    def log_trade(self, trade_data):
        """Log a trade outcome for future learning."""
        entry = json.dumps(trade_data)

        with open(self.log_file, "a") as f:
            f.write(entry + "\n")

        # Mine the new data
        try:
            subprocess.run(["mempalace", "mine", self.project_path], check=False, capture_output=True)
            print("Trade logged and mined into memory.")
        except Exception as e:
            print(f"Warning: mempalace mine failed: {e}")

    def search_similar_setups(self, query):
        """Query memory for similar past setups."""
        try:
            result = subprocess.run(["mempalace", "search", query], capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            print(f"Warning: mempalace search failed: {e}")
            return ""

if __name__ == "__main__":
    mem = TradeMemory("memory_palace_data")

    # Test data
    sample_trade = {
        "setup": "Bullish FVG on 15m",
        "action": "BUY",
        "status": "WIN",
        "reasoning": "Strong momentum",
        "symbol": "BTC/USDT"
    }

    mem.log_trade(sample_trade)
    print("Testing search...")
    print(mem.search_similar_setups("Bullish FVG"))
