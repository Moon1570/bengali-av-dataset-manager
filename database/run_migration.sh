#!/bin/bash
# Run database migration to add video domain support

echo "🔄 Running migration: Add video domain column"
echo "=============================================="

# Get the script's directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env file from project root
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Loading environment from .env file..."
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep DATABASE_URL | xargs)
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable not set"
    echo "Please set it in $PROJECT_ROOT/.env file or export it"
    exit 1
fi

# Run migration
echo "📝 Applying migration..."
psql "$DATABASE_URL" < "$SCRIPT_DIR/migrate_add_video_domain.sql"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "Changes applied:"
    echo "  - Added domain column to videos table"
    echo "  - Initialized domain from speaker domain for existing videos"
    echo "  - Updated pending_videos_queue view"
    echo ""
    echo "You can now:"
    echo "  1. Assign different domains to videos (different from speaker domain)"
    echo "  2. Use the domain dropdown in the web UI"
else
    echo ""
    echo "❌ Migration failed!"
    echo "Please check the error messages above"
    exit 1
fi
