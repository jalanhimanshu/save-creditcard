import sys
from scanner import TradingEngine

nifty50_tickers = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS",
    "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS",
    "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LTIM.NS",
    "LT.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS",
    "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS",
    "TITAN.NS", "UPL.NS", "ULTRACEMCO.NS", "WIPRO.NS"
]

engine = TradingEngine(nifty50_tickers)
print("Scanning Nifty 50 for today's setups...")
sys.stdout.flush()

triggered = []
for ticker in nifty50_tickers:
    print(f"Scanning {ticker}...")
    sys.stdout.flush()
    try:
        eval_result = engine.process_stock(ticker)
        if eval_result and eval_result['triggered']:
            triggered.append(eval_result['report'])
    except Exception as e:
        pass

print("\n--- SCAN COMPLETE ---")
if len(triggered) == 0:
    print("No stocks triggered the strategy today.")
else:
    print(f"Found {len(triggered)} setups!")
    for r in triggered:
        print(r)
