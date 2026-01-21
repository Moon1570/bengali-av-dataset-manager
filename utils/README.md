# Database Utilities

This directory contains utility scripts for managing the database.

## db_manager.py

A comprehensive database management tool for viewing, inspecting, and cleaning database tables.

### Usage

#### Interactive Mode (Recommended)
```bash
python db_manager.py
```

This will launch an interactive menu with the following options:
1. List all tables
2. View table contents
3. Show table statistics
4. Clear specific table
5. Clear all tables
6. Show all statistics
0. Exit

#### Command Line Mode

**List all tables:**
```bash
python db_manager.py list
```

**Show statistics for all tables:**
```bash
python db_manager.py stats
```

**View table contents:**
```bash
python db_manager.py view <table_name> [limit]

# Examples:
python db_manager.py view speakers
python db_manager.py view videos 20
python db_manager.py view processing_jobs 50
```

**Clear a specific table:**
```bash
python db_manager.py clear <table_name>

# Example:
python db_manager.py clear processing_results
```

**Clear all tables:**
```bash
python db_manager.py clear all
```
⚠️ Warning: This will delete all data from all tables!

### Features

- ✅ List all database tables
- ✅ View table contents with pagination
- ✅ Show table statistics (row count, columns)
- ✅ Clear specific table
- ✅ Clear all tables (with confirmation)
- ✅ Interactive menu interface
- ✅ Command-line interface
- ✅ Safe deletion with confirmations
- ✅ Proper foreign key handling

### Requirements

```bash
pip install tabulate
```

### Examples

```bash
# Interactive mode
cd utils
python db_manager.py

# View all speakers
python db_manager.py view speakers

# View first 100 videos
python db_manager.py view videos 100

# Show database statistics
python db_manager.py stats

# Clear processing_results table
python db_manager.py clear processing_results

# Clear all tables (dangerous!)
python db_manager.py clear all
```
