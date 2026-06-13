import subprocess
import time
import json
import os

def run_agency():
    state_path = '/app/ranking_state.json'
    
    while True:
        print("ACEO | Starting Strategy Ranking Cycle...")
        try:
            # Run the ranking engine
            process = subprocess.Popen(['python', '/app/ict_agent/ranking_engine.py'])
            process.wait()
        except Exception as e:
            print(f"ACEO | System Crash: {e}. Recovering...")

        # Check if ranking is complete
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            processed = state.get('processed_strategies', [])
            print(f"ACEO | Progress Check: {len(processed)} Strategies Processed.")
            
            # If all strategies (approx 21) are processed, find the winner
            if len(processed) >= 21:
                winner = max(processed, key=lambda x: x['win_rate'])
                print(f"ACEO | RANKING COMPLETE. WINNER: {winner['name']} with {winner['win_rate']*100:.2f}% WR.")
                break
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        run_agency()
    except KeyboardInterrupt:
        print("\nACEO | Interrupted by User.")
    except Exception as e:
        print(f"\nACEO | Fatal Error: {e}")
    finally:
        print("STATE SAVED. READY FOR RESUMPTION.")
