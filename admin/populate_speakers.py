"""
Populate speakers database from CSV or manual entry
"""

import psycopg2
import csv
import sys
from pathlib import Path

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

def add_speaker(speaker_id, channel_id, channel_name, speaker_name, domain='general', gender=None, nationality='BD'):
    """Add a single speaker to database"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO speakers 
            (speaker_id, youtube_channel_id, channel_name, speaker_name, domain, gender, nationality)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (speaker_id) DO UPDATE
            SET channel_name = EXCLUDED.channel_name,
                speaker_name = EXCLUDED.speaker_name,
                domain = EXCLUDED.domain,
                gender = EXCLUDED.gender,
                nationality = EXCLUDED.nationality,
                updated_at = NOW()
        """, (speaker_id, channel_id, channel_name, speaker_name, domain, gender, nationality))
        
        conn.commit()
        print(f"✓ Added speaker: {speaker_id} - {speaker_name} ({domain})")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error adding speaker {speaker_id}: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def import_from_csv(csv_file):
    """
    Import speakers from CSV file
    
    CSV format:
    speaker_id,channel_id,channel_name,speaker_name,domain,gender,nationality
    """
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        return
    
    print(f"Importing speakers from {csv_file}...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        count = 0
        for row in reader:
            success = add_speaker(
                row['speaker_id'],
                row['channel_id'],
                row['channel_name'],
                row['speaker_name'],
                row.get('domain', 'general'),
                row.get('gender'),
                row.get('nationality', 'BD')
            )
            if success:
                count += 1
    
    print(f"\nImported {count} speakers")

def list_speakers():
    """List all speakers in database"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT speaker_id, speaker_name, channel_name, domain
        FROM speakers
        ORDER BY domain, speaker_id
    """)
    
    speakers = cur.fetchall()
    
    print("\nCurrent speakers in database:")
    print("-" * 80)
    print(f"{'ID':<12} {'Name':<25} {'Channel':<30} {'Domain':<15}")
    print("-" * 80)
    
    for speaker_id, name, channel, domain in speakers:
        print(f"{speaker_id:<12} {name:<25} {channel:<30} {domain:<15}")
    
    print("-" * 80)
    print(f"Total: {len(speakers)} speakers")
    
    cur.close()
    conn.close()

def interactive_add():
    """Interactively add speakers"""
    print("\n" + "="*60)
    print("Add Speaker Interactively")
    print("="*60)
    
    speaker_id = input("Speaker ID (e.g., SPK001): ").strip()
    channel_id = input("YouTube Channel ID (e.g., UCxxxxx): ").strip()
    channel_name = input("Channel Name: ").strip()
    speaker_name = input("Speaker Name: ").strip()
    
    print("\nDomain options:")
    print("  1. food_blogger")
    print("  2. academician")
    print("  3. economic")
    print("  4. financial")
    print("  5. motivational_speaker")
    print("  6. comedian")
    print("  7. sports_and_gaming")
    print("  8. general")
    print("  9. other")
    
    domain_choice = input("Select domain (1-9): ").strip()
    domain_map = {
        '1': 'food_blogger',
        '2': 'academician',
        '3': 'economic',
        '4': 'financial',
        '5': 'motivational_speaker',
        '6': 'comedian',
        '7': 'sports_and_gaming',
        '8': 'general',
        '9': 'other'
    }
    domain = domain_map.get(domain_choice, 'general')
    
    gender = input("Gender (M/F/Other, or leave blank): ").strip() or None
    nationality = input("Nationality (default BD): ").strip() or 'BD'
    
    print("\nAdding speaker...")
    add_speaker(speaker_id, channel_id, channel_name, speaker_name, domain, gender, nationality)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python populate_speakers.py import <csv_file>   - Import from CSV")
        print("  python populate_speakers.py add                 - Add speaker interactively")
        print("  python populate_speakers.py list                - List all speakers")
        print("\nCSV format:")
        print("  speaker_id,channel_id,channel_name,speaker_name,domain,gender,nationality")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'import':
        if len(sys.argv) < 3:
            print("Error: CSV file required")
            print("Usage: python populate_speakers.py import <csv_file>")
            sys.exit(1)
        import_from_csv(sys.argv[2])
        
    elif command == 'add':
        interactive_add()
        
    elif command == 'list':
        list_speakers()
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()