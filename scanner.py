import yfinance as yf
import pandas as pd
import numpy as np
import pytz
import requests

# Set timezone to IST
IST = pytz.timezone('Asia/Kolkata')

class TradingEngine:
    def __init__(self, tickers, interval="5m", multi_tf=True):
        self.tickers = tickers
        self.interval = interval
        self.multi_tf = multi_tf
        self.benchmark_ticker = "^NSEI" 

    def fetch_data(self, ticker, period="10d", interval="5m"):
        try:
            session = requests.Session()
            data = yf.download(ticker, period=period, interval=interval, progress=False, session=session)
            if data.empty:
                return None
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
                
            if data.index.tz is None:
                data.index = data.index.tz_localize('UTC').tz_convert(IST)
            else:
                data.index = data.index.tz_convert(IST)
            
            return data
        except Exception as e:
            return None

    def fetch_daily_data(self, ticker, period="1mo"):
        try:
            session = requests.Session()
            data = yf.download(ticker, period=period, interval="1d", progress=False, session=session)
            if data.empty:
                return None
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
            return data
        except Exception as e:
            return None

    def calculate_pivots(self, high, low, close):
        p = (high + low + close) / 3
        r1 = (2 * p) - low
        s1 = (2 * p) - high
        r2 = p + (high - low)
        s2 = p - (high - low)
        return p, r1, s1, r2, s2
        
    def check_pivot_clearance(self, open_price, high_price, low_price, p, r1, s1, r2, s2, direction):
        if direction == "BULLISH":
            if (r1 - high_price > 0 and r1 - high_price < 0.05 * r1) or (r2 - high_price > 0 and r2 - high_price < 0.05 * r2):
                return False, "Blocked by R1/R2 Ceiling"
            return True, "Clear"
        elif direction == "BEARISH":
            if (open_price - s1 > 0 and open_price - s1 < 0.05 * s1) or (open_price - s2 > 0 and open_price - s2 < 0.05 * s2):
                return False, "Blocked by S1/S2 Floor"
            return True, "Clear"
        return False, "Invalid Direction"
        
    def compute_supertrend(self, df, period=10, multiplier=3):
        df['tr1'] = df['High'] - df['Low']
        df['tr2'] = abs(df['High'] - df['Close'].shift(1))
        df['tr3'] = abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(period).mean()

        hl2 = (df['High'] + df['Low']) / 2
        df['basic_ub'] = hl2 + (multiplier * df['atr'])
        df['basic_lb'] = hl2 - (multiplier * df['atr'])

        final_ub = [0.0] * len(df)
        final_lb = [0.0] * len(df)
        
        for i in range(period, len(df)):
            if df['basic_ub'].iloc[i] < final_ub[i-1] or df['Close'].iloc[i-1] > final_ub[i-1]:
                final_ub[i] = df['basic_ub'].iloc[i]
            else:
                final_ub[i] = final_ub[i-1]
                
            if df['basic_lb'].iloc[i] > final_lb[i-1] or df['Close'].iloc[i-1] < final_lb[i-1]:
                final_lb[i] = df['basic_lb'].iloc[i]
            else:
                final_lb[i] = final_lb[i-1]
                
        df['final_ub'] = final_ub
        df['final_lb'] = final_lb
        
        supertrend = [0.0] * len(df)
        st_dir = [1] * len(df)
        
        for i in range(period, len(df)):
            if supertrend[i-1] == final_ub[i-1] and df['Close'].iloc[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
                st_dir[i] = -1
            elif supertrend[i-1] == final_ub[i-1] and df['Close'].iloc[i] > final_ub[i]:
                supertrend[i] = final_lb[i]
                st_dir[i] = 1
            elif supertrend[i-1] == final_lb[i-1] and df['Close'].iloc[i] >= final_lb[i]:
                supertrend[i] = final_lb[i]
                st_dir[i] = 1
            elif supertrend[i-1] == final_lb[i-1] and df['Close'].iloc[i] < final_lb[i]:
                supertrend[i] = final_ub[i]
                st_dir[i] = -1

        df['supertrend'] = supertrend
        df['st_dir'] = st_dir
        return df

    def evaluate_timeframe(self, df, df_daily, benchmark_daily, ticker, timeframe_label):
        dates = pd.Series(df.index.date).unique()
        if len(dates) < 2:
            return None
            
        target_date = dates[-1] 
        yesterday_date = dates[-2]
        
        day_data = df[df.index.date == target_date]
        if day_data.empty:
            return None
            
        first_candle = day_data.iloc[0]
        
        # Layer 1 Metrics
        c_open = round(float(first_candle['Open']), 2)
        c_high = round(float(first_candle['High']), 2)
        c_low = round(float(first_candle['Low']), 2)
        c_close = round(float(first_candle['Close']), 2)
        c_vol = float(first_candle['Volume'])
        
        range_tot = round(c_high - c_low, 2)
        real_body = round(abs(c_close - c_open), 2)
        
        if range_tot == 0:
            return None
            
        body_ratio = round((real_body / range_tot) * 100, 2) if range_tot > 0 else 0
        
        bullish_struct = (c_open == c_low)
        bearish_struct = (c_open == c_high)
        
        direction = "NONE"
        if bullish_struct:
            direction = "BULLISH"
        elif bearish_struct:
            direction = "BEARISH"
            
        struct_pass = bullish_struct or bearish_struct
        body_pass = body_ratio >= 70.0
        
        layer1_pass = struct_pass and body_pass
        
        # Historical Daily Data for Overrides
        prev_day_row = df_daily[df_daily.index.date < target_date].iloc[-1]
        pdh = round(float(prev_day_row['High']), 2)
        pdl = round(float(prev_day_row['Low']), 2)
        pdc = round(float(prev_day_row['Close']), 2)
        
        # Gap Calculation
        gap_pct = round(((c_open - pdc) / pdc) * 100, 2)
        
        # Layer 2 Metrics
        avg_daily_vol = df_daily['Volume'].mean()
        pre_market_pass = avg_daily_vol >= 1000000 
        
        # Calculate RVOL for slot
        first_candles_idx = df.groupby(df.index.date).apply(lambda x: x.index[0])
        first_candles = df.loc[first_candles_idx]
        avg_slot_vol = first_candles['Volume'].iloc[:-1].mean()
        
        vol_multiplier = round(c_vol / avg_slot_vol, 2) if avg_slot_vol > 0 else 0
        inst_vol_pass = vol_multiplier >= 2.0
        rvol_override = vol_multiplier >= 5.0 
        
        vz_pass = False
        if direction == "BULLISH":
            vz_pass = c_low > pdh
        elif direction == "BEARISH":
            vz_pass = c_high < pdl
            
        # Gap & Momentum Override
        gap_override = False
        if direction == "BULLISH" and gap_pct >= 2.0 and body_ratio >= 90.0:
            gap_override = True
        elif direction == "BEARISH" and gap_pct <= -2.0 and body_ratio >= 90.0:
            gap_override = True
            
        # Extreme Momentum Override
        extreme_mom_override = (body_ratio >= 99.0) # Allowing slight float rounding

        tier = 0
        strict_l2_pass = pre_market_pass and inst_vol_pass and vz_pass
        
        if strict_l2_pass:
            layer2_pass = True
            tier = 1
        elif rvol_override or gap_override or extreme_mom_override:
            layer2_pass = True
            tier = 2
        else:
            layer2_pass = False

        # Layer 3 Metrics
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TP_V'] = df['Typical_Price'] * df['Volume']
        day_grouped = df.groupby(df.index.date)
        df['Cum_Vol'] = day_grouped['Volume'].cumsum()
        df['Cum_TP_V'] = day_grouped['TP_V'].cumsum()
        df['VWAP'] = df['Cum_TP_V'] / df['Cum_Vol']
        
        vwap = float(df[df.index.date == target_date].iloc[0]['VWAP'])
        
        df = self.compute_supertrend(df, period=10, multiplier=3)
        st_dir = df[df.index.date == target_date].iloc[0]['st_dir']
            
        vwap_st_pass = False
        if direction == "BULLISH":
            vwap_st_pass = (c_close > vwap) and (st_dir == 1)
        elif direction == "BEARISH":
            vwap_st_pass = (c_close < vwap) and (st_dir == -1)
            
        bench_prev = benchmark_daily.iloc[-2]['Close']
        bench_curr = benchmark_daily.iloc[-1]['Close']
        bench_green = bench_curr > bench_prev
        bench_red = bench_curr < bench_prev
        
        cohesion_pass = False
        if direction == "BULLISH":
            cohesion_pass = bench_green
        elif direction == "BEARISH":
            cohesion_pass = bench_red
            
        p, r1, s1, r2, s2 = self.calculate_pivots(pdh, pdl, pdc)
        pivot_pass, pivot_reason = self.check_pivot_clearance(c_open, c_high, c_low, p, r1, s1, r2, s2, direction)
        
        if tier == 2:
             cohesion_pass = True 
             vwap_st_pass = True 
             pivot_pass = True 
             
        layer3_pass = layer2_pass and vwap_st_pass and cohesion_pass and pivot_pass
        
        target1 = r1 if direction == "BULLISH" else s1
        target2 = r2 if direction == "BULLISH" else s2
        stop = c_low - 0.05 if direction == "BULLISH" else c_high + 0.05

        return {
            'struct_pass': struct_pass,
            'body_pass': body_pass,
            'layer1_pass': layer1_pass,
            'triggered': layer3_pass,
            'direction': direction,
            'tier': tier,
            'entry': c_close,
            'stop': round(stop, 2),
            't1': round(target1, 2),
            't2': round(target2, 2),
            'report': self.format_report(ticker, c_open, c_high, c_low, c_close, bullish_struct, bearish_struct,
                                 body_ratio, body_pass, pre_market_pass, vol_multiplier, inst_vol_pass, vz_pass,
                                 vwap_st_pass, cohesion_pass, pivot_pass, layer1_pass, layer2_pass, layer3_pass,
                                 direction, r1, s1, r2, s2, gap_pct, rvol_override, gap_override, extreme_mom_override, tier, timeframe_label)
        }

    def process_stock(self, ticker, target_date=None):
        df_daily = self.fetch_daily_data(ticker, period="60d")
        benchmark_daily = self.fetch_daily_data(self.benchmark_ticker, period="60d")
        
        if df_daily is None or len(df_daily) < 2:
            return None

        # Fetch base interval (usually 5m)
        df_base = self.fetch_data(ticker, period="40d", interval=self.interval)
        if df_base is None or len(df_base) < 20:
            return None
            
        if target_date is not None:
            df_base = df_base[df_base.index.date <= target_date]
            df_daily = df_daily[df_daily.index.date <= target_date]
            benchmark_daily = benchmark_daily[benchmark_daily.index.date <= target_date]
            
        if len(df_base) < 20 or len(df_daily) < 2:
            return None
            
        base_eval = self.evaluate_timeframe(df_base, df_daily, benchmark_daily, ticker, self.interval)
        
        if base_eval is None:
            return None
            
        final_eval = base_eval
            
        # Multi-Timeframe Confirmation Logic
        if self.multi_tf and base_eval['struct_pass'] and not base_eval['body_pass']:
            df_15m = self.fetch_data(ticker, period="40d", interval="15m")
            if df_15m is not None:
                if target_date is not None:
                    df_15m = df_15m[df_15m.index.date <= target_date]
                if len(df_15m) > 5:
                    eval_15m = self.evaluate_timeframe(df_15m, df_daily, benchmark_daily, ticker, "15m")
                    if eval_15m and eval_15m['layer1_pass']:
                        eval_15m['report'] = eval_15m['report'].replace("METRIC VALIDATION REPORT", "MULTI-TIMEFRAME UPGRADE REPORT")
                        final_eval = eval_15m
                    elif eval_15m:
                        eval_15m['report'] = eval_15m['report'].replace("METRIC VALIDATION REPORT", "MULTI-TIMEFRAME UPGRADE REPORT (Failed)")
                        final_eval = eval_15m

        return final_eval

    def format_report(self, ticker, o, h, l, c, bull, bear, body_ratio, body_pass,
                      pm_pass, vol_mult, inst_pass, vz_pass,
                      vwap_pass, cohesion_pass, pivot_pass,
                      l1_pass, l2_pass, l3_pass, direction, r1, s1, r2, s2, gap_pct, rvol_over, gap_over, ext_mom_over, tier, tf_label):
        
        struct_msg = f"FAIL (O:{o}, H:{h}, L:{l})"
        if bull:
            struct_msg = f"PASS (BULLISH Open==Low: {o})"
        elif bear:
            struct_msg = f"PASS (BEARISH Open==High: {o})"
            
        body_msg = "PASS" if body_pass else "FAIL"
        pm_msg = "PASS" if pm_pass else "FAIL"
        inst_msg = "PASS" if inst_pass else "FAIL"
        vz_msg = "PASS" if vz_pass else "FAIL"
        vwap_msg = "PASS" if vwap_pass else "FAIL"
        coh_msg = "PASS" if cohesion_pass else "FAIL"
        piv_msg = "PASS" if pivot_pass else "FAIL"
        
        decision = "TRADE REJECTED - "
        sizing = "N/A"
        
        if not l1_pass:
            decision += "Failed Layer 1 Screening"
        elif not l2_pass:
            decision += "Failed Layer 2 Liquidity/Environment"
        elif not l3_pass:
            decision += "Failed Layer 3 Concurrency"
        else:
            if tier == 1:
                decision = "STRATEGY TRIGGERED [TIER 1 CORE] - EXECUTE ENTRY"
                sizing = "100% Position Size"
            elif tier == 2:
                decision = "STRATEGY TRIGGERED [TIER 2 EXPLOSIVE] - EXECUTE ENTRY"
                sizing = "40% Position Size (High RVOL / Gap / Extreme Momentum Override Active)"
            
        target1 = r1 if direction == "BULLISH" else s1
        target2 = r2 if direction == "BULLISH" else s2
        stop = l - 0.05 if direction == "BULLISH" else h + 0.05

        report = f"""
## METRIC VALIDATION REPORT: {ticker} ({tf_label})
---
### LAYER 1: Structural Screening
*   [{'x' if (bull or bear) else ' '}] Open == Low / High Check: **[{'PASS' if (bull or bear) else 'FAIL'}]** {struct_msg}
*   [{'x' if body_pass else ' '}] Candle Body Ratio (>= 70%): **[{body_msg}]** ({body_ratio}%)

### LAYER 2: Environment & Liquidity (Dynamic)
*   Baseline Checks: Pre-Mkt Vol: **[{pm_msg}]** | Value Zone Breakout: **[{vz_msg}]**
*   Volume Metrics: Inst Vol Spike: **[{inst_msg}]** ({vol_mult}x)
*   **Overrides Triggered:** 
    *   [{'x' if rvol_over else ' '}] RVOL Explosion (>= 5x)
    *   [{'x' if gap_over else ' '}] Gap & Momentum Exception (Gap: {gap_pct}%, Body: {body_ratio}%)
    *   [{'x' if ext_mom_over else ' '}] Extreme Momentum Exception (100% Body Efficiency)
    *   Layer 2 Status: **[{'PASS' if l2_pass else 'FAIL'}]** (Tier {tier if tier > 0 else 'N/A'})

### LAYER 3: Concurrency Matrix
*   [{'x' if vwap_pass else ' '}] VWAP & Supertrend Alignment: **[{vwap_msg}]** { '(Tier 2 Bypassed)' if tier==2 else '' }
*   [{'x' if cohesion_pass else ' '}] Broader Index & Sector Cohesion: **[{coh_msg}]** { '(Tier 2 Bypassed)' if tier==2 else '' }
*   [{'x' if pivot_pass else ' '}] Pivot Zone Floor/Ceiling Clearance: **[{piv_msg}]** { '(Tier 2 Bypassed)' if tier==2 else '' }

---
## FINAL ORDER LOGIC
**DECISION:** {decision}

**EXECUTION PARAMETERS (If Triggered):**
*   **Direction:** {direction}
*   **Position Sizing:** {sizing}
*   **Entry Trigger Price:** {c}
*   **Stop-Loss:** {round(stop, 2)} (1 tick past structural extreme)
*   **Targets:** T1: {round(target1, 2)} / T2: {round(target2, 2)}
"""
        return report

if __name__ == "__main__":
    tickers = ["ACC.NS"]
    engine = TradingEngine(tickers)
    for t in tickers:
        report = engine.process_stock(t)
        if report:
            print(report)
