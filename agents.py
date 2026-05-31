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
        expected_output='A structured markdown report detailing recent credit card reward devaluations relevant to the user portfolio.',
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
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not found in environment.")
        return False
        
    try:
        # Dynamically fetch user cards
        with sqlite3.connect('savepoints.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT card_name FROM cards")
            cards = cursor.fetchall()
            cards_str = ", ".join([name for name, in cards])

        rss_data = fetch_cardexpert_rss()

        crew = create_market_crew()
        result = crew.kickoff(inputs={'portfolio_cards': cards_str, 'rss_feed_data': rss_data})
        
        with open("market_report.md", "w", encoding="utf-8") as f:
            f.write("### Market Intelligence & Devaluation Alerts\n\n")
            f.write(str(result))
            f.write(f"\n\n*(Sourced from CardExpert.in on {datetime.datetime.now().strftime('%I:%M %p, %Y-%m-%d')})*")

        with open("last_sync.txt", "w", encoding="utf-8") as f:
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        print("Market Sync Complete.")
        return True
    except Exception as e:
        print(f"Sync failed: {e}")
        return False

def fetch_apify_tweets():
    import urllib.request
    import json
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        return '{"error": "APIFY_API_TOKEN is not set in .env. Awaiting user API key."}'
    
    url = f"https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token={token}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({
        "searchTerms": ["#creditcardrewards OR @card24_ai OR @savingssimpl OR @rewardsraja OR @ccg33k"],
        "maxItems": 20
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        res = urllib.request.urlopen(req)
        data = json.loads(res.read())
        tweets = ""
        for i, item in enumerate(data[:20]):
            text = item.get("full_text", item.get("text", ""))
            author = item.get("user", {}).get("screen_name", "unknown")
            tweets += f"Tweet {i+1} (@{author}): {text}\n\n"
        return tweets if tweets else "No recent tweets found."
    except Exception as e:
        return f"Error fetching from Apify: {e}"

def create_twitter_crew():
    llm = get_llm()
    
    flash_deal_agent = Agent(
        role='Social Media Flash Deal Analyst',
        goal='Monitor X (Twitter) for real-time credit card offers and flash deals.',
        backstory="You are a FinTwit expert. You find the best deals by analyzing raw JSON feeds of the latest tweets.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    twitter_task = Task(
        description='''
        Read the following raw tweet data fetched directly from the Apify Twitter API:
        {apify_data}
        
        Find recent flash deals, reward multiplier promotions, or devaluations for ANY major Indian credit card.
        You may prioritize these specific cards if mentioned, but DO NOT filter out other cards:
        {portfolio_cards}
        
        Filter the noise and output a clean markdown list of any LIVE or RECENT offers.
        If no relevant new deals are found in the data, just say "No major flash deals found."
        ''',
        expected_output='A clean markdown list of live Twitter flash deals or a notice that none were found.',
        agent=flash_deal_agent
    )

    return Crew(
        agents=[flash_deal_agent],
        tasks=[twitter_task],
        process=Process.sequential
    )

def run_twitter_sync():
    print(f"[{datetime.datetime.now()}] Starting Hourly Twitter Sync...")
    if not os.getenv("GEMINI_API_KEY"):
        return False
        
    try:
        with sqlite3.connect('savepoints.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT card_name FROM cards")
            cards = cursor.fetchall()
            cards_str = ", ".join([name for name, in cards])

        apify_payload = fetch_apify_tweets()

        crew = create_twitter_crew()
        result = crew.kickoff(inputs={'portfolio_cards': cards_str, 'apify_data': apify_payload})
        
        with open("twitter_alerts.md", "w", encoding="utf-8") as f:
            f.write(str(result))
            f.write(f"\n\n*(Last scanned: {datetime.datetime.now().strftime('%I:%M %p')})*")
            
        print("Twitter Sync Complete.")
        return True
    except Exception as e:
        print(f"Twitter Sync failed: {e}")
        return False

def run_redemption_offer_sync():
    print(f"[{datetime.datetime.now()}] Starting Redemption Offers Sync...")
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not found in environment.")
        return False
        
    try:
        # Fetch portfolio data and transfer partners from DB
        with sqlite3.connect('savepoints.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT card_name, program, current_balance FROM cards")
            cards = cursor.fetchall()
            portfolio_str = "\n".join([f"- {c[0]} ({c[1]}): {c[2]} points" for c in cards])
            
            cursor.execute("SELECT source_program, target_partner, transfer_ratio, est_value_cpp FROM transfer_partners")
            partners = cursor.fetchall()
            partners_str = "\n".join([f"- {p[0]} -> {p[1]}: Ratio {p[2]}, Est. CPP Rs.{p[3]}" for p in partners])
            
        crew = create_redemption_crew()
        result = crew.kickoff(inputs={'portfolio_data': portfolio_str, 'transfer_partners_data': partners_str})
        
        with open("latest_offers.md", "w", encoding="utf-8") as f:
            f.write("### Active Transfer Bonuses & Offers\n\n")
            f.write(str(result))
            f.write(f"\n\n*(Last verified: {datetime.datetime.now().strftime('%I:%M %p, %Y-%m-%d')})*")
            
        print("Redemption Sync Complete.")
        return True
    except Exception as e:
        print(f"Redemption Sync failed: {e}")
        return False

def ask_savepoints_ai(user_question: str) -> str:
    """
    Acts as the 'Savvy' killer - a chat backend that reads the DB and answers questions.
    """
    import requests
    import json
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY is not set."
        
    try:
        with sqlite3.connect('savepoints.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT card_name, program, current_balance FROM cards")
            cards = cursor.fetchall()
            cards_context = "\n".join([f"- {c[0]} ({c[1]}): {c[2]} points" for c in cards])
            
            cursor.execute("SELECT c.card_name, m.category, m.multiplier FROM cards c JOIN multipliers m ON c.card_id = m.card_id")
            multipliers = cursor.fetchall()
            mult_context = "\n".join([f"- {m[0]} earns {m[2]}x on {m[1]}" for m in multipliers])
            
        system_context = f"""
        You are the 'SavePoints AI Advisor', an expert financial assistant built to outperform 'SaveSage'.
        You MUST base your answers on the user's specific portfolio below.
        
        The user's credit card portfolio:
        {cards_context}
        
        Their card multipliers:
        {mult_context}
        
        User Question: {user_question}
        
        Answer the user's question concisely, logically, and accurately to maximize their financial yield.
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": system_context}]}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response_json = response.json()
        
        if "error" in response_json:
            return f"API Error: {response_json['error'].get('message', 'Unknown error')}"
            
        return response_json["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"AI System Error: The model endpoint could not be reached or failed. Detail: {e}"

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
