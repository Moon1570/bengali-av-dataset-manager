#!/bin/bash

# Initialize Render PostgreSQL Database from Mac
# Run this after creating database in Render

set -e

echo "========================================="
echo "Render Database Initialization (Mac)"
echo "========================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set"
    echo ""
    echo "Set it with:"
    echo "  export DATABASE_URL='postgresql://user:pass@host/database'"
    echo ""
    echo "Get it from: https://dashboard.render.com/databases"
    exit 1
fi

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql not installed"
    echo "Install with: brew install postgresql"
    exit 1
fi

echo ""
echo "Testing connection..."
psql "$DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "ERROR: Cannot connect to database"
    echo "Check your DATABASE_URL"
    exit 1
fi

echo "✓ Connection successful"

echo ""
echo "Running schema.sql..."
psql "$DATABASE_URL" -f "/Users/darklord/Research/Audio_Visual/bengali-av-dataset-manager/bengali-av-dataset-manager/database/schema.sql"

if [ $? -ne 0 ]; then
    echo "ERROR: Schema creation failed"
    exit 1
fi

echo "✓ Schema created"

echo ""
echo "Verifying installation..."
psql "$DATABASE_URL" -c "\dt" | grep -q "speakers"

if [ $? -eq 0 ]; then
    echo "✓ Tables created successfully"
else
    echo "ERROR: Tables not found"
    exit 1
fi

# Count tables
TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

echo ""
echo "========================================="
echo "Database initialized successfully!"
echo "========================================="
echo ""
echo "Tables created: $TABLE_COUNT"
echo ""
echo "Next steps:"
echo "1. Add environment variable to .env:"
echo "   DATABASE_URL=$DATABASE_URL"
echo ""
echo "2. Test with:"
echo "   psql \"\$DATABASE_URL\" -c 'SELECT * FROM workers;'"
echo ""