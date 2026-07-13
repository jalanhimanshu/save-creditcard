import streamlit as st
import pandas as pd
from database import get_db_connection
import optimizer
from agents import ask_savepoints_ai, auto_discover_card_details

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
    st.title("SavePoints Rewards Dashboard")
    st.markdown("### Please Login or Sign Up")
    
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    
    with login_tab:
        l_user = st.text_input("Username", key="l_user")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
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
        
        st.markdown("---")
        st.button("Continue with Google", disabled=True, help="Requires Google Cloud Platform setup by Admin")

    with signup_tab:
        s_user = st.text_input("Choose Username", key="s_user")
        s_email = st.text_input("Email", key="s_email")
        s_pass = st.text_input("Choose Password", type="password", key="s_pass")
        if st.button("Sign Up"):
            if not s_user or not s_pass:
                st.error("Username and password are required")
            else:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'user')", (s_user, hash_password(s_pass), s_email))
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
                    st.error("Username already exists!")
    st.stop()

col_title, col_logout = st.columns([0.9, 0.1])
with col_title:
    st.title(f"SavePoints Rewards Dashboard - Welcome {st.session_state.username}!")
with col_logout:
    def logout():
        token = st.query_params.get('session_id')
        if token:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM session_tokens WHERE token = ?", (token,))
                conn.commit()
        st.query_params.clear()
        st.session_state.clear()
        
    st.button("Logout", on_click=logout)

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
        df_cards = pd.read_sql_query("SELECT card_id, card_name, program, current_balance FROM cards WHERE user_id = ?", conn, params=(st.session_state.user_id,))
    
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
                cursor.execute("UPDATE cards SET current_balance = ? WHERE card_name = ? AND user_id = ?", (new_balance, selected_card, st.session_state.user_id))
                conn.commit()
            st.success(f"Successfully updated {selected_card} balance to {new_balance}.")
            st.rerun()

    st.subheader("Manage Portfolio")
    colM1, colM2 = st.columns(2)
    
    with colM1:
        with st.expander("➕ Add a New Card"):
            add_mode = st.radio("Add Method", ["AI Auto-Discovery", "Manual Entry"])
            if add_mode == "AI Auto-Discovery":
                with st.form("add_card_form_ai"):
                    new_card_name = st.text_input("Card Name (e.g., Axis Magnus)")
                    new_init_bal = st.number_input("Initial Balance", min_value=0, step=1000)
                    new_spend_unit = st.number_input("Spend Unit (₹)", min_value=50, value=100, step=50)
                    
                    add_submitted = st.form_submit_button("Add Card to Portfolio")
                    
                    if add_submitted and new_card_name:
                        with st.spinner("AI is discovering actual reward multipliers & links for this card..."):
                            try:
                                with get_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO cards (user_id, card_name, program, current_balance, spend_unit, reward_link) VALUES (?, ?, ?, ?, ?, ?)", 
                                                 (st.session_state.user_id, new_card_name, "Pending AI Discovery...", new_init_bal, new_spend_unit, "Pending AI Discovery..."))
                                    new_card_id = cursor.lastrowid
                                
                                    ai_data = auto_discover_card_details(new_card_name)
                                    
                                    if "error" not in ai_data:
                                        real_program = ai_data.get("reward_program", f"{new_card_name} Rewards")
                                        real_link = ai_data.get("reward_link", "Not Found")
                                        cursor.execute("UPDATE cards SET program = ?, reward_link = ? WHERE card_id = ?", (real_program, real_link, new_card_id))
                                        
                                        mults = ai_data.get("multipliers", [])
                                        for m in mults:
                                            cursor.execute("INSERT INTO multipliers (card_id, category, multiplier) VALUES (?, ?, ?)",
                                                         (new_card_id, m.get("category", "catch_all"), float(m.get("multiplier", 1.0))))
                                        st.success(f"✅ Added **{new_card_name}** ({real_program}) with AI-discovered multipliers!")
                                    else:
                                        fallback_program = f"{new_card_name} Rewards"
                                        cursor.execute("UPDATE cards SET program = ?, reward_link = ? WHERE card_id = ?", 
                                                     (fallback_program, "https://www.google.com/search?q=" + new_card_name.replace(" ", "+") + "+credit+card", new_card_id))
                                        cursor.execute("INSERT INTO multipliers (card_id, category, multiplier) VALUES (?, ?, ?)",
                                                     (new_card_id, "catch_all", 1.0))
                                        st.warning(f"⚠️ Added **{new_card_name}** with 1x base rate. AI discovery failed — refresh the page and edit the card to update it.")
                                                     
                                    conn.commit()
                            except Exception as e:
                                if "UNIQUE constraint" in str(e):
                                    st.error(f"❌ A card named **{new_card_name}** already exists in your portfolio.")
                                else:
                                    st.error(f"❌ Error adding card: {e}")
                        st.rerun()
            else:
                with st.form("add_card_form_manual"):
                    m_card_name = st.text_input("Card Name")
                    m_program = st.text_input("Reward Program Name")
                    m_init_bal = st.number_input("Initial Balance", min_value=0, step=1000)
                    m_spend_unit = st.number_input("Spend Unit (₹)", min_value=50, value=100, step=50)
                    m_base_mult = st.number_input("Base Multiplier (x)", min_value=0.1, value=1.0, step=0.1)
                    m_submit = st.form_submit_button("Save Card")
                    
                    if m_submit and m_card_name and m_program:
                        try:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO cards (user_id, card_name, program, current_balance, spend_unit, reward_link) VALUES (?, ?, ?, ?, ?, ?)", 
                                             (st.session_state.user_id, m_card_name, m_program, m_init_bal, m_spend_unit, "Manual Entry"))
                                new_card_id = cursor.lastrowid
                                cursor.execute("INSERT INTO multipliers (card_id, category, multiplier) VALUES (?, ?, ?)",
                                             (new_card_id, "catch_all", m_base_mult))
                                conn.commit()
                            st.success(f"✅ Manually added {m_card_name}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error adding card: {e}")
                    
    with colM2:
        with st.expander("❌ Remove a Card"):
            with st.form("remove_card_form"):
                card_to_remove = st.selectbox("Select Card to Delete", df_cards['card_name'].tolist())
                remove_submitted = st.form_submit_button("Delete Permanently")
                
                if remove_submitted:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        # ON DELETE CASCADE handles the multipliers automatically
                        cursor.execute("DELETE FROM cards WHERE card_name = ? AND user_id = ?", (card_to_remove, st.session_state.user_id))
                        conn.commit()
                    st.success(f"Permanently removed {card_to_remove}.")
                    st.rerun()

# ==========================================
# SHARED: Dynamic program list for all tabs
# ==========================================
with get_db_connection() as conn:
    df_programs = pd.read_sql_query("SELECT DISTINCT program FROM cards WHERE user_id = ?", conn, params=(st.session_state.user_id,))
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
            WHERE t.source_program IN (SELECT DISTINCT program FROM cards WHERE user_id = ?)
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
