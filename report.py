import sqlite3
import json

def generate_report(db_path='logs/trading_memory.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT side, entry_price, stop_loss, take_profit, result FROM trades WHERE result IN ('success', 'failure')")
    rows = cursor.fetchall()
    conn.close()

    total_trades = len(rows)
    if total_trades == 0:
        print("No trades found in the database. Wait for the backtester to finish.")
        return

    success_count = sum(1 for r in rows if r[4] == 'success')
    success_rate = (success_count / total_trades) * 100

    total_rr = 0
    for row in rows:
        side, entry, sl, tp, result = row
        if side == 'Long':
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        if risk > 0:
            total_rr += (reward / risk)

    avg_rr = total_rr / total_trades if total_trades > 0 else 0

    # We ran for exactly 1 month.
    monthly_trades = total_trades

    print(f"--- 20 ASSET BACKTEST REPORT ---")
    print(f"Total Trades Taken: {total_trades}")
    print(f"Successful Trades: {success_count}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Average Risk:Reward Ratio: 1:{avg_rr:.2f}")
    print(f"Average Monthly Trades (Across 20 Assets): {monthly_trades}")

if __name__ == "__main__":
    generate_report()
