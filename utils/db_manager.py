"""
Database Management Utility
Manage database tables: view, clean, inspect
"""

import psycopg2
import sys
from pathlib import Path
from tabulate import tabulate

# Add parent directory to path for config
sys.path.append(str(Path(__file__).parent.parent))
from api.config import Config

config = Config()


def get_db():
    """Get database connection"""
    return psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )


def list_tables():
    """List all tables in the database"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    cur.close()
    conn.close()
    
    return [table[0] for table in tables]


def get_table_stats(table_name):
    """Get statistics for a specific table"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = cur.fetchall()
        
        return {
            'count': count,
            'columns': columns
        }
    except Exception as e:
        return {'error': str(e)}
    finally:
        cur.close()
        conn.close()


def view_table(table_name, limit=10):
    """View contents of a specific table"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
        rows = cur.fetchall()
        
        # Get column names
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = [col[0] for col in cur.fetchall()]
        
        return columns, rows
    except Exception as e:
        print(f"❌ Error viewing table: {e}")
        return None, None
    finally:
        cur.close()
        conn.close()


def clear_table(table_name, confirm=True):
    """Clear all data from a specific table"""
    if confirm:
        response = input(f"⚠️  Are you sure you want to clear table '{table_name}'? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return False
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute(f"DELETE FROM {table_name}")
        conn.commit()
        deleted_count = cur.rowcount
        print(f"✅ Cleared {deleted_count} rows from '{table_name}'")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error clearing table: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def clear_all_tables(confirm=True):
    """Clear all data from all tables"""
    if confirm:
        response = input("⚠️  Are you sure you want to clear ALL tables? This cannot be undone! (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return False
    
    tables = list_tables()
    conn = get_db()
    cur = conn.cursor()
    
    # Order matters due to foreign key constraints
    ordered_tables = [
        'processing_results',
        'processing_jobs',
        'videos',
        'speakers',
        'workers'
    ]
    
    # Add any remaining tables
    for table in tables:
        if table not in ordered_tables:
            ordered_tables.append(table)
    
    try:
        for table in ordered_tables:
            if table in tables:
                cur.execute(f"DELETE FROM {table}")
                deleted = cur.rowcount
                print(f"  ✓ Cleared {deleted} rows from '{table}'")
        
        conn.commit()
        print("\n✅ All tables cleared successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error clearing tables: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def show_all_stats():
    """Show statistics for all tables"""
    tables = list_tables()
    
    print("\n" + "="*70)
    print("📊 Database Statistics")
    print("="*70 + "\n")
    
    stats_data = []
    for table in tables:
        stats = get_table_stats(table)
        if 'error' not in stats:
            stats_data.append([
                table,
                stats['count'],
                len(stats['columns'])
            ])
    
    print(tabulate(stats_data, headers=['Table Name', 'Row Count', 'Columns'], tablefmt='grid'))
    print()


def interactive_menu():
    """Interactive menu for database management"""
    while True:
        print("\n" + "="*70)
        print("🗄️  Database Manager")
        print("="*70)
        print("\n1. List all tables")
        print("2. View table contents")
        print("3. Show table statistics")
        print("4. Clear specific table")
        print("5. Clear all tables")
        print("6. Show all statistics")
        print("0. Exit")
        print()
        
        choice = input("Select option (0-6): ").strip()
        
        if choice == '0':
            print("\n👋 Goodbye!")
            break
            
        elif choice == '1':
            tables = list_tables()
            print("\n📋 Tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            print()
            
        elif choice == '2':
            tables = list_tables()
            print("\n📋 Available tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            
            table_choice = input("\nEnter table number or name: ").strip()
            
            # Handle numeric or name input
            if table_choice.isdigit():
                idx = int(table_choice) - 1
                if 0 <= idx < len(tables):
                    table_name = tables[idx]
                else:
                    print("❌ Invalid table number")
                    continue
            else:
                table_name = table_choice
            
            limit = input("Number of rows to display (default 10): ").strip() or "10"
            
            columns, rows = view_table(table_name, int(limit))
            if columns and rows:
                print(f"\n📊 Contents of '{table_name}' (showing {len(rows)} rows):\n")
                print(tabulate(rows, headers=columns, tablefmt='grid'))
            elif columns:
                print(f"\n📊 Table '{table_name}' is empty")
                
        elif choice == '3':
            tables = list_tables()
            print("\n📋 Available tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            
            table_choice = input("\nEnter table number or name: ").strip()
            
            # Handle numeric or name input
            if table_choice.isdigit():
                idx = int(table_choice) - 1
                if 0 <= idx < len(tables):
                    table_name = tables[idx]
                else:
                    print("❌ Invalid table number")
                    continue
            else:
                table_name = table_choice
            
            stats = get_table_stats(table_name)
            if 'error' not in stats:
                print(f"\n📊 Statistics for '{table_name}':")
                print(f"  Total rows: {stats['count']}")
                print(f"\n  Columns:")
                for col_name, col_type in stats['columns']:
                    print(f"    - {col_name} ({col_type})")
            else:
                print(f"❌ Error: {stats['error']}")
                
        elif choice == '4':
            tables = list_tables()
            print("\n📋 Available tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            
            table_choice = input("\nEnter table number or name: ").strip()
            
            # Handle numeric or name input
            if table_choice.isdigit():
                idx = int(table_choice) - 1
                if 0 <= idx < len(tables):
                    table_name = tables[idx]
                else:
                    print("❌ Invalid table number")
                    continue
            else:
                table_name = table_choice
            
            clear_table(table_name)
            
        elif choice == '5':
            clear_all_tables()
            
        elif choice == '6':
            show_all_stats()
            
        else:
            print("❌ Invalid choice. Please select 0-6.")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'list':
            tables = list_tables()
            print("\n📋 Tables:")
            for table in tables:
                print(f"  - {table}")
            print()
            
        elif command == 'stats':
            show_all_stats()
            
        elif command == 'view':
            if len(sys.argv) < 3:
                print("❌ Usage: python db_manager.py view <table_name> [limit]")
                sys.exit(1)
            
            table_name = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            
            columns, rows = view_table(table_name, limit)
            if columns and rows:
                print(f"\n📊 Contents of '{table_name}':\n")
                print(tabulate(rows, headers=columns, tablefmt='grid'))
            elif columns:
                print(f"\n📊 Table '{table_name}' is empty")
                
        elif command == 'clear':
            if len(sys.argv) < 3:
                print("❌ Usage: python db_manager.py clear <table_name|all>")
                sys.exit(1)
            
            target = sys.argv[2]
            if target == 'all':
                clear_all_tables()
            else:
                clear_table(target)
                
        else:
            print(f"❌ Unknown command: {command}")
            print("\nAvailable commands:")
            print("  list               - List all tables")
            print("  stats              - Show statistics for all tables")
            print("  view <table> [n]   - View n rows from table (default 10)")
            print("  clear <table|all>  - Clear specific table or all tables")
            print("  (no args)          - Interactive menu")
            sys.exit(1)
    else:
        # No arguments - show interactive menu
        interactive_menu()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
