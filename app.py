from flask import Flask, render_template, request, redirect, flash, session, url_for, Response
from flask_session import Session
import sqlite3
import os
from datetime import datetime
import csv
import io
import json
from werkzeug.utils import secure_filename
from cs50 import SQl
# Configure application
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Custom filter for date formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%b %Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

# Database setup (will auto-create tables if not exists)
def init_db():
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute("""
            CREATE TABLE IF NOT EXISTS anime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                rating REAL,
                thoughts TEXT,
                date TEXT,
                sequel TEXT,
                details_url TEXT,
                background_url TEXT
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
                images TEXT,  -- JSON list of image URLs or filenames
                story_rating REAL,
                visual_rating REAL,
                sound_rating REAL,
                lessons TEXT,
                rating_note TEXT,
                favorite_episodes TEXT,
                poster_url TEXT,
                background_url TEXT
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
                    note TEXT, starred BOOLEAN DEFAULT 0,
                    FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
                )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS anime_waifus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL,
                name TEXT,
                image TEXT,
                note TEXT, starred BOOLEAN DEFAULT 0,
                FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
            )
        """)



        conn.commit()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        title = request.form.get("title")
        rating = request.form.get("rating") or 0
        rating = float(rating) if rating else 0
        thoughts = request.form.get("thoughts")
        date = request.form.get("date")
        sequel = request.form.get("sequel")
        details_url = request.form.get("details_url")
        background_url = request.form.get("background_url")
        no_date = request.form.get("no_date")

        if not title:
            flash("Please enter a title")
            return redirect("/add")

        if no_date:
            date = None
        elif not date:
            date = datetime.today().strftime('%Y-%m-%d')

        with sqlite3.connect("anime.db") as conn:
            db = conn.cursor()
            db.execute("""
                INSERT INTO anime (title, rating, thoughts, date, sequel, details_url, background_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, rating, thoughts, date, sequel, details_url, background_url))

            if sequel:
                db.execute("INSERT OR IGNORE INTO sequel (name) VALUES (?)", (sequel,))

            conn.commit()

        flash("Anime added successfully!")
        return redirect("/preview")
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        sort_by_rating = request.args.get("sort_by_rating")


    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute("UPDATE anime SET rating = 0 WHERE rating IS NULL OR rating = ''")
        conn.commit()



        if sort_by_rating:
            db.execute("SELECT title FROM anime WHERE rating IS NOT NULL ORDER BY rating DESC")
        else:
            db.execute("SELECT DISTINCT title FROM anime ORDER BY title")

    sequel_list = [row[0] for row in db.fetchall()]


    return render_template("add.html", sequel_list=sequel_list, sort_active=bool(sort_by_rating))

@app.route("/preview")
def preview():
    sort_by_rating = request.args.get("sort_by_rating")
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        if sort_by_rating:
            db.execute("SELECT * FROM anime ORDER BY rating DESC")
            sort_active = True
        else:
            db.execute("SELECT * FROM anime ORDER BY id DESC")
            sort_active = False

        anime_list = db.fetchall()

        # Get anime IDs that have details
        db.execute("SELECT anime_id FROM anime_detail")
        detail_ids = set(row[0] for row in db.fetchall())

    return render_template("preview.html", anime_list=anime_list, detail_ids=detail_ids, sort_active=sort_active)



@app.route("/edit/<int:anime_id>", methods=["GET", "POST"])
def edit(anime_id):
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        if request.method == "POST":
            title = request.form.get("title")
            rating = request.form.get("rating")
            thoughts = request.form.get("thoughts")
            date = request.form.get("date")
            sequel = request.form.get("sequel")
            details_url = request.form.get("details_url")
            background_url = request.form.get("background_url")
            no_date = request.form.get("no_date")

            if no_date:
                date = None
            elif not date:
                date = datetime.today().strftime('%Y-%m-%d')

            db.execute("""
                UPDATE anime
                SET title = ?, rating = ?, thoughts = ?, date = ?, sequel = ?, details_url = ?, background_url = ?
                WHERE id = ?
            """, (title, rating, thoughts, date, sequel, details_url, background_url, anime_id))

            if sequel:
                db.execute("INSERT OR IGNORE INTO sequel (name) VALUES (?)", (sequel,))

            conn.commit()
            flash("Anime updated successfully!")
            return redirect("/preview")

        db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
        anime = db.fetchone()
        db.execute("SELECT DISTINCT title FROM anime ORDER BY title")
        sequel_list = [row[0] for row in db.fetchall()]

    return render_template("edit.html", anime=anime, sequel_list=sequel_list)

@app.route("/delete/<int:anime_id>", methods=["POST"])
def delete(anime_id):
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
        conn.commit()
    flash("Anime deleted successfully!")
    return redirect("/preview")

@app.route("/list")
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

    # Build SQL dynamically
    base_query = f"SELECT id, title, rating, date FROM anime"
    if filter_null == "nonull":
        base_query += f" WHERE {sort_column} IS NOT NULL"

    base_query += f" ORDER BY {sort_column} {order.upper()}"

    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute(base_query)
        anime_list = db.fetchall()

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
def detail(anime_id):
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()

        # Fetch main anime data
        db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
        anime = db.fetchone()

        if not anime:
            flash("Anime not found.")
            return redirect("/preview")

        # Fetch detailed info
        db.execute("SELECT * FROM anime_detail WHERE anime_id = ?", (anime_id,))
        detail = db.fetchone()

        # Decode image list
        image_urls = []
        if detail and detail[3]:
            try:
                image_urls = json.loads(detail[3])
            except:
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
def edit_detail(anime_id):
    UPLOAD_FOLDER = "static/uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()

        db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
        anime = db.fetchone()
        if not anime:
            flash("Anime not found.")
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

            # === Handle images ===
            image_urls = [url.strip() for url in images_raw.split(",") if url.strip()]
            uploaded_files = request.files.getlist("image_uploads")
            uploaded_paths = []
            for file in uploaded_files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(save_path)
                    uploaded_paths.append(f"uploads/{filename}")
            all_images = image_urls + uploaded_paths
            image_json = json.dumps(all_images)

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
                db.execute("""
                    INSERT INTO anime_detail (
                        anime_id, extra_notes, lessons, favorite_episodes, poster_url, background_url,
                        images, story_rating, visual_rating, sound_rating, rating_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    anime_id, extra_notes, lessons, favorite_episodes, poster_url, background_url,
                    image_json, story_rating, visual_rating, sound_rating, rating_note
                ))

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
                    ep_images = json.dumps([url.strip() for url in ep_images_raw.split(",") if url.strip()])
                    ep_overall = request.form.get(f"episode_overall_{eid}") or 0
                    ep_animation = request.form.get(f"episode_animation_{eid}") or 0
                    ep_story = request.form.get(f"episode_story_{eid}") or 0

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

            for i in range(len(new_episode_numbers)):
                try:
                    ep_num = int(new_episode_numbers[i])
                    ep_note = new_episode_notes[i]
                    ep_images = json.dumps([url.strip() for url in new_episode_images[i].split(",") if url.strip()])
                    ep_overall = float(new_episode_overalls[i]) if new_episode_overalls[i] else 0
                    ep_animation = float(new_episode_animations[i]) if new_episode_animations[i] else 0
                    ep_story = float(new_episode_stories[i]) if new_episode_stories[i] else 0

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
            for i in range(len(new_waifu_names)):
                name = new_waifu_names[i]
                image = new_waifu_images[i]
                note = new_waifu_notes[i]
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
            for i in range(len(new_husbando_names)):
                name = new_husbando_names[i]
                image = new_husbando_images[i]
                note = new_husbando_notes[i]
                if name:
                    db.execute("""
                        INSERT INTO anime_husbandos (anime_id, name, image, note)
                        VALUES (?, ?, ?, ?)
                    """, (anime_id, name, image, note))

            conn.commit()
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
def list_detail():
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute("""
            SELECT a.*, d.extra_notes, d.images, d.story_rating, d.visual_rating, d.sound_rating
            FROM anime a
            LEFT JOIN anime_detail d ON a.id = d.anime_id
            ORDER BY a.id DESC
        """)
        anime_list = db.fetchall()
    return render_template("list_detail.html", anime_list=anime_list)

