import json
import time
from openai import OpenAI

class TradingAgent:
    def __init__(self, api_key="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"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model = "meta/llama-3.1-70b-instruct"
        # Nvidia API rate limits can be strict. Let's force a delay between requests.
        self.delay_between_requests = 2.0
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.delay_between_requests:
            time.sleep(self.delay_between_requests - elapsed)
        self.last_request_time = time.time()

    def analyze_setup(self, symbol, timeframe, current_price, recent_candles, fvg_data, ob_data):
        self._wait_for_rate_limit()

        prompt = f"""
You are an expert crypto trader specializing in Inner Circle Trader (ICT) concepts like Fair Value Gaps (FVG) and Order Blocks (OB).
Analyze the following market setup and provide a trading decision.

Symbol: {symbol}
Timeframe: {timeframe}
Current Price: {current_price}

Recent Context:
{recent_candles}

ICT Signals Found:
Fair Value Gaps (FVGs): {fvg_data}
Order Blocks (OBs): {ob_data}

Rules:
1. Target a Risk/Reward ratio of at least 1:2.
2. Only take trades with high probability (>80% win rate expected).
3. If no clear setup exists, output action as "HOLD".

Respond ONLY with a JSON object in this exact format:
{{
    "action": "BUY" | "SELL" | "HOLD",
    "entry_price": float (if action is BUY/SELL),
    "stop_loss": float (if action is BUY/SELL),
    "take_profit": float (if action is BUY/SELL),
    "reasoning": "Brief explanation based on ICT concepts"
}}
"""

        # Simple retry logic for 429
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    top_p=0.7,
                    max_tokens=256,
                )

                content = response.choices[0].message.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()

                return json.loads(content)
            except Exception as e:
                if '429' in str(e):
                    print(f"Rate limited. Retrying in {5 * (attempt + 1)}s...")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"Error querying LLM: {e}")
                    break

        return {"action": "HOLD", "reasoning": "Failed due to API errors."}

if __name__ == "__main__":
    agent = TradingAgent()
    print("Testing Agent API connection...")
    result = agent.analyze_setup(
        "BTC/USDT", "15m", 65000,
        "Last 3 candles bullish. Strong momentum.",
        "Bullish FVG at 64800-64900",
        "Bullish OB at 64500"
    )
    print(json.dumps(result, indent=2))
