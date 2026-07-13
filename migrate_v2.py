import sqlite3

def run_migration():
    conn = sqlite3.connect('savepoints.db')
    cursor = conn.cursor()
    
    # 1. Create new tables
    cursor.execute('''
        CREATE TABLE card_metadata (
            meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT UNIQUE,
            program TEXT,
            reward_link TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE user_cards (
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
        CREATE TABLE card_requests (
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
        CREATE TABLE multipliers_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER,
            category TEXT,
            multiplier REAL,
            FOREIGN KEY(meta_id) REFERENCES card_metadata(meta_id) ON DELETE CASCADE
        )
    ''')
    
    # 2. Extract unique cards into card_metadata
    cursor.execute("SELECT DISTINCT card_name, program, reward_link FROM cards")
    unique_cards = cursor.fetchall()
    
    cursor.executemany(
        "INSERT INTO card_metadata (card_name, program, reward_link) VALUES (?, ?, ?)",
        unique_cards
    )
    
    # Build mapping from card_name to meta_id
    cursor.execute("SELECT card_name, meta_id FROM card_metadata")
    meta_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 3. Migrate user portfolios into user_cards
    cursor.execute("SELECT card_id, user_id, card_name, current_balance, spend_unit FROM cards")
    old_cards = cursor.fetchall()
    
    user_cards_data = []
    old_card_id_to_meta_id = {}
    for row in old_cards:
        old_card_id = row[0]
        u_id = row[1]
        c_name = row[2]
        bal = row[3]
        spend = row[4]
        
        m_id = meta_map[c_name]
        old_card_id_to_meta_id[old_card_id] = m_id
        user_cards_data.append((u_id, m_id, bal, spend))
        
    cursor.executemany(
        "INSERT INTO user_cards (user_id, meta_id, current_balance, spend_unit) VALUES (?, ?, ?, ?)",
        user_cards_data
    )
    
    # 4. Migrate multipliers
    cursor.execute("SELECT card_id, category, multiplier FROM multipliers")
    old_mults = cursor.fetchall()
    
    mult_set = set()
    for row in old_mults:
        old_card_id = row[0]
        cat = row[1]
        val = row[2]
        m_id = old_card_id_to_meta_id[old_card_id]
        mult_set.add((m_id, cat, val))
        
    cursor.executemany(
        "INSERT INTO multipliers_v2 (meta_id, category, multiplier) VALUES (?, ?, ?)",
        list(mult_set)
    )
    
    # 5. Drop old tables and rename new ones
    cursor.execute("DROP TABLE multipliers")
    cursor.execute("ALTER TABLE multipliers_v2 RENAME TO multipliers")
    cursor.execute("DROP TABLE cards")
    
    conn.commit()
    conn.close()
    print("Migration V2 Complete: Global catalog and user cards created successfully.")

if __name__ == '__main__':
    run_migration()