@app.template_filter('loads')
def json_loads_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []

@app.route("/characters", methods=["GET", "POST"])
def characters():
    search = request.args.get("search", "").strip()
    query = "%" + search + "%" if search else "%"

    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()

        # Fetch waifus
        db.execute("""
            SELECT w.id, w.name, w.image, w.note, w.starred, a.id, a.title
            FROM anime_waifus w
            JOIN anime a ON w.anime_id = a.id
            WHERE w.name LIKE ?
            ORDER BY w.starred DESC, w.name
        """, (query,))
        waifus = db.fetchall()

        # Fetch husbandos
        db.execute("""
            SELECT h.id, h.name, h.image, h.note, h.starred, a.id, a.title
            FROM anime_husbandos h
            JOIN anime a ON h.anime_id = a.id
            WHERE h.name LIKE ?
            ORDER BY h.starred DESC, h.name
        """, (query,))
        husbandos = db.fetchall()

    return render_template("characters.html", waifus=waifus, husbandos=husbandos, search=search)

@app.route("/toggle_star/<string:character_type>/<int:char_id>", methods=["POST"])
def toggle_star(character_type, char_id):
    if character_type not in ("waifu", "husbando"):
        return "Invalid type", 400

    table = "anime_waifus" if character_type == "waifu" else "anime_husbandos"

    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute(f"UPDATE {table} SET starred = NOT starred WHERE id = ?", (char_id,))
        conn.commit()

    return redirect(request.referrer or url_for("characters"))

@app.route("/export")
def export():
    # Create string buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["id", "title", "rating", "thoughts", "date", "sequel", "details_url", "background_url"])

    # Get data and write rows
    with sqlite3.connect("anime.db") as conn:
        db = conn.cursor()
        db.execute("SELECT * FROM anime ORDER BY id DESC")
        rows = db.fetchall()

        for row in rows:
            # Replace None values with empty strings
            clean_row = [cell if cell is not None else "" for cell in row]
            writer.writerow(clean_row)

    # Get CSV content
    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=anime_list.csv"}
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
