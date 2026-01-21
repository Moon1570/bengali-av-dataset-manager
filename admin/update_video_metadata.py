"""
Update existing videos with missing metadata (duration, description, thumbnail)
"""

from googleapiclient.discovery import build
import psycopg2
import os
import sys
from pathlib import Path
import re

# Add parent directory to path for config
sys.path.append(str(Path(__file__).parent.parent))
from api.config import Config

config = Config()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY environment variable not set")
    sys.exit(1)

def get_db():
    """Get database connection"""
    return psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )

def parse_duration(duration_str):
    """Convert ISO 8601 duration to seconds"""
    # PT1H2M10S -> 3730 seconds
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def get_video_metadata(youtube, video_ids):
    """Fetch detailed metadata for videos"""
    if not video_ids:
        return {}
    
    try:
        request = youtube.videos().list(
            part='contentDetails,snippet,statistics',
            id=','.join(video_ids)
        )
        response = request.execute()
        
        metadata = {}
        for item in response['items']:
            video_id = item['id']
            metadata[video_id] = {
                'duration': parse_duration(item['contentDetails']['duration']),
                'description': item['snippet'].get('description', '')[:500],  # Truncate to 500 chars
                'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'high' in item['snippet']['thumbnails'] else '',
            }
        
        return metadata
    except Exception as e:
        print(f"Error fetching video metadata: {e}")
        return {}

def update_videos_metadata():
    """Update all videos missing duration metadata"""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    conn = get_db()
    cur = conn.cursor()
    
    # Find videos with missing or zero duration
    cur.execute("""
        SELECT video_id FROM videos 
        WHERE duration_seconds IS NULL OR duration_seconds = 0
        ORDER BY added_at DESC
    """)
    
    video_ids = [row[0] for row in cur.fetchall()]
    
    if not video_ids:
        print("✅ All videos have duration metadata")
        cur.close()
        conn.close()
        return
    
    print(f"Found {len(video_ids)} videos missing duration metadata")
    print("Fetching metadata from YouTube...")
    
    # Process in batches of 50 (YouTube API limit)
    batch_size = 50
    updated_count = 0
    failed_count = 0
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(video_ids)-1)//batch_size + 1} ({len(batch)} videos)...")
        
        metadata = get_video_metadata(youtube, batch)
        
        for video_id, data in metadata.items():
            try:
                cur.execute("""
                    UPDATE videos
                    SET duration_seconds = %s,
                        description = %s,
                        thumbnail_url = %s
                    WHERE video_id = %s
                """, (
                    data['duration'],
                    data['description'],
                    data['thumbnail'],
                    video_id
                ))
                updated_count += 1
                
                # Print duration for verification
                mins = data['duration'] // 60
                secs = data['duration'] % 60
                print(f"  ✓ {video_id}: {data['duration']}s ({mins}m {secs}s)")
                
            except Exception as e:
                print(f"  ✗ Error updating {video_id}: {e}")
                failed_count += 1
        
        conn.commit()
    
    print(f"\n{'='*60}")
    print(f"✅ Updated {updated_count} videos")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} videos")
    print(f"{'='*60}")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    update_videos_metadata()
