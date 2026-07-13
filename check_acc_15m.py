import sys
import os

sys.path.append(r'd:\AntiGravity project')

from scanner import TradingEngine

if __name__ == "__main__":
    engine = TradingEngine(["ACC.NS"], interval="15m")
    report = engine.process_stock("ACC.NS")
    
    if report:
        print(report)
    else:
        print("No valid data or report generated for ACC.NS on 15m")
