import streamlit as st
import pandas as pd
from database import get_db_connection
import optimizer
from agents import ask_savepoints_ai, auto_discover_card_details
import re

st.set_page_config(page_title="SavePoints Dashboard (India)", layout="wide")

import time
import threading

@st.cache_data(ttl=3600, show_spinner=False)
def trigger_background_sync():
    from agents import run_daily_market_sync, run_redemption_offer_sync, run_twitter_sync
    def run_sync_tasks():
        try:
            run_daily_market_sync()
            run_redemption_offer_sync()
            run_twitter_sync()
        except Exception as e:
            pass
    thread = threading.Thread(target=run_sync_tasks, daemon=True)
    thread.start()
    return time.time()

current_sync_time = trigger_background_sync()
if 'last_toast_time' not in st.session_state or st.session_state['last_toast_time'] != current_sync_time:
    st.toast("🔄 Running hourly AI market sync in the background...")
    st.session_state['last_toast_time'] = current_sync_time

import hashlib
import uuid

def hash_password(password):
    salt = "savepoints_salt_"
    return hashlib.sha256((salt + password).encode()).hexdigest()

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Streamlit native persistent session using query parameters and database
token = st.query_params.get('session_id')
if token and st.session_state.user_id is None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username, u.role 
            FROM users u
            JOIN session_tokens s ON u.user_id = s.user_id
            WHERE s.token = ?
        """, (token,))
        user = cursor.fetchone()
        if user:
            st.session_state.user_id = user[0]
            st.session_state.username = user[1]
            st.session_state.role = user[2]
            st.rerun()

if not st.session_state.user_id:
    
    # --- SAAS PLAIN BACKGROUND OVERRIDE ---
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="viewerBadge"] {display: none !important;}
            div[class^="viewerBadge"] {display: none !important;}
            
            [data-testid="stAppViewContainer"] {
                background-color: #e2e8f0;
            }
            [data-testid="stAppViewBlockContainer"] {
                padding-top: 5rem !important;
                max-width: 100% !important;
            }
            [data-testid="stSidebar"] {
                display: none;
            }
            header[data-testid="stHeader"] {
                display: none !important;
            }
            
            /* Style the center column exactly as a solid dark panel */
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                background: #111827 !important;
                border-radius: 4px !important;
                padding: 4rem 3rem !important;
                box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5) !important;
                border: none !important;
            }
            
            /* Ensure clean text styling */
            h1, p, label, .stTabs span {
                color: #ffffff !important;
                text-shadow: none !important;
            }
            
            /* Make inputs look like the screenshot */
            input {
                background-color: rgba(255, 255, 255, 0.1) !important;
                color: white !important;
                border: 1px solid rgba(255,255,255,0.2) !important;
            }
            
            /* Custom Form Styling */
            .stTabs [data-baseweb="tab-list"] {
                gap: 2rem;
                justify-content: center;
            }
            div.stButton > button:first-child {
                background-color: #4F46E5;
                color: white;
                border-radius: 8px;
                padding: 0.75rem 1rem;
                font-weight: 600;
                border: none;
            }
            div.stButton > button:first-child:hover {
                background-color: #4338CA;
                color: white;
            }
            
            /* Responsive adjustments for mobile */
            @media (max-width: 768px) {
                [data-testid="stAppViewBlockContainer"] {
                    padding-top: 2rem !important;
                }
                div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                    padding: 2rem 1.5rem !important;
                    border-radius: 12px !important;
                }
                div[data-testid="stHorizontalBlock"] > div:first-child,
                div[data-testid="stHorizontalBlock"] > div:last-child {
                    display: none !important;
                }
                [data-testid="stAppViewContainer"] {
                    background-position: right center !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)
    col1, col_form_c, col3 = st.columns([0.2, 1.4, 2.4])
    
    with col_form_c:
        st.markdown("<h1 style='text-align: center;'>Welcome Back</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 2rem; opacity: 0.7;'>Sign in to continue to SavePoints.</p>", unsafe_allow_html=True)
        
        login_tab, signup_tab = st.tabs(["Sign In", "Create Account"])
        
        with login_tab:
            l_user = st.text_input("Email Address", key="l_user")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            st.markdown("<div style='text-align: right;'><a href='#' style='color: #4F46E5; font-size: 0.875rem; text-decoration: none;'>Forgot Password?</a></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Sign In", use_container_width=True):
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id, role FROM users WHERE username = ? AND password_hash = ?", (l_user, hash_password(l_pass)))
                    user = cursor.fetchone()
                    if user:
                        st.session_state.user_id = user[0]
                        st.session_state.role = user[1]
                        st.session_state.username = l_user
                        
                        new_token = str(uuid.uuid4())
                        cursor.execute("INSERT INTO session_tokens (token, user_id) VALUES (?, ?)", (new_token, user[0]))
                        conn.commit()
                        st.query_params['session_id'] = new_token
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
            
            st.markdown("""
            <div style="display: flex; align-items: center; margin: 2rem 0;">
                <div style="flex-grow: 1; height: 1px; background-color: rgba(128,128,128,0.2);"></div>
                <span style="padding: 0 1rem; opacity: 0.6; font-size: 0.875rem;">or continue with</span>
                <div style="flex-grow: 1; height: 1px; background-color: rgba(128,128,128,0.2);"></div>
            </div>
            """, unsafe_allow_html=True)
            st.button("Continue with Google", disabled=True, use_container_width=True)

        with signup_tab:
            s_user = st.text_input("Email Address", key="s_user")
            s_pass = st.text_input("Choose Password", type="password", key="s_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Create Account", use_container_width=True):
                if not s_user or not s_pass:
                    st.error("Email and password are required")
                elif not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", s_user):
                    st.error("Please enter a valid email address")
                else:
                    try:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'user')", (s_user, hash_password(s_pass), s_user))
                            conn.commit()
                            
                            cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (s_user,))
                            user = cursor.fetchone()
                            st.session_state.user_id = user[0]
                            st.session_state.role = user[1]
                            st.session_state.username = s_user
                            
                            new_token = str(uuid.uuid4())
                            cursor.execute("INSERT INTO session_tokens (token, user_id) VALUES (?, ?)", (new_token, user[0]))
                            conn.commit()
                            st.query_params['session_id'] = new_token
                            st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Email is already registered!")
    st.stop()

st.title("SavePoints Rewards Dashboard")

with st.sidebar:
    st.markdown(f"**Logged in as:**<br>{st.session_state.username}", unsafe_allow_html=True)
    def logout():
        token = st.query_params.get('session_id')
        if token:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM session_tokens WHERE token = ?", (token,))
                conn.commit()
        st.query_params.clear()
        st.session_state.clear()
        
    st.button("Logout", on_click=logout, use_container_width=True)
    st.markdown("---")
tabs = ["Dashboard Overview", "Which Card to Use", "Redemption Calculator", "Smarter Flight Bookings", "Ask SavePoints AI"]
if st.session_state.role == 'admin':
    tabs.append("Admin Control Panel")
    
rendered_tabs = st.tabs(tabs)
tab1, tab2, tab3, tab4, tab5 = rendered_tabs[:5]
if st.session_state.role == 'admin':
    tab6 = rendered_tabs[5]

# ==========================================
# TAB 1: DASHBOARD OVERVIEW
# ==========================================
with tab1:
    st.header("Dashboard Overview")
    
    # Display AI Sync Status
    try:
        with open("last_sync.txt", "r") as f:
            last_sync = f.read().strip()
    except FileNotFoundError:
        last_sync = "Never (Background sync is starting now)"
        
    st.info(f"🤖 **Market Intelligence Agent Sync:** Last updated on {last_sync}")
    
    colA, colB = st.columns(2)
    with colA:
        try:
            with open("market_report.md", "r", encoding="utf-8") as f:
                market_content = f.read()
            with st.expander("📉 **View Latest Market Devaluations & Alerts (from CardExpert.in)**", expanded=True):
                st.markdown(market_content)
        except FileNotFoundError:
            pass
        
        try:
            with open("latest_offers.md", "r", encoding="utf-8") as f:
                offers_content = f.read()
            with st.expander("🎁 **View Today's Active Redemption Offers (from AI Agent)**", expanded=True):
                st.markdown(offers_content)
        except FileNotFoundError:
            pass

    with colB:
        st.subheader("🐦 Live Social Media Alerts")
        st.info("Scanning @card24_ai, @savingssimpl, @rewardsraja, @ccg33k every 60 mins.")
        try:
            with open("twitter_alerts.md", "r", encoding="utf-8") as f:
                twitter_content = f.read()
            st.markdown(twitter_content)
        except FileNotFoundError:
            st.write("Waiting for first 60-minute scan...")
    
    # Fetch all cards dynamically
    with get_db_connection() as conn:
        df_cards = pd.read_sql_query("""
            SELECT uc.id, cm.card_name, cm.program, uc.current_balance 
            FROM user_cards uc 
            JOIN card_metadata cm ON uc.meta_id = cm.meta_id 
            WHERE uc.user_id = ?
        """, conn, params=(st.session_state.user_id,))
    
    # Calculate standalone values and combined net worth
    df_cards['baseline_cpp_rs'] = df_cards['program'].apply(optimizer.get_baseline_cpp)
    df_cards['cash_value_rs'] = df_cards['current_balance'] * df_cards['baseline_cpp_rs']
    
    total_net_worth = df_cards['cash_value_rs'].sum()
    st.metric("Combined Net Worth", f"₹{total_net_worth:,.2f}")
    
    st.subheader("Portfolio")
    # Using width parameter to resolve deprecation warning
    st.dataframe(df_cards[['card_name', 'program', 'current_balance', 'cash_value_rs']], width=800)
    
    st.subheader("Update Balance")
    with st.form("update_balance_form"):
        selected_card = st.selectbox("Select Card", df_cards['card_name'].tolist())
        new_balance = st.number_input("New Point Balance", min_value=0, step=1000)
        submitted = st.form_submit_button("Update Balance")
        
        if submitted:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT meta_id FROM card_metadata WHERE card_name = ?", (selected_card,))
                m_id = cursor.fetchone()[0]
                cursor.execute("UPDATE user_cards SET current_balance = ? WHERE meta_id = ? AND user_id = ?", (new_balance, m_id, st.session_state.user_id))
                conn.commit()
            st.success(f"Successfully updated {selected_card} balance to {new_balance}.")
            st.rerun()

    st.subheader("Manage Portfolio")
    colM1, colM2 = st.columns(2)
    
    with colM1:
        with st.expander("➕ Add a New Card"):
            with get_db_connection() as conn:
                df_global_cards = pd.read_sql_query("SELECT card_name, meta_id FROM card_metadata ORDER BY card_name", conn)
            
            add_mode = st.radio("Add Method", ["Select from Global Catalog", "Request Unlisted Card"])
            
            if add_mode == "Select from Global Catalog":
                with st.form("add_card_form_global"):
                    selected_global = st.selectbox("Choose a Card", df_global_cards['card_name'].tolist())
                    new_init_bal = st.number_input("Initial Balance", min_value=0, step=1000)
                    new_spend_unit = st.number_input("Spend Unit (₹)", min_value=50, value=100, step=50)
                    
                    if st.form_submit_button("Add to Portfolio"):
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            m_id = df_global_cards.loc[df_global_cards['card_name'] == selected_global, 'meta_id'].values[0]
                            try:
                                cursor.execute("INSERT INTO user_cards (user_id, meta_id, current_balance, spend_unit) VALUES (?, ?, ?, ?)",
                                             (st.session_state.user_id, int(m_id), new_init_bal, new_spend_unit))
                                conn.commit()
                                st.success(f"✅ Added {selected_global} to your portfolio!")
                            except sqlite3.IntegrityError:
                                st.error("❌ You already have this card in your portfolio.")
                        st.rerun()
            else:
                with st.form("add_card_form_request"):
                    req_card_name = st.text_input("Card Name (e.g., SBI Cashback)")
                    req_init_bal = st.number_input("Initial Balance", min_value=0, step=1000)
                    req_spend_unit = st.number_input("Spend Unit (₹)", min_value=50, value=100, step=50)
                    
                    if st.form_submit_button("Submit Request"):
                        if req_card_name:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO card_requests (user_id, requested_card_name, initial_balance, spend_unit) VALUES (?, ?, ?, ?)",
                                             (st.session_state.user_id, req_card_name, req_init_bal, req_spend_unit))
                                conn.commit()
                            st.success(f"✅ Submitted request for {req_card_name}. It will appear here once approved by Admin.")
                            st.rerun()
                        else:
                            st.error("Please enter a card name.")
        
        # Display Pending Requests
        with get_db_connection() as conn:
            df_pending = pd.read_sql_query("SELECT requested_card_name, status FROM card_requests WHERE user_id = ? AND status = 'pending'", conn, params=(st.session_state.user_id,))
        if not df_pending.empty:
            st.markdown("**Your Pending Requests:**")
            for _, row in df_pending.iterrows():
                st.caption(f"⏳ {row['requested_card_name']} (Pending Admin Approval)")
                    
    with colM2:
        with st.expander("❌ Remove a Card"):
            with st.form("remove_card_form"):
                card_to_remove = st.selectbox("Select Card to Delete", df_cards['card_name'].tolist())
                remove_submitted = st.form_submit_button("Delete Permanently")
                
                if remove_submitted:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT meta_id FROM card_metadata WHERE card_name = ?", (card_to_remove,))
                        m_id = cursor.fetchone()[0]
                        cursor.execute("DELETE FROM user_cards WHERE meta_id = ? AND user_id = ?", (m_id, st.session_state.user_id))
                        conn.commit()
                    st.success(f"Permanently removed {card_to_remove}.")
                    st.rerun()

# ==========================================
# SHARED: Dynamic program list for all tabs
# ==========================================
with get_db_connection() as conn:
    df_programs = pd.read_sql_query("""
        SELECT DISTINCT cm.program 
        FROM user_cards uc 
        JOIN card_metadata cm ON uc.meta_id = cm.meta_id 
        WHERE uc.user_id = ?
    """, conn, params=(st.session_state.user_id,))
db_programs = [p for p in df_programs['program'].tolist() if p != "Pending AI Discovery..."]
all_programs = sorted(list(set(db_programs)))

# ==========================================
# TAB 2: "WHICH CARD TO USE" RECOMMENDATION ENGINE
# ==========================================
with tab2:
    st.header("Which Card to Use")
    
    col1, col2 = st.columns(2)
    with col1:
        # Dynamically fetch unique categories for the dropdown, adding defaults
        with get_db_connection() as conn:
            df_cats = pd.read_sql_query("SELECT DISTINCT category FROM multipliers WHERE category != 'catch_all'", conn)
        categories = df_cats['category'].tolist()
        categories.extend(['gas', 'grocery', 'upi']) 
        
        selected_category = st.selectbox("Transaction Category", list(set(categories)))
    with col2:
        spend_amount = st.number_input("Transaction Spend Amount (₹)", min_value=0.0, value=10000.0, step=500.0)
        spend_submitted = st.button("Get Recommendations")
        
    if spend_submitted:
        ranked_cards = optimizer.suggest_best_card(selected_category, spend_amount, st.session_state.user_id)
        if ranked_cards:
            best_card = ranked_cards[0]
            # Hero Element
            st.success(f"🏆 **#1 Recommended Card:** {best_card['card_name']} ({best_card['program']}) - Yields **₹{best_card['yield_rupees']:.2f}**")
            
            st.subheader("Comparative Analysis")
            df_ranked = pd.DataFrame(ranked_cards)
            
            # Display horizontal bar chart
            st.bar_chart(df_ranked.set_index('card_name')['yield_rupees'])
            
            # Display data table using width
            st.dataframe(df_ranked[['card_name', 'program', 'multiplier', 'spend_unit', 'yield_rupees']], width=800)

# ==========================================
# TAB 3: REDEMPTION CALCULATOR & TRANSFER PARTNERS
# ==========================================
with tab3:
    st.header("Redemption Calculator & Transfer Partners")
    
    try:
        with open("latest_offers.md", "r", encoding="utf-8") as f:
            offers_content = f.read()
        st.info("💡 **AI Agent Tip:** Always check the active transfer bonuses below before making a redemption!")
        with st.expander("🎁 **Today's Active Redemption Offers**", expanded=True):
            st.markdown(offers_content)
    except FileNotFoundError:
        pass
    
    st.subheader("Transfer Partners Directory")
    with get_db_connection() as conn:
        query = """
            SELECT t.source_program, t.target_partner, t.transfer_ratio, t.est_value_cpp 
            FROM transfer_partners t
            WHERE t.source_program IN (
                SELECT DISTINCT cm.program 
                FROM user_cards uc 
                JOIN card_metadata cm ON uc.meta_id = cm.meta_id 
                WHERE uc.user_id = ?
            )
        """
        df_partners = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))
    st.dataframe(df_partners, width=800)
    
    st.subheader("Live Calculator Suite")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        program_to_redeem = st.selectbox("Program", all_programs)
    with col4:
        cash_cost = st.number_input("Cash Cost (₹)", min_value=0.0, value=5000.0, step=500.0)
    with col5:
        points_required = st.number_input("Points Required", min_value=1, value=10000, step=1000)
        
    result = optimizer.evaluate_redemption(program_to_redeem, cash_cost, points_required)
    
    st.write("### Results")
    st.metric("Achieved CPP (₹)", f"₹{result['achieved_cpp']:.2f}")
    
    if result['rating'] == "Great Value":
        st.success(f"🌟 **{result['rating']}**! (Baseline: ₹{result['baseline_cpp']:.2f})")
    else:
        st.error(f"⚠️ **{result['rating']}** (Baseline: ₹{result['baseline_cpp']:.2f})")

# ==========================================
# TAB 4: SMARTER FLIGHT BOOKINGS
# ==========================================
with tab4:
    st.header("Smarter Flight Bookings: Cash vs Points")
    st.markdown("Before booking a flight, compare the true cost of using your points versus paying in cash with your best travel card.")
    
    colA, colB, colC = st.columns(3)
    with colA:
        flight_cash = st.number_input("Flight Cash Price (₹)", min_value=0.0, value=12000.0, step=500.0, key="flight_cash")
    with colB:
        flight_points = st.number_input("Flight Points Required", min_value=1, value=15000, step=1000, key="flight_points")
    with colC:
        programs_list = all_programs
        flight_program = st.selectbox("Points Program", programs_list, key="flight_program")
        
    flight_submitted = st.button("Evaluate Flight Deal")
    if flight_submitted:
        res = optimizer.evaluate_flight_deal(flight_cash, flight_points, flight_program, st.session_state.user_id)
        
        st.markdown("### Deal Analysis")
        if res['winner'] == "Cash":
            st.success(f"🏆 **SMARTER DEAL: PAY WITH CASH!** You save ₹{res['savings']:.2f} by hoarding your points and earning rewards instead.")
        else:
            st.success(f"🏆 **SMARTER DEAL: USE YOUR POINTS!** You save ₹{res['savings']:.2f} by using points instead of paying cash.")
            
        c1, c2 = st.columns(2)
        with c1:
            st.info("### 💳 Path 1: Pay with Cash")
            st.markdown(f"**Sticker Price:** ₹{res['cash_cost']:.2f}")
            st.markdown(f"**Best Card to Use:** {res['best_card_name']}")
            st.markdown(f"**Hidden Rewards Earned:** ₹{res['cash_yield']:.2f}")
            st.metric("Effective Cash Price", f"₹{res['effective_cash_cost']:.2f}")
            
        with c2:
            st.warning("### ✈️ Path 2: Pay with Points")
            st.markdown(f"**Points Required:** {res['points_cost']:,}")
            st.markdown(f"**Baseline Value:** ₹{res['baseline_cpp']:.2f} per point")
            st.markdown("**Hidden Cost of Burned Points:**")
            st.metric("Effective Points Value", f"₹{res['effective_points_value_rs']:.2f}")

# ==========================================
# TAB 5: ASK SAVEPOINTS AI
# ==========================================
with tab5:
    st.header("💬 Ask SavePoints AI (The 'Savvy' Killer)")
    st.markdown("Ask any question about your portfolio. *E.g., 'I am spending ₹50k on Amazon, which card should I use?'*")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if prompt := st.chat_input("Ask about your credit cards..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner(f"Analyzing your {len(df_cards)} cards..."):
                response = ask_savepoints_ai(prompt, st.session_state.user_id)
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ==========================================
# TAB 6: ADMIN CONTROL PANEL
# ==========================================
if st.session_state.role == 'admin':
    with tab6:
        st.header("Admin Control Panel")
        
        with get_db_connection() as conn:
            users_df = pd.read_sql_query("SELECT user_id, username, email, role FROM users", conn)
        st.subheader("Registered Users")
        st.dataframe(users_df, use_container_width=True)
        
        st.subheader("🤖 AI Learning Tracker (Unhandled Queries)")
        st.info("These questions bypassed the local Intent Router and were sent to Gemini. Review them to identify new keywords to add to the local rules engine!")
        try:
            with get_db_connection() as conn:
                unhandled_df = pd.read_sql_query("""
                    SELECT uq.query_id, u.username, uq.question, uq.timestamp 
                    FROM unhandled_queries uq
                    JOIN users u ON uq.user_id = u.user_id
                    ORDER BY uq.timestamp DESC
                """, conn)
            if unhandled_df.empty:
                st.success("No unhandled queries! The Intent Router is catching everything.")
            else:
                st.dataframe(unhandled_df, use_container_width=True)
                
                # Option to clear the tracker
                if st.button("Clear Learning Tracker"):
                    with get_db_connection() as conn:
                        conn.execute("DELETE FROM unhandled_queries")
                        conn.commit()
                    st.rerun()
        except Exception as e:
            st.error(f"Error loading unhandled queries: {e}")
        
        st.subheader("Pending Card Requests")
        with get_db_connection() as conn:
            requests_df = pd.read_sql_query("""
                SELECT cr.request_id, u.username, cr.requested_card_name, cr.initial_balance, cr.spend_unit
                FROM card_requests cr
                JOIN users u ON cr.user_id = u.user_id
                WHERE cr.status = 'pending'
            """, conn)
            
        if requests_df.empty:
            st.info("No pending card requests.")
        else:
            st.dataframe(requests_df, use_container_width=True)
            
            with st.form("admin_process_request"):
                selected_req_id = st.selectbox("Select Request ID to Process", requests_df['request_id'].tolist())
                proc_mode = st.radio("Processing Method", ["AI Auto-Discovery", "Manual Entry", "Reject Request"])
                
                m_program = st.text_input("Manual: Program Name")
                m_base_mult = st.number_input("Manual: Base Multiplier (x)", min_value=0.1, value=1.0, step=0.1)
                
                if st.form_submit_button("Process Request"):
                    req = requests_df[requests_df['request_id'] == selected_req_id].iloc[0]
                    req_id = int(req['request_id'])
                    c_name = req['requested_card_name']
                    with get_db_connection() as conn:
                        u_id = int(conn.execute("SELECT user_id FROM card_requests WHERE request_id = ?", (req_id,)).fetchone()[0])
                    bal = int(req['initial_balance'])
                    spend = int(req['spend_unit'])
                    
                    if proc_mode == "Reject Request":
                        with get_db_connection() as conn:
                            conn.execute("UPDATE card_requests SET status = 'rejected' WHERE request_id = ?", (req_id,))
                            conn.commit()
                        st.success(f"Rejected request {req_id}.")
                        st.rerun()
                        
                    elif proc_mode == "AI Auto-Discovery":
                        with st.spinner(f"AI discovering details for {c_name}..."):
                            ai_data = auto_discover_card_details(c_name)
                            if "error" not in ai_data:
                                real_program = ai_data.get("reward_program", f"{c_name} Rewards")
                                real_link = ai_data.get("reward_link", "Not Found")
                                mults = ai_data.get("multipliers", [{"category": "catch_all", "multiplier": 1.0}])
                            else:
                                real_program = f"{c_name} Rewards"
                                real_link = "Manual Update Required"
                                mults = [{"category": "catch_all", "multiplier": 1.0}]
                                st.warning("AI failed to discover card. Saved with default 1x multiplier.")
                            
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT OR IGNORE INTO card_metadata (card_name, program, reward_link) VALUES (?, ?, ?)",
                                             (c_name, real_program, real_link))
                                cursor.execute("SELECT meta_id FROM card_metadata WHERE card_name = ?", (c_name,))
                                meta_id = cursor.fetchone()[0]
                                
                                cursor.execute("DELETE FROM multipliers WHERE meta_id = ?", (meta_id,))
                                for m in mults:
                                    cursor.execute("INSERT INTO multipliers (meta_id, category, multiplier) VALUES (?, ?, ?)",
                                                 (meta_id, m.get("category", "catch_all"), float(m.get("multiplier", 1.0))))
                                                 
                                cursor.execute("INSERT OR IGNORE INTO user_cards (user_id, meta_id, current_balance, spend_unit) VALUES (?, ?, ?, ?)",
                                             (u_id, meta_id, bal, spend))
                                             
                                cursor.execute("UPDATE card_requests SET status = 'approved' WHERE request_id = ?", (req_id,))
                                conn.commit()
                            st.success(f"Successfully processed {c_name} via AI and added to user's portfolio!")
                            st.rerun()
                            
                    elif proc_mode == "Manual Entry":
                        if m_program:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO card_metadata (card_name, program, reward_link) VALUES (?, ?, ?) ON CONFLICT (card_name) DO NOTHING",
                                             (c_name, m_program, "Manual Entry"))
                                cursor.execute("SELECT meta_id FROM card_metadata WHERE card_name = ?", (c_name,))
                                meta_id = cursor.fetchone()[0]
                                
                                cursor.execute("DELETE FROM multipliers WHERE meta_id = ?", (meta_id,))
                                cursor.execute("INSERT INTO multipliers (meta_id, category, multiplier) VALUES (?, ?, ?)", (meta_id, "catch_all", m_base_mult))
                                
                                cursor.execute("INSERT OR IGNORE INTO user_cards (user_id, meta_id, current_balance, spend_unit) VALUES (?, ?, ?, ?)",
                                             (u_id, meta_id, bal, spend))
                                             
                                cursor.execute("UPDATE card_requests SET status = 'approved' WHERE request_id = ?", (req_id,))
                                conn.commit()
                            st.success(f"Successfully processed {c_name} manually!")
                            st.rerun()
                        else:
                            st.error("Program Name is required for Manual Entry.")
        
        st.subheader("Global Transfer Partners Database")
        st.info("Warning: Editing these values affects the redemption calculators for ALL users on the platform.")
        with get_db_connection() as conn:
            partners_df = pd.read_sql_query("SELECT * FROM transfer_partners", conn)
        
        edited_df = st.data_editor(partners_df, num_rows="dynamic", key="admin_partners_editor", use_container_width=True)
        if st.button("Save Global Partners Database"):
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM transfer_partners")
                    for _, row in edited_df.iterrows():
                        if pd.notna(row['source_program']) and pd.notna(row['target_partner']):
                            cursor.execute("INSERT INTO transfer_partners (source_program, target_partner, transfer_ratio, est_value_cpp) VALUES (?, ?, ?, ?)",
                                         (row['source_program'], row['target_partner'], row['transfer_ratio'], float(row['est_value_cpp'])))
                    conn.commit()
                st.success("Global transfer partners database updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving database: {e}")
