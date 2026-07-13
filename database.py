import sqlite3
import contextlib
import os

DB_FILE = 'savepoints.db'

@contextlib.contextmanager
def get_db_connection():
    """Provides a safe database connection context."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                email TEXT,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_metadata (
                meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT UNIQUE,
                program TEXT,
                reward_link TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                meta_id INTEGER,
                current_balance INTEGER,
                spend_unit INTEGER,
                UNIQUE(user_id, meta_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(meta_id) REFERENCES card_metadata(meta_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                requested_card_name TEXT,
                initial_balance INTEGER,
                spend_unit INTEGER,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multipliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_id INTEGER,
                category TEXT,
                multiplier REAL,
                FOREIGN KEY (meta_id) REFERENCES card_metadata (meta_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfer_partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_program TEXT,
                target_partner TEXT,
                transfer_ratio TEXT,
                est_value_cpp REAL
            )
        ''')
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM card_metadata")
        if cursor.fetchone()[0] == 0:
            seed_data(conn)

def seed_data(conn):
    import hashlib
    cursor = conn.cursor()
    
    salt = "savepoints_salt_"
    admin_password = hashlib.sha256((salt + 'password@him').encode()).hexdigest()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, email, role)
        VALUES (?, ?, ?, ?)
    ''', ('jalanhimanshu', admin_password, 'admin@savepoints.local', 'admin'))
    
    cursor.execute("SELECT user_id FROM users WHERE username = 'jalanhimanshu'")
    admin_id = cursor.fetchone()[0]
    
    # Insert Global Catalog: name, program, reward_link
    cards_meta = [
        ('SBI Elite', 'SBI Rewardz', 'https://www.sbicard.com/en/personal/rewards.page'),
        ('BOB Eterna', 'BOB Rewardz', 'https://www.bobcard.co.in/credit-card-types/eterna'),
        ('HDFC Diners Black Privilege', 'HDFC Reward Points', 'https://offers.smartbuy.hdfcbank.com/diners'),
        ('HDFC Tata Neu', 'NeuCoins', 'https://www.tataneu.com/neucoins'),
        ('HDFC Swiggy', 'Swiggy Cashback', 'https://www.hdfcbank.com/personal/pay/cards/credit-cards/swiggy-hdfc-bank-credit-card'),
        ('Amex Platinum Travel', 'Amex MR (India)', 'https://www.americanexpress.com/en-in/rewards/membership-rewards/'),
        ('HSBC Platinum', 'HSBC Rewards', 'https://www.hsbc.co.in/credit-cards/rewards/'),
        ('IDFC First Bank', 'IDFC Rewards', 'https://www.idfcfirstbank.com/credit-card/rewards'),
        ('ICICI Coral', 'ICICI Rewards', 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/coral-card/index.page'),
        ('ICICI Sapphiro', 'ICICI Rewards', 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/sapphiro/index.page'),
        ('ICICI Rupay', 'ICICI Rewards', 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/rupay-credit-card.page'),
        ('Adani One ICICI', 'Adani Rewardz', 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/adani-one.page'),
        ('ICICI MakeMyTrip', 'MyCash', 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/makemytrip.page'),
        ('IndusInd Indulge', 'IndusInd Rewards', 'https://www.indusind.com/in/en/personal/cards/credit-card/indulge-credit-card.html'),
        ('Yes Bank Reserv', 'Yes Rewards', 'https://www.yesbank.in/personal-banking/cards/credit-card/yes-first-exclusive'),
        ('Kotak Bank PVR', 'PVR Tickets', 'https://www.kotak.com/en/personal-banking/cards/credit-cards/pvr-kotak-credit-card.html'),
        ('RBL IndianOil XtraPremium', 'Fuel Points', 'https://www.rblbank.com/product/credit-cards/indianoil-rbl-bank-xtra-credit-card'),
        ('Federal Scapia', 'Scapia Coins', 'https://www.federalbank.co.in/scapia-credit-card'),
        ('Equitas Selfe', 'Equitas Rewards', 'https://www.equitasbank.com/selfe-credit-card')
    ]
    cursor.executemany("INSERT INTO card_metadata (card_name, program, reward_link) VALUES (?, ?, ?)", cards_meta)
    
    cursor.execute("SELECT card_name, meta_id FROM card_metadata")
    meta_map = {name: id for name, id in cursor.fetchall()}
    
    # Assign cards to Admin's Portfolio: user_id, meta_id, balance, spend_unit
    user_cards_data = [
        (admin_id, meta_map['SBI Elite'], 10000, 100),
        (admin_id, meta_map['BOB Eterna'], 5000, 100),
        (admin_id, meta_map['HDFC Diners Black Privilege'], 25000, 150),
        (admin_id, meta_map['HDFC Tata Neu'], 3000, 100),
        (admin_id, meta_map['HDFC Swiggy'], 1500, 100),
        (admin_id, meta_map['Amex Platinum Travel'], 40000, 50),
        (admin_id, meta_map['HSBC Platinum'], 8000, 150),
        (admin_id, meta_map['IDFC First Bank'], 12000, 100),
        (admin_id, meta_map['ICICI Coral'], 4000, 100),
        (admin_id, meta_map['ICICI Sapphiro'], 18000, 100),
        (admin_id, meta_map['ICICI Rupay'], 2000, 100),
        (admin_id, meta_map['Adani One ICICI'], 5000, 100),
        (admin_id, meta_map['ICICI MakeMyTrip'], 3500, 200),
        (admin_id, meta_map['IndusInd Indulge'], 60000, 100),
        (admin_id, meta_map['Yes Bank Reserv'], 15000, 200),
        (admin_id, meta_map['Kotak Bank PVR'], 2, 100),
        (admin_id, meta_map['RBL IndianOil XtraPremium'], 1200, 100),
        (admin_id, meta_map['Federal Scapia'], 8000, 100),
        (admin_id, meta_map['Equitas Selfe'], 2500, 100)
    ]
    cursor.executemany("INSERT INTO user_cards (user_id, meta_id, current_balance, spend_unit) VALUES (?, ?, ?, ?)", user_cards_data)
    
    card_map = meta_map
    
    # Insert Multipliers
    multipliers_data = [
        (card_map['SBI Elite'], 'dining', 10),
        (card_map['SBI Elite'], 'departmental_stores', 10),
        (card_map['SBI Elite'], 'catch_all', 2),
        
        (card_map['BOB Eterna'], 'travel', 15),
        (card_map['BOB Eterna'], 'dining', 15),
        (card_map['BOB Eterna'], 'online_shopping', 15),
        (card_map['BOB Eterna'], 'catch_all', 3),
        
        (card_map['HDFC Diners Black Privilege'], 'swiggy', 10),
        (card_map['HDFC Diners Black Privilege'], 'zomato', 10),
        (card_map['HDFC Diners Black Privilege'], 'catch_all', 4),
        
        (card_map['HDFC Tata Neu'], 'tata_brands', 10),
        (card_map['HDFC Tata Neu'], 'catch_all', 1.5),
        
        (card_map['HDFC Swiggy'], 'swiggy', 10),
        (card_map['HDFC Swiggy'], 'online_shopping', 5),
        (card_map['HDFC Swiggy'], 'catch_all', 1),
        
        (card_map['Amex Platinum Travel'], 'catch_all', 1),
        
        (card_map['HSBC Platinum'], 'dining', 5),
        (card_map['HSBC Platinum'], 'catch_all', 2),
        
        (card_map['IDFC First Bank'], 'online_shopping', 6),
        (card_map['IDFC First Bank'], 'catch_all', 3),
        
        (card_map['ICICI Coral'], 'dining', 4),
        (card_map['ICICI Coral'], 'catch_all', 2),
        
        (card_map['ICICI Sapphiro'], 'international', 4),
        (card_map['ICICI Sapphiro'], 'catch_all', 2),
        
        (card_map['ICICI Rupay'], 'upi', 2),
        (card_map['ICICI Rupay'], 'catch_all', 1),
        
        (card_map['Adani One ICICI'], 'adani_ecosystem', 7),
        (card_map['Adani One ICICI'], 'catch_all', 1.5),
        
        (card_map['ICICI MakeMyTrip'], 'mmt_bookings', 3),
        (card_map['ICICI MakeMyTrip'], 'catch_all', 1.25),
        
        (card_map['IndusInd Indulge'], 'dining', 3),
        (card_map['IndusInd Indulge'], 'catch_all', 1.5),
        
        (card_map['Yes Bank Reserv'], 'online_shopping', 6),
        (card_map['Yes Bank Reserv'], 'catch_all', 3),
        
        (card_map['Kotak Bank PVR'], 'catch_all', 1),
        
        (card_map['RBL IndianOil XtraPremium'], 'fuel', 10),
        (card_map['RBL IndianOil XtraPremium'], 'catch_all', 1),
        
        (card_map['Federal Scapia'], 'travel', 4),
        (card_map['Federal Scapia'], 'catch_all', 2),
        
        (card_map['Equitas Selfe'], 'dining', 2),
        (card_map['Equitas Selfe'], 'catch_all', 1)
    ]
    cursor.executemany("INSERT INTO multipliers (meta_id, category, multiplier) VALUES (?, ?, ?)", multipliers_data)
    
    # Insert Transfer Partners
    transfer_partners_data = [
        ('Amex MR (India)', 'Taj Hotels', '2:1', 0.50),
        ('Amex MR (India)', 'Marriott Bonvoy', '1:1', 0.50),
        ('Amex MR (India)', 'Club Vistara', '3:1', 0.25),
        ('Amex MR (India)', 'Taj Vouchers', '2 Pts = ₹1', 0.50),
        ('HDFC Reward Points', 'InterMiles', '1:1', 0.30),
        ('HDFC Reward Points', 'KrisFlyer', '1:1', 1.50),
        ('HDFC Reward Points', 'Accor Live Limitless', '1:1', 1.80),
        ('HDFC Reward Points', 'SmartBuy Flights', '2 Pts = ₹1', 0.50),
        ('SBI Rewardz', 'Club Vistara', '1:1', 0.80),
        ('SBI Rewardz', 'Yatra/Cleartrip Vouchers', '4 Pts = ₹1', 0.25),
        ('Edge Rewards', 'KrisFlyer', '5:4', 1.20),
        ('Edge Rewards', 'Club Vistara', '5:4', 0.80),
        ('Edge Rewards', 'Marriott Bonvoy', '2:1', 0.50),
        ('Citibank PremierMiles', 'Flying Blue', '1:1', 1.00),
        ('Citibank PremierMiles', 'Club Vistara', '1:1', 0.80),
        ('NeuCoins', 'Tata Neu App Flights/Groceries', '1 Pt = ₹1', 1.00),
        ('HSBC Rewards', 'Accor Live Limitless', '2:1', 0.90),
        ('HSBC Rewards', 'Singapore Krisflyer', '2:1', 0.75),
        ('HSBC Rewards', 'Statement Credit', '5 Pts = ₹1', 0.20),
        ('Yes Rewards', 'Rewardz Flight Bookings', '4 Pts = ₹1', 0.25),
        ('Yes Rewards', 'Air India Maharaja', '10:1', 0.10),
        ('IndusInd Rewards', 'Club Vistara', '1:1', 0.80),
        ('IndusInd Rewards', 'Cash Credit (Indulge)', '1 Pt = ₹1', 1.00),
        ('Adani Rewardz', 'Adani One Flights/Duty-Free', '4 Pts = ₹1', 0.25),
        ('MyCash', 'MakeMyTrip Bookings', '1 Pt = ₹1', 1.00),
        ('Scapia Coins', 'Scapia App Flights', '5 Pts = ₹1', 0.20),
        ('Fuel Points', 'IndianOil Fuel Outlets', '4 Pts = ₹1', 0.25),
        ('PVR Tickets', 'PVR Cinemas Box Office', '1 Ticket', 0.50),
        ('Swiggy Cashback', 'Swiggy App Credit', '1 Pt = ₹1', 1.00),
        ('IDFC Rewards', 'Pay with Points', '4 Pts = ₹1', 0.25),
        ('ICICI Rewards', 'Amazon Pay Vouchers', '4 Pts = ₹1', 0.25),
        ('BOB Rewardz', 'Statement Credit', '4 Pts = ₹1', 0.25),
        ('Equitas Rewards', 'Statement Credit', '5 Pts = ₹1', 0.20),
        ('Cashback', 'Statement Credit', '1 Pt = ₹1', 1.00)
    ]
    cursor.executemany("INSERT INTO transfer_partners (source_program, target_partner, transfer_ratio, est_value_cpp) VALUES (?, ?, ?, ?)", transfer_partners_data)
    
    conn.commit()
    print("Database initialized and seeded with Indian market baseline data and URLs.")

if __name__ == '__main__':
    # Wipe the existing db if it exists
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()
