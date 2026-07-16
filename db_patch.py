import sys
from database import get_db_connection

def patch_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            print("Adding security_question column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS security_question TEXT")
            
            print("Adding security_answer column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS security_answer TEXT")
            
            conn.commit()
            print("Database patched successfully!")
    except Exception as e:
        print(f"Error patching database: {e}")

if __name__ == '__main__':
    patch_db()
