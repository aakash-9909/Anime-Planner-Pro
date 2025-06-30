import sqlite3

def check_database():
    conn = sqlite3.connect('anime.db')
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(anime)")
    columns = cursor.fetchall()
    
    print("Anime table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Check if poster_url exists
    poster_url_exists = any(col[1] == 'poster_url' for col in columns)
    print(f"\nposter_url column exists: {poster_url_exists}")
    
    # Check if background_url exists
    background_url_exists = any(col[1] == 'background_url' for col in columns)
    print(f"background_url column exists: {background_url_exists}")
    
    # Check if user_id exists
    user_id_exists = any(col[1] == 'user_id' for col in columns)
    print(f"user_id column exists: {user_id_exists}")
    
    conn.close()

if __name__ == "__main__":
    check_database() 