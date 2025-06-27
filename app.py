from flask import Flask, render_template, request, redirect, flash, session, url_for, Response, send_file
from flask_session import Session
import sqlite3
import os
from datetime import datetime
import csv
import io
import json
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import random
import zipfile

# Configure application
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# managing login and stuff(login requires)
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Login required.")
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

# DB connection helper for SQLite
def get_db():
    return sqlite3.connect("anime.db")

# Helper function to convert SQLite rows to dictionaries
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Helper function to get database with dictionary factory
def get_db_dict():
    conn = sqlite3.connect("anime.db")
    conn.row_factory = dict_factory
    return conn

# Custom Jinja filter
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%b %Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

# Create tables with SQLite syntax
def init_db():
    conn = get_db()
    db = conn.cursor()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            rating REAL,
            thoughts TEXT,
            date TEXT,
            sequel TEXT,
            details_url TEXT,
            background_url TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS sequel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS anime_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            extra_notes TEXT,
            images TEXT,
            story_rating REAL,
            visual_rating REAL,
            sound_rating REAL,
            lessons TEXT,
            rating_note TEXT,
            favorite_episodes TEXT,
            poster_url TEXT,
            background_url TEXT,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS anime_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER,
            episode_number INTEGER,
            episode_note TEXT,
            episode_images TEXT,
            rating_overall REAL,
            rating_animation REAL,
            rating_story REAL,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS anime_husbandos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            name TEXT,
            image TEXT,
            note TEXT,
            starred INTEGER DEFAULT 0,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS anime_waifus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            name TEXT,
            image TEXT,
            note TEXT,
            starred INTEGER DEFAULT 0,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    db.close()
    conn.close()

