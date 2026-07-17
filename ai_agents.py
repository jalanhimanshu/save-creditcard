import os
import sqlite3
import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

# Load environment variables
load_dotenv()

def get_llm():
    return "gemini/gemini-flash-latest"

def fetch_cardexpert_rss():
    import urllib.request
    import xml.etree.ElementTree as ET
    try:
        req = urllib.request.Request('https://www.cardexpert.in/feed/', headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req)
        root = ET.fromstring(res.read())
        items = root.findall('.//item')[:10]
        feed_data = ""
        for item in items:
            title = item.find('title').text if item.find('title') is not None else 'No Title'
            desc = item.find('description').text if item.find('description') is not None else 'No Desc'
            feed_data += f"Title: {title}\nSummary: {desc}\n\n"
        return feed_data
    except Exception as e:
        return f"Error fetching RSS: {e}"

def fetch_local_flash_deals():
    import urllib.request
    import xml.etree.ElementTree as ET
    
    deals = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. Fetch from CardExpert
    try:
        req_ce = urllib.request.Request('https://www.cardexpert.in/feed/', headers=headers)
        res_ce = urllib.request.urlopen(req_ce, timeout=10)
        root_ce = ET.fromstring(res_ce.read())
        
        ce_keywords = ['offer', 'discount', 'cashback', 'bonus', 'sale', 'reward', 'devaluation', 'changes']
        for item in root_ce.findall('.//item')[:10]:
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else '#'
            if any(k in title.lower() for k in ce_keywords):
                deals.append(f"- ⚡ **[CardExpert]** [{title}]({link})")
    except Exception:
        pass

    # 2. Fetch from DesiDime
    try:
        req_dd = urllib.request.Request('https://www.desidime.com/deals/new.rss', headers=headers)
        res_dd = urllib.request.urlopen(req_dd, timeout=10)
        root_dd = ET.fromstring(res_dd.read())
        
        # Desidime has all sorts of deals, so we only want credit card related ones
        dd_keywords = ['credit card', 'hdfc', 'sbi', 'icici', 'axis', 'amex', 'kotak', 'bob', 'indusind', 'au small', 'idfc']
        for item in root_dd.findall('.//item')[:25]:
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else '#'
            if any(k in title.lower() for k in dd_keywords):
                deals.append(f"- 💰 **[DesiDime]** [{title}]({link})")
    except Exception:
        pass

    if deals:
        return "\n".join(deals)
    else:
        return "No major flash deals or offers found recently."

def create_market_crew():
    llm = get_llm()
    
    market_intelligence_agent = Agent(
        role='Credit Card Market Intelligence Analyst',
        goal='Research the latest reward point devaluations and structural changes in the Indian credit card market.',
        backstory="You are a financial analyst specializing in Indian credit cards (HDFC, SBI, ICICI, etc.). Your job is to track sneaky devaluations, changes in spend multipliers, and baseline value adjustments across all major banks.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    research_task = Task(
        description='''
        Read the following RSS feed data from CardExpert.in representing the latest market news:
        {rss_feed_data}
        
        Filter this news against the user's specific portfolio:
        {portfolio_cards}
        
        Identify the 3 most significant recent reward devaluations, multiplier changes, or buffs affecting these specific cards or their respective banks (HDFC, SBI, ICICI, Amex, etc.).
        Output a structured summary of changes affecting multipliers, spend units, or baseline CPP.
        ''',
        expected_output='''A structured markdown report detailing recent credit card reward devaluations relevant to the user portfolio. 
        DO NOT include a letterhead, "To/From" fields, dates, or memo subjects. Start immediately with an "Executive Summary" header, followed by a markdown table cross-referencing the changes against the user's cards.''',
        agent=market_intelligence_agent
    )

    return Crew(
        agents=[market_intelligence_agent],
        tasks=[research_task],
        process=Process.sequential
    )

