import sqlite3

def check_columns():
    conn = sqlite3.connect('anime.db')
    cursor = conn.cursor()
    
    # Check anime table
    cursor.execute("PRAGMA table_info(anime)")
    anime_columns = cursor.fetchall()
    print("Anime table columns:")
    for i, col in enumerate(anime_columns):
        print(f"  {i}: {col[1]} ({col[2]})")
    
    # Check anime_detail table
    cursor.execute("PRAGMA table_info(anime_detail)")
    detail_columns = cursor.fetchall()
    print("\nAnime_detail table columns:")
    for i, col in enumerate(detail_columns):
        print(f"  {i}: {col[1]} ({col[2]})")
    
    # Find poster_url indices
    anime_poster_idx = None
    detail_poster_idx = None
    
    for i, col in enumerate(anime_columns):
        if col[1] == 'poster_url':
            anime_poster_idx = i
            break
    
    for i, col in enumerate(detail_columns):
        if col[1] == 'poster_url':
            detail_poster_idx = i
            break
    
    print(f"\nPoster URL indices:")
    print(f"  anime.poster_url: index {anime_poster_idx}")
    print(f"  detail.poster_url: index {detail_poster_idx}")
    
    conn.close()

if __name__ == "__main__":
    check_columns() 