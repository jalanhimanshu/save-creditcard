import pandas as pd
from scanner import TradingEngine
import yfinance as yf
import urllib.request
import json
from datetime import datetime

# Define Nifty 50 sub-universe for stable execution
nifty_universe = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"
]

engine = TradingEngine(nifty_universe)

print("Fetching reference dates...")
ref_data = yf.download("RELIANCE.NS", period="40d", interval="5m", progress=False)
dates = pd.Series(ref_data.index.date).unique()

# Get the last 30 trading days
backtest_dates = dates[-30:]

stats = {
    'total_triggered': 0,
    'wins_t1': 0,
    'wins_t2': 0,
    'losses': 0,
    'time_exits': 0,
    'tier1_triggers': 0,
    'tier2_triggers': 0,
    'tier1_wins': 0,
    'tier2_wins': 0
}

print(f"Running backtest across {len(nifty_universe)} stocks for {len(backtest_dates)} days...")

for ticker in nifty_universe:
    print(f"Processing {ticker}...")
    df_5m = engine.fetch_data(ticker, period="40d", interval="5m")
    df_daily = engine.fetch_daily_data(ticker, period="60d")
    
    if df_5m is None or df_daily is None or len(df_5m) == 0:
        continue
        
    for target_date in backtest_dates:
        if target_date not in df_5m.index.date:
            continue
            
        try:
            eval_result = engine.process_stock(ticker, target_date=target_date)
            
            if eval_result and eval_result['triggered']:
                stats['total_triggered'] += 1
                if eval_result['tier'] == 1:
                    stats['tier1_triggers'] += 1
                else:
                    stats['tier2_triggers'] += 1
                    
                dir = eval_result['direction']
                entry = eval_result['entry']
                stop = eval_result['stop']
                t1 = eval_result['t1']
                t2 = eval_result['t2']
                
                # Forward test the rest of the day
                day_data = df_5m[(df_5m.index.date == target_date)]
                
                outcome = "TIME_EXIT"
                for idx, row in day_data.iterrows():
                    h = row['High']
                    l = row['Low']
                    
                    if dir == "BULLISH":
                        if l <= stop:
                            outcome = "LOSS"
                            break
                        if h >= t2:
                            outcome = "WIN_T2"
                            break
                        if h >= t1:
                            outcome = "WIN_T1"
                            break
                    elif dir == "BEARISH":
                        if h >= stop:
                            outcome = "LOSS"
                            break
                        if l <= t2:
                            outcome = "WIN_T2"
                            break
                        if l <= t1:
                            outcome = "WIN_T1"
                            break
                            
                if outcome == "WIN_T1":
                    stats['wins_t1'] += 1
                    if eval_result['tier'] == 1: stats['tier1_wins'] += 1
                    else: stats['tier2_wins'] += 1
                elif outcome == "WIN_T2":
                    stats['wins_t2'] += 1
                    if eval_result['tier'] == 1: stats['tier1_wins'] += 1
                    else: stats['tier2_wins'] += 1
                elif outcome == "LOSS":
                    stats['losses'] += 1
                else:
                    stats['time_exits'] += 1
        except Exception as e:
            print(f"Error on {ticker} for {target_date}: {e}")

print("\n--- 30-DAY BACKTEST RESULTS ---")
print(f"Total Trades Triggered: {stats['total_triggered']}")
if stats['total_triggered'] > 0:
    total_wins = stats['wins_t1'] + stats['wins_t2']
    win_rate = (total_wins / stats['total_triggered']) * 100
    print(f"Total Wins: {total_wins} (T1: {stats['wins_t1']}, T2: {stats['wins_t2']})")
    print(f"Total Losses: {stats['losses']}")
    print(f"Time Exits (No Target/No Stop): {stats['time_exits']}")
    print(f"OVERALL WIN RATE: {win_rate:.2f}%")
    
    if stats['tier1_triggers'] > 0:
        t1_win_rate = (stats['tier1_wins'] / stats['tier1_triggers']) * 100
        print(f"Tier 1 (Core) Win Rate: {t1_win_rate:.2f}% ({stats['tier1_triggers']} trades)")
        
    if stats['tier2_triggers'] > 0:
        t2_win_rate = (stats['tier2_wins'] / stats['tier2_triggers']) * 100
        print(f"Tier 2 (Explosive) Win Rate: {t2_win_rate:.2f}% ({stats['tier2_triggers']} trades)")
    
with open("backtest_results.txt", "w") as f:
    f.write(f"Total Trades Triggered: {stats['total_triggered']}\n")
    if stats['total_triggered'] > 0:
        f.write(f"Total Wins: {total_wins} (T1: {stats['wins_t1']}, T2: {stats['wins_t2']})\n")
        f.write(f"Total Losses: {stats['losses']}\n")
        f.write(f"Time Exits: {stats['time_exits']}\n")
        f.write(f"OVERALL WIN RATE: {win_rate:.2f}%\n")
        if stats['tier1_triggers'] > 0:
            f.write(f"Tier 1 Win Rate: {t1_win_rate:.2f}% ({stats['tier1_triggers']} trades)\n")
        if stats['tier2_triggers'] > 0:
            f.write(f"Tier 2 Win Rate: {t2_win_rate:.2f}% ({stats['tier2_triggers']} trades)\n")