def create_redemption_crew():
    """
    Analyzes redemption opportunities using the transfer partners data from the DB.
    No web scraping needed — we feed it structured data directly.
    """
    llm = get_llm()
    
    redemption_analyst_agent = Agent(
        role='Reward Redemption Optimization Analyst',
        goal='Identify the highest-value redemption paths for Indian credit card points using transfer partner data and current market conditions.',
        backstory="You are a travel hacker and points expert. You analyze transfer partner ratios, estimated CPP values, and current market conditions to recommend the best redemption strategies.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    redemption_research_task = Task(
        description='''
        Analyze the following transfer partner data from the user's portfolio and identify the top 3 highest-value redemption opportunities:
        
        Transfer Partners:
        {transfer_partners_data}
        
        User's Card Portfolio and Balances:
        {portfolio_data}
        
        For each recommendation, explain:
        1. The Bank/Program and current point balance
        2. The Transfer Partner
        3. The Transfer Ratio and estimated CPP value
        4. Why this is a good redemption (e.g., sweet spots, upcoming devaluations to beat)
        
        Also flag any programs where points should NOT be redeemed right now (e.g., if a transfer bonus is expected soon).
        ''',
        expected_output='A clean markdown list of the top 3 recommended redemption strategies and any warnings.',
        agent=redemption_analyst_agent
    )

    return Crew(
        agents=[redemption_analyst_agent],
        tasks=[redemption_research_task],
        process=Process.sequential
    )

def run_daily_market_sync():
    print(f"[{datetime.datetime.now()}] Starting Daily Market Intelligence Sync...")
    try:
        rss_data = fetch_cardexpert_rss()
        
        with open("market_report.md", "w", encoding="utf-8") as f:
            f.write("### Market Intelligence & Devaluation Alerts\n\n")
            f.write(rss_data)
            f.write(f"\n\n*(Sourced from CardExpert.in on {datetime.datetime.now().strftime('%I:%M %p, %Y-%m-%d')})*")

        with open("last_sync.txt", "w", encoding="utf-8") as f:
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        print("Market Sync Complete.")
        return True
    except Exception as e:
        print(f"Sync failed: {e}")
        return False

def run_twitter_sync():
    print(f"[{datetime.datetime.now()}] Skipping Twitter Sync (AI disabled)...")
    return True

def run_redemption_offer_sync():
    print(f"[{datetime.datetime.now()}] Starting Redemption Offers Sync...")
    try:
        deals = fetch_local_flash_deals()
        with open("latest_offers.md", "w", encoding="utf-8") as f:
            f.write("### Active Transfer Bonuses & Offers\n\n")
            f.write(deals)
            f.write(f"\n\n*(Last verified: {datetime.datetime.now().strftime('%I:%M %p, %Y-%m-%d')})*")
            
        print("Redemption Sync Complete.")
        return True
    except Exception as e:
        print(f"Redemption Sync failed: {e}")
        return False

