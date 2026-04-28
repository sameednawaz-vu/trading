import json
import os
import time
from openai import OpenAI
from agent import TradingAgent
from backtest import load_and_prepare_data, run_backtest

def calculate_metrics(trades):
    if not trades:
        return 0.0, 0
    wins = [t for t in trades if t['pnl'] > 0]
    win_rate = len(wins) / len(trades)
    return win_rate, len(trades)

def get_refined_prompt(client, current_prompt, win_rate, total_trades):
    meta_prompt = f"""
    The trading agent using the following system prompt achieved a win rate of {win_rate*100:.1f}% over {total_trades} trades.
    Our goal is >= 80% win rate.

    Current Prompt:
    {current_prompt}

    Analyze the deficiencies. Focus strictly on refining the ICT execution rules.
    Provide a revised system prompt.
    You MUST output valid JSON exactly like this:
    {{"new_prompt": "..."}}
    """

    max_retries = 5
    base_wait = 2.0

    for attempt in range(max_retries):
        try:
            time.sleep(1.6) # respect RPM
            completion = client.chat.completions.create(
                model="meta/llama-3.3-70b-instruct",
                messages=[{"role": "user", "content": meta_prompt}],
                temperature=0.3
            )
            response = completion.choices[0].message.content
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].strip()

            data = json.loads(response)
            return data.get('new_prompt', current_prompt)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                wait = base_wait * (2 ** attempt)
                print(f"Rate limited during optimization. Waiting {wait} seconds...")
                time.sleep(wait)
            else:
                return current_prompt
    return current_prompt

def optimize():
    print("Loading Optimization Data...")
    df = load_and_prepare_data("BTC_USDT")
    df_train = df.head(100) # smaller subset for speed during demo

    agent = TradingAgent()
    client = agent.client

    current_prompt = agent.system_prompt

    os.makedirs('logs', exist_ok=True)

    iteration = 0
    while True:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        agent.set_system_prompt(current_prompt)

        trades = run_backtest(df_train)
        win_rate, num_trades = calculate_metrics(trades)

        print(f"Result: {win_rate*100:.1f}% Win Rate, {num_trades} Trades")

        with open("logs/optimization.log", "a") as f:
            f.write(f"Iteration {iteration}: {win_rate*100:.1f}% WR, {num_trades} Trades\n")
            f.write(f"Prompt: {current_prompt[:100]}...\n\n")

        if win_rate >= 0.80 and num_trades > 0:
            print("Target reached!")
            with open("logs/best_prompt.txt", "w") as f:
                f.write(current_prompt)
            break

        print("Refining prompt...")
        current_prompt = get_refined_prompt(client, current_prompt, win_rate, num_trades)

if __name__ == "__main__":
    os.environ["NVIDIA_API_KEY"] = "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"
    optimize()
