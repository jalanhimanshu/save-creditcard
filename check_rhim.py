import sys
import os

# Add the directory containing scanner.py to the path
sys.path.append(r'd:\AntiGravity project')

from scanner import TradingEngine

if __name__ == "__main__":
    engine = TradingEngine(["RHIM.NS"])
    report = engine.process_stock("RHIM.NS")
    
    if report:
        print(report)
    else:
        print("No valid data or report generated for RHIM.NS")