def ask_savepoints_ai(user_question: str, user_id: int) -> str:
    """
    Acts as the 'Savvy' killer - a chat backend that reads the DB and answers questions locally,
    falling back to Gemini only when necessary.
    """
    import requests
    import json
    from database import get_db_connection
    import os
    
    # --- INTENT ROUTER (Local Pre-Processing) ---
    q_lower = user_question.lower()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch user's cards
            cursor.execute("""
                SELECT cm.card_name, cm.program, uc.current_balance 
                FROM user_cards uc 
                JOIN card_metadata cm ON uc.meta_id = cm.meta_id 
                WHERE uc.user_id = ?
            """, (user_id,))
            user_cards = cursor.fetchall()
            
            # Identify if a specific card was mentioned
            mentioned_card = None
            for card in user_cards:
                c_name = card[0]
                if c_name.lower() in q_lower:
                    mentioned_card = c_name
                    break
            
            # Intent 1: Balance Check
            if any(k in q_lower for k in ["balance", "how many points", "my points", "total points"]):
                if not user_cards:
                    return "You don't have any cards in your portfolio yet! Add some from the Dashboard."
                if mentioned_card:
                    for c in user_cards:
                        if c[0] == mentioned_card:
                            return f"💰 **{c[0]} Balance:** {c[2]:,} points ({c[1]})"
                
                resp = "Here are your current balances:\n"
                for c in user_cards:
                    resp += f"- **{c[0]}**: {c[2]:,} points\n"
                return resp
                
            # Intent 2: Transfer Partners
            if any(k in q_lower for k in ["transfer", "partners", "convert", "redeem", "where can i use"]):
                if not user_cards:
                    return "You need to add some cards to your portfolio before checking transfer partners."
                
                if mentioned_card:
                    # Get program for mentioned card
                    program = [c[1] for c in user_cards if c[0] == mentioned_card][0]
                    cursor.execute("SELECT target_partner, transfer_ratio, est_value_cpp FROM transfer_partners WHERE source_program = ?", (program,))
                    partners = cursor.fetchall()
                    if not partners:
                        return f"I couldn't find any transfer partners for the **{program}** program attached to your {mentioned_card}."
                    
                    resp = f"✈️ **Transfer Partners for {mentioned_card} ({program})**\n\n| Partner | Ratio | Est. Value (CPP) |\n|---|---|---|\n"
                    for p in partners:
                        resp += f"| {p[0]} | {p[1]} | ₹{p[2]:.2f} |\n"
                    return resp
                
                # If they ask generally but we need to know which card
                if "which card" not in q_lower and "what card" not in q_lower:
                     return "Which card are you asking about? Please include the card name (e.g., 'What are my transfer partners for Axis Atlas?')"
            
            # Intent 3: Multipliers / Earning Rates
            if any(k in q_lower for k in ["multiplier", "earn", "reward rate", "how many points for", "give me for"]):
                if not user_cards:
                    return "Please add cards to your portfolio to view earning rates."
                
                if mentioned_card:
                    cursor.execute("""
                        SELECT m.category, m.multiplier 
                        FROM multipliers m 
                        JOIN card_metadata cm ON m.meta_id = cm.meta_id
                        WHERE cm.card_name = ?
                    """, (mentioned_card,))
                    mults = cursor.fetchall()
                    if not mults:
                        return f"I don't have earning rate data for your {mentioned_card}."
                    
                    resp = f"📊 **Earning Rates for {mentioned_card}**\n"
                    for m in mults:
                        resp += f"- **{m[0].replace('_', ' ').title()}**: {m[1]}x\n"
                    return resp
                
                # General query, ask for a specific card
                return "Which card's earning rates do you want to see? Please mention the card name."

            # Intent 4: Card Recommendation (Spend Category)
            if any(k in q_lower for k in ["which card", "should i use", "best card for", "spending", "spend"]):
                if not user_cards:
                    return "You don't have any cards in your portfolio yet! Add some from the Dashboard to get recommendations."
                
                target_category = 'catch_all'
                if any(k in q_lower for k in ["amazon", "flipkart", "myntra", "online", "shopping"]):
                    target_category = 'online_shopping'
                elif any(k in q_lower for k in ["flight", "hotel", "travel", "make my trip", "mmt"]):
                    target_category = 'travel'
                    if "mmt" in q_lower or "make my trip" in q_lower or "makemytrip" in q_lower:
                        target_category = 'mmt_bookings'
                elif any(k in q_lower for k in ["restaurant", "food", "dining", "zomato", "swiggy", "eat"]):
                    target_category = 'dining'
                    if "swiggy" in q_lower: target_category = 'swiggy'
                    if "zomato" in q_lower: target_category = 'zomato'
                elif any(k in q_lower for k in ["fuel", "petrol", "diesel", "gas"]):
                    target_category = 'fuel'
                elif any(k in q_lower for k in ["grocery", "supermarket", "departmental", "mart"]):
                    target_category = 'departmental_stores'
                elif any(k in q_lower for k in ["international", "foreign", "abroad", "usd"]):
                    target_category = 'international'
                elif any(k in q_lower for k in ["upi", "scan", "paytm", "phonepe", "gpay", "bharatpe"]):
                    target_category = 'upi'
                    
                cursor.execute("""
                    SELECT cm.card_name, m.multiplier
                    FROM user_cards uc
                    JOIN card_metadata cm ON uc.meta_id = cm.meta_id
                    JOIN multipliers m ON cm.meta_id = m.meta_id
                    WHERE uc.user_id = ? AND m.category = ?
                    ORDER BY m.multiplier DESC
                """, (user_id, target_category))
                best_match = cursor.fetchone()
                
                if best_match:
                    display_cat = target_category.replace('_', ' ').title()
                    return f"💡 For this spend ({display_cat}), you should use your **{best_match[0]}**. It earns the highest rate at **{best_match[1]}x** points!"
                else:
                    cursor.execute("""
                        SELECT cm.card_name, m.multiplier
                        FROM user_cards uc
                        JOIN card_metadata cm ON uc.meta_id = cm.meta_id
                        JOIN multipliers m ON cm.meta_id = m.meta_id
                        WHERE uc.user_id = ? AND m.category = 'catch_all'
                        ORDER BY m.multiplier DESC
                    """, (user_id,))
                    best_catch = cursor.fetchone()
                    if best_catch:
                         return f"💡 I don't see a specific category bonus for that, so use your best everyday card: **{best_catch[0]}** (earns **{best_catch[1]}x** points)."
                    return "I couldn't find a recommendation for this spend."

    except Exception as e:
        print(f"Intent Router Error: {e}")
        pass
        
    # --- FALLBACK TO GEMINI (API CALL) ---
    # Log the unhandled query for the self-learning system
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO unhandled_queries (user_id, question) VALUES (?, ?)", (user_id, user_question))
            conn.commit()
    except Exception as e:
        print(f"Failed to log unhandled query: {e}")

    # Gemini API is temporarily disabled to save quota.
    return "I'm currently in **Offline Mode** to save API quota! I can still help you locally with things like checking balances, listing transfer partners, and viewing earning multipliers. If you have a complex question, please try again later when the API limit resets."

