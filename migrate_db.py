import sqlite3
import hashlib

def hash_password(password):
    # Using SHA256 + salt for secure storage without external dependencies
    salt = "savepoints_salt_"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def migrate():
    conn = sqlite3.connect('savepoints.db')
    cursor = conn.cursor()
    
    # Disable foreign keys temporarily for migration
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # 1. Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            email TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # 2. Insert Admin Account
    admin_username = 'jalanhimanshu'
    admin_password = hash_password('password@him')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, email, role)
        VALUES (?, ?, ?, ?)
    ''', (admin_username, admin_password, 'admin@savepoints.local', 'admin'))
    
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (admin_username,))
    admin_id = cursor.fetchone()[0]
    
    # 3. Recreate Cards Table with user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_cards (
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
    
    # 4. Migrate Data
    # Check if old cards table has user_id already
    cursor.execute("PRAGMA table_info(cards)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print("Migrating cards to new schema...")
        cursor.execute('''
            INSERT INTO new_cards (card_id, user_id, card_name, program, current_balance, spend_unit, reward_link)
            SELECT card_id, ?, card_name, program, current_balance, spend_unit, reward_link
            FROM cards
        ''', (admin_id,))
        
        # Drop old and rename new
        cursor.execute("DROP TABLE cards")
        cursor.execute("ALTER TABLE new_cards RENAME TO cards")
        print("Migration complete. All existing cards assigned to admin account.")
    else:
        print("Schema already up to date. Dropping temp table.")
        cursor.execute("DROP TABLE IF EXISTS new_cards")

    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.close()

if __name__ == '__main__':
    migrate()
