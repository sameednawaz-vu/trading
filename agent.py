from openai import OpenAI
import json
import os
import time

class TradingAgent:
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable is required")

        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model = "meta/llama-3.3-70b-instruct"
        self.system_prompt = """
        You are an elite autonomous AI trading agent. Your core strategy relies on ICT (Inner Circle Trader) concepts like
        Fair Value Gaps (FVG), Order Blocks (OB), and Liquidity Sweeps across multiple timeframes.

        You will be provided with recent market context annotated with these features.
        Analyze the setup. You must respond ONLY with a valid JSON object matching the following format exactly:
        {
            "action": "BUY" or "SELL" or "HOLD",
            "stop_loss": <float> or null,
            "take_profit": <float> or null,
            "reasoning": "brief explanation"
        }

        Rules:
        1. If action is HOLD, stop_loss and take_profit can be null.
        2. If action is BUY or SELL, stop_loss and take_profit MUST be numbers.
        3. Enforce a minimum 1:2 Risk/Reward ratio.
        """

    def set_system_prompt(self, new_prompt):
        self.system_prompt = new_prompt

    def predict(self, context_str):
        max_retries = 5
        base_wait = 2.0

        for attempt in range(max_retries):
            try:
                # Respect 40 RPM limit
                time.sleep(1.6)

                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": context_str}
                    ],
                    temperature=0.2,
                    max_tokens=200
                )
                response_text = completion.choices[0].message.content

                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].strip()

                return json.loads(response_text)
            except Exception as e:
                print(f"Agent prediction error: {e}")
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait = base_wait * (2 ** attempt)
                    print(f"Rate limited. Waiting {wait} seconds...")
                    time.sleep(wait)
                else:
                    return {"action": "HOLD", "stop_loss": None, "take_profit": None, "reasoning": str(e)}

        return {"action": "HOLD", "stop_loss": None, "take_profit": None, "reasoning": "Max retries exceeded"}

if __name__ == "__main__":
    os.environ["NVIDIA_API_KEY"] = "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"
    agent = TradingAgent()
    mock_context = "Current Price: 65500.00"
    decision = agent.predict(mock_context)
    print("Agent Decision:", decision)