def auto_discover_card_details(card_name: str) -> dict:
    """
    Pings Gemini to discover the exact category multipliers and official web link for a newly added card.
    Returns a dict with 'multipliers' and 'reward_link'.
    """
    import requests
    import json
    import re
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "API key not set"}
        
    prompt = f"""
    You are a credit card data extractor. I need the reward structure for the Indian credit card: '{card_name}'.
    Return a pure JSON object with no markdown formatting. It must have this exact structure:
    {{
        "reward_program": "Name of the points program (e.g. Edge Rewards, Amex MR, NeuCoins, Cashback)",
        "reward_link": "https://www.bank.com/official-card-page",
        "multipliers": [
            {{"category": "dining", "multiplier": 5}},
            {{"category": "travel", "multiplier": 3}},
            {{"category": "catch_all", "multiplier": 1}}
        ]
    }}
    Important: Always include a 'catch_all' category. Multipliers should be numbers representing the points earned per spend unit. Use categories like: dining, travel, online_shopping, fuel, catch_all.
    """
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        # Retry up to 3 times to handle transient 503 errors
        import time
        last_error = None
        for attempt in range(3):
            response = requests.post(url, headers=headers, json=data)
            response_json = response.json()
            
            if "candidates" in response_json:
                break  # success
            
            last_error = response_json
            if attempt < 2:
                time.sleep(2)  # wait 2s before retry
        else:
            return {"error": f"API Error after 3 attempts: {last_error}"}
            
        text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences
        text = re.sub(r'```json\n?', '', text)
        text = re.sub(r'```', '', text).strip()
        
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test execution
    run_redemption_offer_sync()
