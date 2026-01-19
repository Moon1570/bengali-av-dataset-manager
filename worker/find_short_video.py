"""
Quick script to find short videos via API for testing
"""

import requests
import os

API_URL = os.getenv('API_URL', 'http://localhost:5000')

def find_short_videos():
    """Find videos available in the queue for testing"""
    
    try:
        # Login first (need to use a valid student_id from workers table)
        session = requests.Session()
        login_response = session.post(
            f"{API_URL}/api/auth/login",
            json={"student_id": "student0000"}  # Using student0000
        )
        
        print(f"Login attempt to: {API_URL}/api/auth/login")
        print(f"Status code: {login_response.status_code}")
        print(f"Response: {login_response.text[:200]}")
        
        if login_response.status_code != 200:
            print("❌ Failed to login to API. Make sure the API server is running.")
            print(f"   Try: cd api && python app.py")
            return
        
        # Get next videos from queue
        response = session.get(f"{API_URL}/api/videos/next")
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch videos: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        data = response.json()
        videos = data.get('videos', [])
        
        if not videos:
            print("❌ No videos available in the queue.")
            return
        
        print("=" * 80)
        print("AVAILABLE VIDEOS FOR TESTING")
        print("=" * 80)
        
        for i, video in enumerate(videos, 1):
            duration = video.get('duration_seconds') or 0
            mins = duration // 60
            secs = duration % 60
            
            print(f"\n{i}. Video ID: {video['video_id']}")
            print(f"   Duration: {duration}s ({mins}m {secs}s)")
            print(f"   Title: {video['title'][:60]}...")
            print(f"   Speaker: {video.get('speaker_name', 'Unknown')}")
            print(f"   URL: {video['youtube_url']}")
        
        print("\n" + "=" * 80)
        
        # Find shortest video
        shortest = min(videos, key=lambda v: v.get('duration_seconds', float('inf')))
        
        print(f"\n✅ To test with the shortest video ({shortest.get('duration_seconds')}s), run:")
        print(f"   ../.venv/bin/python test_worker.py {shortest['video_id']}")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server.")
        print(f"   Make sure the API is running at {API_URL}")
        print(f"   Try: cd api && python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    find_short_videos()