@app.route("/")
def index():
    # Romcom/funny quotes (no explicit or Naruto quotes)
    quotes = [
        {"text": "I have no interest in ordinary humans. If there are any aliens, time travelers, or espers here, come join me.", "author": "Haruhi Suzumiya", "anime": "The Melancholy of Haruhi Suzumiya"},
        {"text": "I am not a tsundere!", "author": "Taiga Aisaka", "anime": "Toradora!"},
        {"text": "Love is like a hurricane!", "author": "Rikka Takanashi", "anime": "Chuunibyou demo Koi ga Shitai!"},
        {"text": "I'm not short! I'm fun-sized!", "author": "Shinobu Oshino", "anime": "Monogatari Series"},
        {"text": "I am... just a passing-through ordinary house husband.", "author": "Tatsu", "anime": "The Way of the Househusband"},
        {"text": "I want to eat your pancreas!", "author": "Sakura Yamauchi", "anime": "I Want to Eat Your Pancreas"},
        {"text": "My body is made of 100% sugar.", "author": "Chiyo Sakura", "anime": "Monthly Girls' Nozaki-kun"},
        {"text": "I am the bone of my bread.", "author": "Kaguya Shinomiya", "anime": "Kaguya-sama: Love is War"},
        {"text": "If you have time to fantasize about a beautiful end, then just live beautifully 'til the end.", "author": "Sakata Gintoki", "anime": "Gintama"}
    ]
    quote = random.choice(quotes)

    # Random image gallery from uploads
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    all_images = [f for f in os.listdir(uploads_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    gallery_images = random.sample(all_images, min(6, len(all_images))) if all_images else []
    gallery_images = [f"uploads/{img}" for img in gallery_images]

    return render_template("index.html", quote=quote, gallery_images=gallery_images)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        title = request.form.get("title")
        rating = request.form.get("rating") or 0
        rating = float(rating) if rating else 0
        thoughts = request.form.get("thoughts")
        date = request.form.get("date")
        sequel = request.form.get("sequel")
        background_url = request.form.get("background_url")
        no_date = request.form.get("no_date")

        if not title:
            flash("Please enter a title")
            return redirect("/add")

        if no_date:
            date = None
        elif not date:
            date = datetime.today().strftime('%Y-%m-%d')

        conn = get_db()
        db = conn.cursor()
        user_id = session.get("user_id")

        poster_file = request.files.get("poster_upload") if "poster_upload" in request.files else None
        poster_url = None
        details_url = None  # Always define details_url
        if poster_file and poster_file.filename:
            filename = secure_filename(poster_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            poster_file.save(save_path)
            poster_url = f"uploads/{filename}"
            details_url = poster_url
        # If not uploaded, check for details_url in form (optional)
        if not details_url:
            details_url = request.form.get("details_url") or None

        # --- Fix background image upload ---
        background_file = request.files.get("background_upload") if "background_upload" in request.files else None
        if background_file and background_file.filename:
            filename = secure_filename(background_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            background_file.save(save_path)
            background_url = f"uploads/{filename}"

        db.execute("""
            INSERT INTO anime (title, rating, thoughts, date, sequel, details_url, background_url, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, rating, thoughts, date, sequel, details_url, background_url, user_id))
        anime_id = db.lastrowid

        # --- Remove automatic anime_detail creation ---
        # Only create anime_detail when user adds details in edit_detail

        if sequel:
            db.execute("INSERT INTO sequel (name) VALUES (?)", (sequel,))

        conn.commit()
        db.close()
        conn.close()

        flash("Anime added successfully!")
        return redirect("/preview")
    
    # GET method - show the form
    conn = get_db()
    db = conn.cursor()
    sort_by_rating = request.args.get("sort_by_rating")
    user_id = session.get("user_id")

    db.execute("UPDATE anime SET rating = 0 WHERE rating IS NULL AND user_id = ?", (user_id,))
    conn.commit()

    if sort_by_rating:
        db.execute("SELECT title FROM anime WHERE rating IS NOT NULL AND user_id = ? ORDER BY rating DESC", (user_id,))
    else:
        db.execute("SELECT DISTINCT title FROM anime WHERE user_id = ? ORDER BY title", (user_id,))

    sequel_list = [row[0] for row in db.fetchall()]
    db.close()
    conn.close()

    return render_template("add.html", sequel_list=sequel_list, sort_active=bool(sort_by_rating))

@app.route("/preview")
@login_required
def preview():
    sort_by_rating = request.args.get("sort_by_rating")
    conn = get_db_dict()
    db = conn.cursor()
    user_id = session.get("user_id")
    
    order_clause = "ORDER BY a.rating DESC" if sort_by_rating else "ORDER BY a.id DESC"
    
    db.execute(f"""
        SELECT a.*, d.poster_url
        FROM anime a
        LEFT JOIN anime_detail d ON a.id = d.anime_id
        WHERE a.user_id = ?
        {order_clause}
    """, (user_id,))
    anime_list = db.fetchall()

    # Get anime IDs that have details
    db.execute("SELECT anime_id FROM anime_detail ad JOIN anime a ON ad.anime_id = a.id WHERE a.user_id = ?", (user_id,))
    detail_ids = set(row['anime_id'] for row in db.fetchall())

    db.close()
    conn.close()
    return render_template("preview.html", anime_list=anime_list, detail_ids=detail_ids, sort_active=bool(sort_by_rating))

@app.route("/edit/<int:anime_id>", methods=["GET", "POST"])
@login_required
def edit(anime_id):
    user_id = session.get("user_id")
    
    if request.method == "POST":
        title = request.form.get("title")
        rating = request.form.get("rating")
        thoughts = request.form.get("thoughts")
        date = request.form.get("date")
        sequel = request.form.get("sequel")
        background_url = request.form.get("background_url")
        no_date = request.form.get("no_date")

        if no_date:
            date = None
        elif not date:
            date = datetime.today().strftime('%Y-%m-%d')

        # --- Handle background image upload ---
        background_file = request.files.get("background_upload") if "background_upload" in request.files else None
        if background_file and background_file.filename:
            filename = secure_filename(background_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            background_file.save(save_path)
            background_url = f"uploads/{filename}"
        # If no new file, use the value from the form (could be a URL or a local path)

        conn = get_db()
        db = conn.cursor()
        
        # Update main anime table (without details_url)
        db.execute("""
            UPDATE anime
            SET title = ?, rating = ?, thoughts = ?, date = ?, sequel = ?, background_url = ?
            WHERE id = ? AND user_id = ?
        """, (title, rating, thoughts, date, sequel, background_url, anime_id, user_id))

        if sequel:
            db.execute("INSERT INTO sequel (name) VALUES (?)", (sequel,))

        conn.commit()
        db.close()
        conn.close()
        flash("Anime updated successfully!")
        return redirect("/preview")

    # Use dictionary factory for GET to make template access consistent
    conn_dict = get_db_dict()
    db_dict = conn_dict.cursor()
    db_dict.execute("SELECT * FROM anime WHERE id = ? AND user_id = ?", (anime_id, user_id))
    anime = db_dict.fetchone()
    
    if not anime:
        db_dict.close()
        conn_dict.close()
        flash("Anime not found or access denied.")
        return redirect("/preview")
    
    # Get sequel list for dropdown
    conn = get_db()
    db = conn.cursor()
    db.execute("SELECT DISTINCT title FROM anime WHERE user_id = ? ORDER BY title", (user_id,))
    sequel_list = [row[0] for row in db.fetchall()]
    
    db.close()
    conn.close()
    db_dict.close()
    conn_dict.close()

    return render_template("edit.html", anime=anime, sequel_list=sequel_list)

@app.route("/delete/<int:anime_id>", methods=["POST"])
@login_required
def delete(anime_id):
    conn = get_db()
    db = conn.cursor()
    user_id = session.get("user_id")
    db.execute("DELETE FROM anime WHERE id = ? AND user_id = ?", (anime_id, user_id))
    conn.commit()
    db.close()
    conn.close()
    flash("Anime deleted successfully!")
    return redirect("/preview")

@app.route("/list")
@login_required
def list_view():
    sort_by = request.args.get("sort", "rating")  # default: rating
    order = request.args.get("order", "desc")     # default: descending
    filter_null = request.args.get("filter", "nonull")  # default: filter out NULLs

    # Validate parameters
    if sort_by not in {"date", "rating"}:
        sort_by = "rating"
    if order not in {"asc", "desc"}:
        order = "desc"
    if filter_null not in {"nonull", "all"}:
        filter_null = "nonull"

    sort_column = "rating" if sort_by == "rating" else "date"
    user_id = session.get("user_id")

    # Build SQL dynamically
    base_query = "SELECT id, title, rating, date FROM anime WHERE user_id = ?"
    if filter_null == "nonull":
        base_query += f" AND {sort_column} IS NOT NULL"

    base_query += f" ORDER BY {sort_column} {order.upper()}"

    conn = get_db()
    db = conn.cursor()
    db.execute(base_query, (user_id,))
    anime_list = db.fetchall()
    db.close()
    conn.close()

    return render_template("list.html",
        anime_list=anime_list,
        sort_by=sort_by,
        order=order,
        filter_null=filter_null
    )

@app.template_filter('render_stars')
def render_stars(value):
    try:
        value = float(value)
        full = int(value) // 2
        half = 1 if int(value) % 2 else 0
        return "⭐" * full + ("½" if half else "")
    except:
        return "N/A"
@app.route("/detail/<int:anime_id>")
@login_required
def detail(anime_id):
    conn = get_db()
    db = conn.cursor()
    user_id = session.get("user_id")

    # Fetch main anime data (only for current user)
    db.execute("SELECT * FROM anime WHERE id = ? AND user_id = ?", (anime_id, user_id))
    anime = db.fetchone()

    if not anime:
        db.close()
        conn.close()
        flash("Anime not found or access denied.")
        return redirect("/preview")

    # Fetch detailed info
    db.execute("SELECT * FROM anime_detail WHERE anime_id = ?", (anime_id,))
    detail = db.fetchone()

    # Decode image list
    image_urls = []
    if detail and detail[3]:
        try:
            image_urls = json.loads(detail[3])
            print(f"Debug: Loaded {len(image_urls)} images from database: {image_urls}")
        except Exception as e:
            print(f"Debug: Error parsing images JSON: {e}")
            image_urls = []

    # Fetch and format episodes
    db.execute("""
        SELECT episode_number, episode_note, episode_images, rating_overall, rating_animation, rating_story
        FROM anime_episodes WHERE anime_id = ? ORDER BY episode_number ASC
    """, (anime_id,))

    episode_rows = db.fetchall()
    episodes = []
    for row in episode_rows:
        ep_number, ep_note, ep_images_json, ep_rating_overall, ep_rating_anim, ep_rating_story = row
        try:
            episode_images = json.loads(ep_images_json) if ep_images_json else []
        except:
            episode_images = []
        episodes.append({
            "number": ep_number,
            "note": ep_note,
            "images": episode_images,
            "overall": ep_rating_overall,
            "animation": ep_rating_anim,
            "story": ep_rating_story
        })
    # Fetch waifus
    db.execute("SELECT name, image, note FROM anime_waifus WHERE anime_id = ?", (anime_id,))
    waifus = [{"name": row[0], "image": row[1], "note": row[2]} for row in db.fetchall()]

    # Fetch husbandos
    db.execute("SELECT name, image, note FROM anime_husbandos WHERE anime_id = ?", (anime_id,))
    husbandos = [{"name": row[0], "image": row[1], "note": row[2]} for row in db.fetchall()]

    db.close()
    conn.close()

    return render_template(
    "detail.html",
    anime=anime,
    detail=detail,
    images=image_urls,
    episodes=episodes,
    waifus=waifus,
    husbandos=husbandos
)

@app.route("/edit_detail/<int:anime_id>", methods=["GET", "POST"])
@login_required
def edit_detail(anime_id):
    conn = get_db()
    db = conn.cursor()
    user_id = session.get("user_id")

    db.execute("SELECT * FROM anime WHERE id = ? AND user_id = ?", (anime_id, user_id))
    anime = db.fetchone()
    if not anime:
        flash("Anime not found or access denied.")
        return redirect("/preview")

    if request.method == "POST":
        # === Fetch detail data ===
        extra_notes = request.form.get("extra_notes")
        lessons = request.form.get("lessons")
        favorite_episodes = request.form.get("favorite_episodes")
        poster_url = request.form.get("poster_url")
        background_url = request.form.get("background_url")  # ✅ NEW
        story_rating = request.form.get("story_rating")
        visual_rating = request.form.get("visual_rating")
        sound_rating = request.form.get("sound_rating")
        rating_note = request.form.get("rating_note")
        images_raw = request.form.get("images", "")

        # Convert empty strings to None for numeric fields
        story_rating = float(story_rating) if story_rating and story_rating.strip() else None
        visual_rating = float(visual_rating) if visual_rating and visual_rating.strip() else None
        sound_rating = float(sound_rating) if sound_rating and sound_rating.strip() else None

        # === Handle images ===
        image_urls = [url.strip() for url in images_raw.split(",") if url.strip()]
        uploaded_files = request.files.getlist("image_uploads")
        uploaded_paths = []
        
        print(f"Debug: Found {len(uploaded_files)} uploaded files")
        
        for file in uploaded_files:
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    print(f"Debug: Saving file {filename} to {save_path}")
                    file.save(save_path)
                    uploaded_paths.append(f"uploads/{filename}")
                    print(f"Debug: Successfully saved {filename}")
                except Exception as e:
                    print(f"Debug: Error saving file {file.filename}: {e}")
                    flash(f"Error uploading {file.filename}: {str(e)}")
        
        all_images = image_urls + uploaded_paths
        image_json = json.dumps(all_images)
        print(f"Debug: Final image list: {all_images}")

        # === Handle poster and background uploads ===
        poster_file = request.files.get("poster_upload")
        if poster_file and poster_file.filename:
            filename = secure_filename(poster_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            poster_file.save(save_path)
            poster_url = f"uploads/{filename}"

        background_file = request.files.get("background_upload") if "background_upload" in request.files else None
        if background_file and background_file.filename:
            filename = secure_filename(background_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            background_file.save(save_path)
            background_url = f"uploads/{filename}"

        try:
            # === Update or insert anime_detail ===
            db.execute("SELECT id FROM anime_detail WHERE anime_id = ?", (anime_id,))
            exists = db.fetchone()
            if exists:
                db.execute("""
                    UPDATE anime_detail
                    SET extra_notes = ?, lessons = ?, favorite_episodes = ?, poster_url = ?, background_url = ?,
                        images = ?, story_rating = ?, visual_rating = ?, sound_rating = ?, rating_note = ?
                    WHERE anime_id = ?
                """, (
                    extra_notes, lessons, favorite_episodes, poster_url, background_url,
                    image_json, story_rating, visual_rating, sound_rating, rating_note,
                    anime_id
                ))
            else:
                # Only insert if at least one detail field is provided
                if any([extra_notes, lessons, favorite_episodes, poster_url, background_url, image_json, story_rating, visual_rating, sound_rating, rating_note]):
                    db.execute("""
                        INSERT INTO anime_detail (
                            anime_id, extra_notes, lessons, favorite_episodes, poster_url, background_url,
                            images, story_rating, visual_rating, sound_rating, rating_note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        anime_id, extra_notes, lessons, favorite_episodes, poster_url, background_url,
                        image_json, story_rating, visual_rating, sound_rating, rating_note
                    ))
        except Exception as e:
            print(f"Debug: Database error: {e}")
            flash(f"Database error: {str(e)}")
            return redirect(url_for("edit_detail", anime_id=anime_id))

        # === Update or delete existing episodes ===
        existing_ids = request.form.getlist("existing_episode_ids")
        for eid in existing_ids:
            delete_flag = request.form.get(f"delete_episode_{eid}")
            if delete_flag:
                db.execute("DELETE FROM anime_episodes WHERE id = ?", (eid,))
            else:
                ep_num = request.form.get(f"episode_number_{eid}")
                ep_note = request.form.get(f"episode_note_{eid}")
                ep_images_raw = request.form.get(f"episode_images_{eid}")
                ep_images_list = [url.strip() for url in ep_images_raw.split(",") if url.strip()]
                # Handle episode image upload
                ep_files = request.files.getlist(f"episode_image_upload_{eid}")
                for file in ep_files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        file.save(save_path)
                        ep_images_list.append(f"uploads/{filename}")
                ep_images = json.dumps(ep_images_list)
                ep_overall = float(request.form.get(f"episode_overall_{eid}")) if request.form.get(f"episode_overall_{eid}") and request.form.get(f"episode_overall_{eid}").strip() else None
                ep_animation = float(request.form.get(f"episode_animation_{eid}")) if request.form.get(f"episode_animation_{eid}") and request.form.get(f"episode_animation_{eid}").strip() else None
                ep_story = float(request.form.get(f"episode_story_{eid}")) if request.form.get(f"episode_story_{eid}") and request.form.get(f"episode_story_{eid}").strip() else None

                db.execute("""
                    UPDATE anime_episodes
                    SET episode_number = ?, episode_note = ?, episode_images = ?,
                        rating_overall = ?, rating_animation = ?, rating_story = ?
                    WHERE id = ?
                """, (ep_num, ep_note, ep_images, ep_overall, ep_animation, ep_story, eid))

        # === Insert new episodes ===
        new_episode_numbers = request.form.getlist("episode_number")
        new_episode_notes = request.form.getlist("episode_note")
        new_episode_images = request.form.getlist("episode_images")
        new_episode_overalls = request.form.getlist("episode_overall")
        new_episode_animations = request.form.getlist("episode_animation")
        new_episode_stories = request.form.getlist("episode_story")
        # For new episodes, handle multiple files per episode
        new_episode_files = request.files.getlist("episode_image_upload")
        file_idx = 0
        for i in range(len(new_episode_numbers)):
            try:
                ep_num = int(new_episode_numbers[i])
                ep_note = new_episode_notes[i]
                ep_images_list = [url.strip() for url in new_episode_images[i].split(",") if url.strip()]
                # Handle episode image upload for new episodes
                # Try to match files to episodes by order
                episode_files = []
                while file_idx < len(new_episode_files) and new_episode_files[file_idx] and new_episode_files[file_idx].filename:
                    filename = secure_filename(new_episode_files[file_idx].filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    new_episode_files[file_idx].save(save_path)
                    ep_images_list.append(f"uploads/{filename}")
                    file_idx += 1
                    # Only one file per episode unless user selects multiple for one episode
                    break
                ep_images = json.dumps(ep_images_list)
                ep_overall = float(new_episode_overalls[i]) if new_episode_overalls[i] and new_episode_overalls[i].strip() else None
                ep_animation = float(new_episode_animations[i]) if new_episode_animations[i] and new_episode_animations[i].strip() else None
                ep_story = float(new_episode_stories[i]) if new_episode_stories[i] and new_episode_stories[i].strip() else None

                db.execute("""
                    INSERT INTO anime_episodes (
                        anime_id, episode_number, episode_note, episode_images,
                        rating_overall, rating_animation, rating_story
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    anime_id, ep_num, ep_note, ep_images, ep_overall, ep_animation, ep_story))
            except Exception as e:
                print(f"Skipping new episode {i}: {e}")

        # === Update or delete existing waifus ===
        existing_waifu_ids = request.form.getlist("existing_waifu_ids")
        for wid in existing_waifu_ids:
            delete_flag = request.form.get(f"delete_waifu_{wid}")
            if delete_flag:
                db.execute("DELETE FROM anime_waifus WHERE id = ?", (wid,))
            else:
                name = request.form.get(f"waifu_name_{wid}")
                image = request.form.get(f"waifu_image_{wid}")
                # Handle waifu image upload
                waifu_file = request.files.get(f"waifu_image_upload_{wid}")
                if waifu_file and waifu_file.filename:
                    filename = secure_filename(waifu_file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    waifu_file.save(save_path)
                    image = f"uploads/{filename}"
                note = request.form.get(f"waifu_note_{wid}")
                db.execute("""
                    UPDATE anime_waifus
                    SET name = ?, image = ?, note = ?
                    WHERE id = ?
                """, (name, image, note, wid))

        # === Insert new waifus ===
        new_waifu_names = request.form.getlist("waifu_name")
        new_waifu_images = request.form.getlist("waifu_image")
        new_waifu_notes = request.form.getlist("waifu_note")
        waifu_files = request.files.getlist("waifu_image_upload")
        for i in range(len(new_waifu_names)):
            name = new_waifu_names[i]
            image = new_waifu_images[i]
            note = new_waifu_notes[i]
            # Handle waifu image upload
            if waifu_files and len(waifu_files) > i and waifu_files[i] and waifu_files[i].filename:
                filename = secure_filename(waifu_files[i].filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                waifu_files[i].save(save_path)
                image = f"uploads/{filename}"
            if name:
                db.execute("""
                    INSERT INTO anime_waifus (anime_id, name, image, note)
                    VALUES (?, ?, ?, ?)
                """, (anime_id, name, image, note))

        # === Update or delete existing husbandos ===
        existing_husbando_ids = request.form.getlist("existing_husbando_ids")
        for hid in existing_husbando_ids:
            delete_flag = request.form.get(f"delete_husbando_{hid}")
            if delete_flag:
                db.execute("DELETE FROM anime_husbandos WHERE id = ?", (hid,))
            else:
                name = request.form.get(f"husbando_name_{hid}")
                image = request.form.get(f"husbando_image_{hid}")
                # Handle husbando image upload
                husbando_file = request.files.get(f"husbando_image_upload_{hid}")
                if husbando_file and husbando_file.filename:
                    filename = secure_filename(husbando_file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    husbando_file.save(save_path)
                    image = f"uploads/{filename}"
                note = request.form.get(f"husbando_note_{hid}")
                db.execute("""
                    UPDATE anime_husbandos
                    SET name = ?, image = ?, note = ?
                    WHERE id = ?
                """, (name, image, note, hid))

        # === Insert new husbandos ===
        new_husbando_names = request.form.getlist("husbando_name")
        new_husbando_images = request.form.getlist("husbando_image")
        new_husbando_notes = request.form.getlist("husbando_note")
        husbando_files = request.files.getlist("husbando_image_upload")
        for i in range(len(new_husbando_names)):
            name = new_husbando_names[i]
            image = new_husbando_images[i]
            note = new_husbando_notes[i]
            # Handle husbando image upload
            if husbando_files and len(husbando_files) > i and husbando_files[i] and husbando_files[i].filename:
                filename = secure_filename(husbando_files[i].filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                husbando_files[i].save(save_path)
                image = f"uploads/{filename}"
            if name:
                db.execute("""
                    INSERT INTO anime_husbandos (anime_id, name, image, note)
                    VALUES (?, ?, ?, ?)
                """, (anime_id, name, image, note))

        conn.commit()
        db.close()
        conn.close()
        flash("Details updated successfully!")
        return redirect(url_for("detail", anime_id=anime_id))

    # === GET method ===
    db.execute("SELECT * FROM anime_detail WHERE anime_id = ?", (anime_id,))
    detail = db.fetchone()

    image_list = ""
    if detail and detail[3]:
        try:
            image_list = ", ".join(json.loads(detail[3]))
        except:
            image_list = detail[3]

    db.execute("""
        SELECT id, episode_number, episode_note, episode_images,
                rating_overall, rating_animation, rating_story
        FROM anime_episodes
        WHERE anime_id = ?
        ORDER BY episode_number
    """, (anime_id,))
    rows = db.fetchall()

    existing_episodes = []
    for row in rows:
        ep_id, number, note, img_json, overall, animation, story = row
        try:
            images = json.loads(img_json) if img_json else []
        except:
            images = []
        existing_episodes.append({
            "id": ep_id,
            "number": number,
            "note": note,
            "images": images,
            "overall": overall,
            "animation": animation,
            "story": story
        })

    db.execute("SELECT id, name, image, note FROM anime_waifus WHERE anime_id = ?", (anime_id,))
    existing_waifus = [{"id": row[0], "name": row[1], "image": row[2], "note": row[3]} for row in db.fetchall()]

    db.execute("SELECT id, name, image, note FROM anime_husbandos WHERE anime_id = ?", (anime_id,))
    existing_husbandos = [{"id": row[0], "name": row[1], "image": row[2], "note": row[3]} for row in db.fetchall()]

    db.close()
    conn.close()

    return render_template(
        "edit_detail.html",
        anime=anime,
        detail=detail,
        image_list=image_list,
        existing_episodes=existing_episodes,
        existing_waifus=existing_waifus,
        existing_husbandos=existing_husbandos
    )

@app.route("/list_detail")
@login_required
def list_detail():
    conn = get_db_dict()
    db = conn.cursor()
    user_id = session.get("user_id")

    db.execute("""
        SELECT a.id, a.title, a.rating, a.thoughts,
               d.extra_notes, d.poster_url, d.images
        FROM anime a
        LEFT JOIN anime_detail d ON a.id = d.anime_id
        WHERE a.user_id = ?
        ORDER BY a.id DESC
    """, (user_id,))
    anime_list = db.fetchall()

    # Safely process the 'images' JSON string in Python
    for anime in anime_list:
        images_data = anime.get('images')
        if images_data and isinstance(images_data, str):
            try:
                # Ensure the loaded data is a list
                loaded_images = json.loads(images_data)
                anime['images'] = loaded_images if isinstance(loaded_images, list) else []
            except (json.JSONDecodeError, TypeError):
                anime['images'] = []
        # If it's not a string (e.g., already a list, or None), ensure it's a list
        elif not isinstance(images_data, list):
            anime['images'] = []

    # Get anime IDs that have details
    db.execute("SELECT anime_id FROM anime_detail ad JOIN anime a ON ad.anime_id = a.id WHERE a.user_id = ?", (user_id,))
    detail_ids = set(row['anime_id'] for row in db.fetchall())

    db.close()
    conn.close()
    return render_template("list_detail.html", anime_list=anime_list, detail_ids=detail_ids)

@app.template_filter('loads')
def json_loads_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []

@app.route("/characters", methods=["GET", "POST"])
@login_required
def characters():
    search = request.args.get("search", "").strip()
    query = "%" + search + "%" if search else "%"
    user_id = session.get("user_id")

    conn = get_db()
    db = conn.cursor()

    # Fetch waifus (only from user's anime)
    db.execute("""
        SELECT w.id, w.name, w.image, w.note, w.starred, a.id, a.title
        FROM anime_waifus w
        JOIN anime a ON w.anime_id = a.id
        WHERE w.name LIKE ? AND a.user_id = ?
        ORDER BY w.starred DESC, w.name
    """, (query, user_id))
    waifus = db.fetchall()

    # Fetch husbandos (only from user's anime)
    db.execute("""
        SELECT h.id, h.name, h.image, h.note, h.starred, a.id, a.title
        FROM anime_husbandos h
        JOIN anime a ON h.anime_id = a.id
        WHERE h.name LIKE ? AND a.user_id = ?
        ORDER BY h.starred DESC, h.name
    """, (query, user_id))
    husbandos = db.fetchall()

    db.close()
    conn.close()
    return render_template("characters.html", waifus=waifus, husbandos=husbandos, search=search)

@app.route("/toggle_star/<string:character_type>/<int:char_id>", methods=["POST"])
@login_required
def toggle_star(character_type, char_id):
    if character_type not in ("waifu", "husbando"):
        return "Invalid type", 400

    table = "anime_waifus" if character_type == "waifu" else "anime_husbandos"
    user_id = session.get("user_id")

    conn = get_db()
    db = conn.cursor()
    
    # Only allow toggling stars for characters from user's anime
    db.execute(f"""
        UPDATE {table} 
        SET starred = NOT starred 
        WHERE id = ? AND anime_id IN (SELECT id FROM anime WHERE user_id = ?)
    """, (char_id, user_id))
    conn.commit()

    return redirect(request.referrer or url_for("characters"))

@app.route("/export")
@login_required
def export():
    # Create in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        conn = get_db()
        db = conn.cursor()
        user_id = session.get("user_id")
        # List of tables to export
        tables = [
            ("anime", "SELECT * FROM anime WHERE user_id = ? ORDER BY id DESC", (user_id,)),
            ("anime_detail", "SELECT * FROM anime_detail WHERE anime_id IN (SELECT id FROM anime WHERE user_id = ?)", (user_id,)),
            ("anime_episodes", "SELECT * FROM anime_episodes WHERE anime_id IN (SELECT id FROM anime WHERE user_id = ?)", (user_id,)),
            ("anime_waifus", "SELECT * FROM anime_waifus WHERE anime_id IN (SELECT id FROM anime WHERE user_id = ?)", (user_id,)),
            ("anime_husbandos", "SELECT * FROM anime_husbandos WHERE anime_id IN (SELECT id FROM anime WHERE user_id = ?)", (user_id,)),
            ("sequel", "SELECT * FROM sequel", ()),
            ("users", "SELECT * FROM users WHERE id = ?", (user_id,)),
        ]
        for table_name, query, params in tables:
            db.execute(query, params)
            rows = db.fetchall()
            if not rows:
                continue
            # Get column names
            col_names = [desc[0] for desc in db.description]
            # Write CSV to string buffer
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(col_names)
            for row in rows:
                writer.writerow(row)
            # Add CSV to zip
            zipf.writestr(f"{table_name}.csv", csv_buffer.getvalue())
        db.close()
        conn.close()
    zip_buffer.seek(0)
    return Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={"Content-Disposition": "attachment; filename=anime_backup.zip"}
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or password != confirmation:
            flash("Invalid input or passwords do not match.")
            return redirect("/register")

        hashed = generate_password_hash(password)

        try:
            conn = get_db()
            db = conn.cursor()
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
            db.close()
            conn.close()
            flash("Registered successfully!")
            return redirect("/login")
        except:
            flash("Username already exists.")
            return redirect("/register")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        db = conn.cursor()
        db.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        user = db.fetchone()
        db.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            flash("Logged in successfully!")
            return redirect("/")
        else:
            flash("Invalid username or password.")
            return redirect("/login")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect("/")

@app.route("/test_upload", methods=["GET", "POST"])
def test_upload():
    if request.method == "POST":
        uploaded_files = request.files.getlist("image_uploads")
        results = []
        for file in uploaded_files:
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(save_path)
                    results.append(f"Successfully uploaded: {filename}")
                except Exception as e:
                    results.append(f"Error uploading {file.filename}: {e}")
        return {"results": results}
    
    return """
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="image_uploads" multiple accept="image/*">
        <button type="submit">Upload</button>
    </form>
    """

@app.route("/export_db")
@login_required
def export_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anime.db')
    return send_file(db_path, as_attachment=True, download_name='anime.db')

if __name__ == "__main__":
    init_db()
    print("anime.db and all tables created!")
