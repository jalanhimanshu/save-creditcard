import pandas as pd
from database import get_db_connection

# Baseline valuations for Indian market in Rupees (e.g. 0.25 Rs = 25 Paise)
BASELINE_CPP = {
    'SBI Rewardz': 0.25,
    'BOB Rewardz': 0.25,
    'HDFC Reward Points': 0.50,
    'NeuCoins': 1.0,
    'Swiggy Cashback': 1.0,
    'Amex MR (India)': 0.30,
    'HSBC Rewards': 0.20,
    'IDFC Rewards': 0.25,
    'ICICI Rewards': 0.25,
    'Adani Rewardz': 0.25,
    'MyCash': 1.0,
    'IndusInd Rewards': 1.0,
    'Yes Rewards': 0.25,
    'PVR Tickets': 0.50,
    'Fuel Points': 0.25,
    'Scapia Coins': 0.20,
    'Equitas Rewards': 0.20,
    'Cashback': 1.0,
    'Edge Rewards': 0.50
}

def get_baseline_cpp(program: str) -> float:
    return BASELINE_CPP.get(program, 0.20)

def suggest_best_card(category: str, spend_amount: float) -> list:
    """
    Evaluates all active cards using Indian spend_unit mathematics.
    Returns a ranked list sorted by financial yield in ₹.
    """
    with get_db_connection() as conn:
        query = """
            SELECT c.card_name, c.program, c.spend_unit, m.category, m.multiplier
            FROM cards c
            JOIN multipliers m ON c.card_id = m.card_id
        """
        df = pd.read_sql_query(query, conn)
    
    results = []
    
    grouped = df.groupby(['card_name', 'program', 'spend_unit'])
    
    for (card_name, program, spend_unit), group in grouped:
        cat_match = group[group['category'].str.lower() == category.lower()]
        
        if not cat_match.empty:
            multiplier = float(cat_match.iloc[0]['multiplier'])
        else:
            catch_all = group[group['category'].str.lower() == 'catch_all']
            if not catch_all.empty:
                multiplier = float(catch_all.iloc[0]['multiplier'])
            else:
                multiplier = 1.0
                
        baseline_cpp = get_baseline_cpp(program)
        
        # Indian Market Formula: Points = (Spend Amount / Spend_Unit) * Multiplier
        # E.g., points are awarded per Rs 100 or 150 block.
        eligible_spend_blocks = int(spend_amount // spend_unit)
        total_points = eligible_spend_blocks * multiplier
        
        # V = Total Points * Baseline CPP (where CPP is in ₹)
        v = total_points * baseline_cpp
        
        results.append({
            'card_name': card_name,
            'program': program,
            'multiplier': multiplier,
            'spend_unit': spend_unit,
            'yield_rupees': v
        })
        
    ranked_cards = sorted(results, key=lambda x: x['yield_rupees'], reverse=True)
    return ranked_cards

def evaluate_redemption(program: str, cash_cost: float, points_required: int) -> dict:
    """
    Validates if a redemption yields a good value based on baseline program CPP.
    cash_cost is assumed to be in Rupees.
    """
    if points_required == 0:
        achieved_cpp = 0.0
    else:
        achieved_cpp = (cash_cost / points_required)
        
    baseline = get_baseline_cpp(program)
    
    rating = "Great Value" if achieved_cpp >= baseline else "Bad Value"
    
    return {
        'program': program,
        'achieved_cpp': achieved_cpp,
        'baseline_cpp': baseline,
        'rating': rating
    }

def evaluate_flight_deal(cash_cost: float, points_cost: int, program: str) -> dict:
    """
    Evaluates the 'Effective' cost of a flight booking by factoring in opportunity costs.
    """
    # 1. Evaluate Points Route
    baseline_cpp = get_baseline_cpp(program)
    effective_points_value_rs = points_cost * baseline_cpp
    
    # 2. Evaluate Cash Route
    best_cards_for_travel = suggest_best_card('travel', cash_cost)
    
    if best_cards_for_travel:
        best_card = best_cards_for_travel[0]
        cash_yield = best_card['yield_rupees']
        best_card_name = f"{best_card['card_name']} ({best_card['program']})"
    else:
        cash_yield = 0.0
        best_card_name = "No Card"
        
    effective_cash_cost = cash_cost - cash_yield
    
    # 3. Determine the Smarter Deal
    if effective_cash_cost < effective_points_value_rs:
        winner = "Cash"
        savings = effective_points_value_rs - effective_cash_cost
    else:
        winner = "Points"
        savings = effective_cash_cost - effective_points_value_rs
        
    return {
        'cash_cost': cash_cost,
        'effective_cash_cost': effective_cash_cost,
        'cash_yield': cash_yield,
        'best_card_name': best_card_name,
        'points_cost': points_cost,
        'effective_points_value_rs': effective_points_value_rs,
        'baseline_cpp': baseline_cpp,
        'winner': winner,
        'savings': savings
    }
