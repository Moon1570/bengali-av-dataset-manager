#!/bin/bash

# Database initialization script
# Run this to set up the PostgreSQL database

set -e

echo "========================================="
echo "Bengali Dataset Database Setup"
echo "========================================="

# Load environment variables from .env if it exists
if [ -f "../.env" ]; then
    echo "Loading configuration from .env file..."
    export $(grep -v '^#' ../.env | xargs)
fi

# Configuration
DB_NAME="${DB_NAME:-bn_av_dataset}"
DB_USER="${DB_USER:-Moon1570}"
DB_PASSWORD="${DB_PASSWORD:-changeme123}"  # Use env var or default

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "Detected OS: $MACHINE"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed"
    if [ "$MACHINE" = "Linux" ]; then
        echo "Install with: sudo apt-get install postgresql postgresql-contrib"
    else
        echo "Install with: brew install postgresql@14"
    fi
    exit 1
fi

# Check if PostgreSQL is running and start if needed
if [ "$MACHINE" = "Linux" ]; then
    if ! sudo systemctl is-active --quiet postgresql; then
        echo "Starting PostgreSQL..."
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
elif [ "$MACHINE" = "Mac" ]; then
    if ! brew services list | grep -q "postgresql.*started"; then
        echo "Starting PostgreSQL..."
        brew services start postgresql@14
    fi
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if psql -U "$USER" -d postgres -c "SELECT 1" &> /dev/null; then
            echo "✓ PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "ERROR: PostgreSQL failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
fi

echo ""
echo "Step 1: Creating database user and database..."

# Create user and database
if [ "$MACHINE" = "Linux" ]; then
    sudo -u postgres psql <<EOF
-- Drop existing database if exists (be careful!)
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;

-- Create new user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

\q
EOF
elif [ "$MACHINE" = "Mac" ]; then
    psql postgres <<EOF
-- Drop existing database if exists (be careful!)
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;

-- Create new user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

\q
EOF
fi

echo "✓ Database and user created"

echo ""
echo "Step 2: Creating schema..."

# Run schema file
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -f schema.sql

echo "✓ Schema created successfully"

echo ""
echo "Step 3: Verifying installation..."

# Verify tables
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME <<EOF
\dt
SELECT 'Total tables: ' || COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
\q
EOF

echo ""
echo "========================================="
echo "Database setup complete!"
echo "========================================="
echo ""
echo "Connection details:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "Add to your .env file:"
echo "  DB_HOST=localhost"
echo "  DB_NAME=$DB_NAME"
echo "  DB_USER=$DB_USER"
echo "  DB_PASSWORD=$DB_PASSWORD"
echo ""
echo "Test connection:"
echo "  psql -U $DB_USER -d $DB_NAME"
echo ""