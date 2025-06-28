#!/bin/bash

# Change directory to the folder where this script is located
cd "$(dirname "$0")"

echo "========================================"
echo "Starting Anime Planner"
echo "========================================"
echo

# Git pull on startup
echo "[1/3] Pulling latest changes..."
if git pull origin main; then
    echo "✓ Successfully pulled latest changes"
else
    echo "✗ Failed to pull changes (continuing anyway)"
fi
echo

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

echo "[2/3] Starting Flask application..."
echo
echo "========================================"
echo "Flask is running on http://localhost:5000"
echo "========================================"
echo
echo "To stop Flask gracefully (recommended):"
echo "1. Open a new terminal"
echo "2. Navigate to this folder"
echo "3. Run: pkill -f 'python.*flask'"
echo
echo "Or press Ctrl+C (will kill entire script)"
echo

# Run Flask in background
python -m flask run &
FLASK_PID=$!

echo "[3/3] Flask started in background (PID: $FLASK_PID)"
echo
echo "========================================"
echo "IMPORTANT: Press any key to stop Flask"
echo "and commit changes automatically"
echo "========================================"
echo

# Wait for user to stop Flask
read -n 1 -s -r -p "Press any key when you want to stop Flask and commit changes..."

# Stop Flask gracefully
echo
echo "Stopping Flask..."
if kill $FLASK_PID 2>/dev/null; then
    echo "✓ Flask stopped"
else
    echo "Flask process not found, trying pkill..."
    pkill -f "python.*flask" 2>/dev/null
    echo "✓ Flask stopped"
fi

# Run git operations
echo
echo "========================================"
echo "Committing and Pushing Changes"
echo "========================================"
echo

# Check if we're in a git repository
if ! git status >/dev/null 2>&1; then
    echo "✗ Error: This is not a git repository!"
    read -p "Press Enter to exit..."
    exit 1
fi

# Add all changes
echo "[1/3] Adding all changes..."
if ! git add .; then
    echo "✗ Failed to add changes"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "✓ No changes to commit"
    goto_push=true
else
    goto_push=false
fi

if [ "$goto_push" = false ]; then
    # Get timestamp for commit message
    echo "[2/3] Committing changes..."
    datestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if git commit -m "$datestamp"; then
        echo "✓ Changes committed with message: $datestamp"
    else
        echo "✗ Failed to commit changes"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Push changes
echo "[3/3] Pushing changes..."
if git push origin main; then
    echo "✓ Successfully pushed changes!"
else
    echo "✗ Failed to push changes"
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "========================================"
echo "✓ All operations completed successfully!"
echo "========================================"
echo
read -p "Press Enter to exit..." 