"""
Fetch videos from YouTube channels and add to processing queue
"""

import psycopg2
from googleapiclient.discovery import build
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for config
sys.path.append(str(Path(__file__).parent.parent))
from api.config import Config

config = Config()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY environment variable not set")
    print("Get API key from: https://console.cloud.google.com/apis/credentials")
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
    import re
    
    # PT1H2M10S -> 3730 seconds
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def get_video_details(youtube, video_ids):
    """Fetch detailed metadata for videos"""
    try:
        request = youtube.videos().list(
            part='contentDetails,snippet,statistics',
            id=','.join(video_ids)
        )
        response = request.execute()
        
        details = {}
        for item in response['items']:
            video_id = item['id']
            details[video_id] = {
                'duration': parse_duration(item['contentDetails']['duration']),
                'description': item['snippet'].get('description', ''),
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'view_count': item['statistics'].get('viewCount', 0)
            }
        
        return details
    except Exception as e:
        print(f"Error fetching video details: {e}")
        return {}

def get_channel_videos(channel_id, max_results=50):
    """Fetch videos from a YouTube channel"""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    videos = []
    next_page_token = None
    
    print(f"Fetching videos from channel {channel_id}...")
    
    while len(videos) < max_results:
        try:
            request = youtube.search().list(
                part='id,snippet',
                channelId=channel_id,
                maxResults=min(50, max_results - len(videos)),
                order='date',
                type='video',
                pageToken=next_page_token
            )
            
            response = request.execute()
            
            video_ids = []
            for item in response['items']:
                video_ids.append(item['id']['videoId'])
            
            # Fetch detailed metadata for these videos (in batches of 50)
            if video_ids:
                video_details = get_video_details(youtube, video_ids)
            else:
                video_details = {}
            
            for item in response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                upload_date = item['snippet']['publishedAt'][:10]
                
                # Get detailed metadata
                details = video_details.get(video_id, {})
                
                videos.append({
                    'video_id': video_id,
                    'title': title,
                    'upload_date': upload_date,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'duration_seconds': details.get('duration', 0),
                    'description': details.get('description', ''),
                    'thumbnail_url': details.get('thumbnail', ''),
                    'view_count': details.get('view_count', 0)
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        except Exception as e:
            print(f"Error fetching videos: {e}")
            break
    
    return videos

def add_videos_to_db(speaker_id, videos):
    """Add videos to database and create processing jobs"""
    conn = get_db()
    cur = conn.cursor()
    
    added_count = 0
    skipped_count = 0
    
    for video in videos:
        try:
            # Add video with all metadata
            cur.execute("""
                INSERT INTO videos 
                (video_id, youtube_url, speaker_id, title, description, 
                 duration_seconds, upload_date, thumbnail_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (video_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    duration_seconds = EXCLUDED.duration_seconds,
                    thumbnail_url = EXCLUDED.thumbnail_url
                RETURNING video_id
            """, (
                video['video_id'],
                video['url'],
                speaker_id,
                video['title'],
                video.get('description', ''),
                video.get('duration_seconds', 0),
                video['upload_date'],
                video.get('thumbnail_url', '')
            ))
            
            if cur.fetchone():
                # Create processing job
                cur.execute("""
                    INSERT INTO processing_jobs (video_id, status)
                    VALUES (%s, 'pending')
                """, (video['video_id'],))
                
                added_count += 1
            else:
                skipped_count += 1
            
        except Exception as e:
            print(f"Error adding video {video['video_id']}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return added_count, skipped_count

def populate_videos_for_speaker(speaker_id, max_videos=20):
    """Fetch and add videos for a specific speaker"""
    conn = get_db()
    cur = conn.cursor()
    
    # Get speaker info
    cur.execute("""
        SELECT youtube_channel_id, speaker_name, channel_name, domain
        FROM speakers
        WHERE speaker_id = %s
    """, (speaker_id,))
    
    speaker = cur.fetchone()
    
    if not speaker:
        print(f"Error: Speaker {speaker_id} not found")
        cur.close()
        conn.close()
        return
    
    channel_id, speaker_name, channel_name, domain = speaker
    
    print(f"\nFetching videos for:")
    print(f"  Speaker: {speaker_name}")
    print(f"  Channel: {channel_name}")
    print(f"  Domain: {domain}")
    print(f"  Max videos: {max_videos}")
    print()
    
    # Fetch videos
    videos = get_channel_videos(channel_id, max_videos)
    
    print(f"Found {len(videos)} videos")
    
    if videos:
        # Add to database
        added, skipped = add_videos_to_db(speaker_id, videos)
        print(f"Added {added} new videos, skipped {skipped} duplicates")
    
    cur.close()
    conn.close()

def populate_videos_for_all_speakers(max_videos_per_speaker=20):
    """Fetch videos for all speakers in database"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT speaker_id, youtube_channel_id, speaker_name, domain
        FROM speakers
        ORDER BY domain, speaker_id
    """)
    
    speakers = cur.fetchall()
    
    print(f"\n{'='*60}")
    print(f"Fetching videos for {len(speakers)} speakers")
    print(f"{'='*60}\n")
    
    total_added = 0
    total_skipped = 0
    
    for speaker_id, channel_id, speaker_name, domain in speakers:
        print(f"\n[{domain}] {speaker_name} ({speaker_id})")
        
        videos = get_channel_videos(channel_id, max_videos_per_speaker)
        
        if videos:
            added, skipped = add_videos_to_db(speaker_id, videos)
            total_added += added
            total_skipped += skipped
            print(f"  ✓ Added {added} videos")
        else:
            print(f"  ✗ No videos found")
    
    print(f"\n{'='*60}")
    print(f"Total: {total_added} videos added, {total_skipped} skipped")
    print(f"{'='*60}\n")
    
    cur.close()
    conn.close()

def populate_by_domain(domain, max_videos_per_speaker=20):
    """Fetch videos for all speakers in a specific domain"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT speaker_id, youtube_channel_id, speaker_name
        FROM speakers
        WHERE domain = %s
        ORDER BY speaker_id
    """, (domain,))
    
    speakers = cur.fetchall()
    
    if not speakers:
        print(f"No speakers found in domain: {domain}")
        cur.close()
        conn.close()
        return
    
    print(f"\nFetching videos for {len(speakers)} speakers in domain '{domain}'")
    
    total_added = 0
    
    for speaker_id, channel_id, speaker_name in speakers:
        print(f"\n{speaker_name} ({speaker_id})")
        videos = get_channel_videos(channel_id, max_videos_per_speaker)
        
        if videos:
            added, skipped = add_videos_to_db(speaker_id, videos)
            total_added += added
            print(f"  Added {added} videos")
    
    print(f"\nTotal: {total_added} videos added for domain '{domain}'")
    
    cur.close()
    conn.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_channel_videos.py all <max_per_speaker>        - Fetch for all speakers")
        print("  python fetch_channel_videos.py speaker <speaker_id> <max>   - Fetch for one speaker")
        print("  python fetch_channel_videos.py domain <domain> <max>        - Fetch for domain")
        print("\nDomains: food_blogger, academician, economic, financial, motivational_speaker,")
        print("         comedian, sports_and_gaming, general, other")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'all':
        max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        populate_videos_for_all_speakers(max_videos)
        
    elif command == 'speaker':
        if len(sys.argv) < 3:
            print("Error: speaker_id required")
            sys.exit(1)
        speaker_id = sys.argv[2]
        max_videos = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        populate_videos_for_speaker(speaker_id, max_videos)
        
    elif command == 'domain':
        if len(sys.argv) < 3:
            print("Error: domain required")
            sys.exit(1)
        domain = sys.argv[2]
        max_videos = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        populate_by_domain(domain, max_videos)
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()