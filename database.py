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
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                card_name TEXT,
                program TEXT,
                current_balance INTEGER,
                spend_unit INTEGER,
                reward_link TEXT,
                UNIQUE(user_id, card_name),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multipliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER,
                category TEXT,
                multiplier REAL,
                FOREIGN KEY (card_id) REFERENCES cards (card_id) ON DELETE CASCADE
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
        
        cursor.execute("SELECT COUNT(*) FROM cards")
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
    
    # Insert Cards: user_id, name, program, balance, spend_unit, reward_link
    cards_data = [
        (admin_id, 'SBI Elite', 'SBI Rewardz', 10000, 100, 'https://www.sbicard.com/en/personal/rewards.page'),
        (admin_id, 'BOB Eterna', 'BOB Rewardz', 5000, 100, 'https://www.bobcard.co.in/credit-card-types/eterna'),
        (admin_id, 'HDFC Diners Black Privilege', 'HDFC Reward Points', 25000, 150, 'https://offers.smartbuy.hdfcbank.com/diners'),
        (admin_id, 'HDFC Tata Neu', 'NeuCoins', 3000, 100, 'https://www.tataneu.com/neucoins'),
        (admin_id, 'HDFC Swiggy', 'Swiggy Cashback', 1500, 100, 'https://www.hdfcbank.com/personal/pay/cards/credit-cards/swiggy-hdfc-bank-credit-card'),
        (admin_id, 'Amex Platinum Travel', 'Amex MR (India)', 40000, 50, 'https://www.americanexpress.com/en-in/rewards/membership-rewards/'),
        (admin_id, 'HSBC Platinum', 'HSBC Rewards', 8000, 150, 'https://www.hsbc.co.in/credit-cards/rewards/'),
        (admin_id, 'IDFC First Bank', 'IDFC Rewards', 12000, 100, 'https://www.idfcfirstbank.com/credit-card/rewards'),
        (admin_id, 'ICICI Coral', 'ICICI Rewards', 4000, 100, 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/coral-card/index.page'),
        (admin_id, 'ICICI Sapphiro', 'ICICI Rewards', 18000, 100, 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/sapphiro/index.page'),
        (admin_id, 'ICICI Rupay', 'ICICI Rewards', 2000, 100, 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/rupay-credit-card.page'),
        (admin_id, 'Adani One ICICI', 'Adani Rewardz', 5000, 100, 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/adani-one.page'),
        (admin_id, 'ICICI MakeMyTrip', 'MyCash', 3500, 200, 'https://www.icicibank.com/Personal-Banking/cards/Consumer-Cards/Credit-Card/makemytrip.page'),
        (admin_id, 'IndusInd Indulge', 'IndusInd Rewards', 60000, 100, 'https://www.indusind.com/in/en/personal/cards/credit-card/indulge-credit-card.html'),
        (admin_id, 'Yes Bank Reserv', 'Yes Rewards', 15000, 200, 'https://www.yesbank.in/personal-banking/cards/credit-card/yes-first-exclusive'),
        (admin_id, 'Kotak Bank PVR', 'PVR Tickets', 2, 100, 'https://www.kotak.com/en/personal-banking/cards/credit-cards/pvr-kotak-credit-card.html'),
        (admin_id, 'RBL IndianOil XtraPremium', 'Fuel Points', 1200, 100, 'https://www.rblbank.com/product/credit-cards/indianoil-rbl-bank-xtra-credit-card'),
        (admin_id, 'Federal Scapia', 'Scapia Coins', 8000, 100, 'https://www.federalbank.co.in/scapia-credit-card'),
        (admin_id, 'Equitas Selfe', 'Equitas Rewards', 2500, 100, 'https://www.equitasbank.com/selfe-credit-card')
    ]
    cursor.executemany("INSERT INTO cards (user_id, card_name, program, current_balance, spend_unit, reward_link) VALUES (?, ?, ?, ?, ?, ?)", cards_data)
    
    cursor.execute("SELECT card_id, card_name FROM cards")
    card_map = {name: id for id, name in cursor.fetchall()}
    
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
    cursor.executemany("INSERT INTO multipliers (card_id, category, multiplier) VALUES (?, ?, ?)", multipliers_data)
    
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
