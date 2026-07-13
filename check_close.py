import yfinance as yf
import pandas as pd
import pytz

IST = pytz.timezone('Asia/Kolkata')
ticker = "TPLPLASTEH.NS"

try:
    data = yf.download(ticker, period="5d", interval="1d", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
        
    last_day = data.iloc[-1]
    date_str = data.index[-1].strftime('%Y-%m-%d')
    
    print(f"Closing Data for {ticker} on {date_str}:")
    print(f"Open:  {round(float(last_day['Open']), 2)}")
    print(f"High:  {round(float(last_day['High']), 2)}")
    print(f"Low:   {round(float(last_day['Low']), 2)}")
    print(f"Close: {round(float(last_day['Close']), 2)}")
    print(f"Volume: {int(last_day['Volume'])}")
    
    # Check percentage change from open
    open_price = float(last_day['Open'])
    close_price = float(last_day['Close'])
    pct_change = ((close_price - open_price) / open_price) * 100
    print(f"Intraday Move (Open to Close): {round(pct_change, 2)}%")
    
except Exception as e:
    print(f"Error fetching closing data: {e}")
