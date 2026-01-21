#!/usr/bin/env python3
"""
Test script to verify chunks API endpoint and file access
"""

import requests
import sys
from pathlib import Path

API_URL = "http://localhost:5000"

def test_chunks_endpoint(video_id):
    """Test fetching chunks for a video"""
    print(f"\n{'='*60}")
    print(f"Testing chunks endpoint for video: {video_id}")
    print(f"{'='*60}\n")
    
    # First, create a session and login (if needed)
    session = requests.Session()
    
    # Test login (you may need to adjust this)
    login_data = {"student_id": "admin"}
    try:
        login_resp = session.post(f"{API_URL}/api/auth/login", json=login_data)
        print(f"✓ Login status: {login_resp.status_code}")
    except Exception as e:
        print(f"⚠ Login skipped: {e}")
    
    # Fetch chunks
    print(f"\n1. Fetching chunks from: {API_URL}/api/videos/{video_id}/chunks")
    try:
        response = session.get(f"{API_URL}/api/videos/{video_id}/chunks")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Success!")
            print(f"   Total chunks: {data.get('total', 0)}")
            print(f"   Storage path: {data.get('storage_path', 'N/A')}")
            
            chunks = data.get('chunks', [])
            if chunks:
                print(f"\n2. Chunk Details:")
                print(f"   {'='*58}")
                for i, chunk in enumerate(chunks, 1):
                    print(f"\n   Chunk {i}: {chunk['chunk_id']}")
                    print(f"   - Video URL: {chunk['video_url']}")
                    print(f"   - Has Audio: {chunk['has_audio']}")
                    print(f"   - Has Cropped: {chunk['has_cropped']}")
                    print(f"   - Has BBox: {chunk['has_bbox']}")
                    if chunk.get('transcription'):
                        print(f"   - Transcription: {chunk['transcription'][:50]}...")
                    else:
                        print(f"   - Transcription: None")
                
                # Test file access for first chunk
                print(f"\n3. Testing File Access (Chunk 1):")
                print(f"   {'='*58}")
                first_chunk = chunks[0]
                
                # Test normal video
                print(f"\n   Testing normal video...")
                video_resp = session.get(f"{API_URL}{first_chunk['video_url']}", stream=True)
                print(f"   - Status: {video_resp.status_code}")
                if video_resp.status_code == 200:
                    content_type = video_resp.headers.get('Content-Type', 'N/A')
                    content_length = video_resp.headers.get('Content-Length', 'N/A')
                    print(f"   - Content-Type: {content_type}")
                    print(f"   - Content-Length: {content_length} bytes")
                    print(f"   ✓ Normal video accessible")
                else:
                    print(f"   ✗ Failed: {video_resp.text}")
                
                # Test cropped video if available
                if first_chunk['has_cropped']:
                    print(f"\n   Testing cropped video...")
                    cropped_resp = session.get(f"{API_URL}{first_chunk['cropped_url']}", stream=True)
                    print(f"   - Status: {cropped_resp.status_code}")
                    if cropped_resp.status_code == 200:
                        print(f"   ✓ Cropped video accessible")
                    else:
                        print(f"   ✗ Failed")
                
                # Test bbox video if available
                if first_chunk['has_bbox']:
                    print(f"\n   Testing bbox video...")
                    bbox_resp = session.get(f"{API_URL}{first_chunk['bbox_url']}", stream=True)
                    print(f"   - Status: {bbox_resp.status_code}")
                    if bbox_resp.status_code == 200:
                        print(f"   ✓ BBox video accessible")
                    else:
                        print(f"   ✗ Failed")
                
                print(f"\n{'='*60}")
                print("✓ Test completed successfully!")
                print(f"{'='*60}\n")
                return True
            else:
                print("\n   ⚠ No chunks found in response")
                return False
        else:
            print(f"   ✗ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_local_files(video_id):
    """Check if files exist locally"""
    print(f"\n{'='*60}")
    print(f"Checking local files for video: {video_id}")
    print(f"{'='*60}\n")
    
    outputs_dir = Path(__file__).parent / 'data' / 'outputs'
    possible_paths = [
        outputs_dir / video_id / video_id,
        outputs_dir / video_id,
    ]
    
    video_dir = None
    for path in possible_paths:
        if path.exists():
            video_dir = path
            print(f"✓ Found video directory: {video_dir}")
            break
    
    if not video_dir:
        print(f"✗ Video directory not found")
        print(f"  Checked paths:")
        for path in possible_paths:
            print(f"    - {path}")
        return False
    
    # Check subdirectories
    print(f"\nDirectory structure:")
    for subdir in ['video_normal', 'video_cropped', 'video_bbox', 'audio', 'google_transcription', 'whisper_transcription']:
        subdir_path = video_dir / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob('*'))
            print(f"  ✓ {subdir}: {len(files)} files")
            if files and len(files) <= 5:
                for f in files:
                    print(f"    - {f.name}")
        else:
            print(f"  ✗ {subdir}: not found")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_chunks_api.py <video_id>")
        print("\nExample: python test_chunks_api.py xJNXkhXScus")
        sys.exit(1)
    
    video_id = sys.argv[1]
    
    # Check local files first
    local_ok = check_local_files(video_id)
    
    if local_ok:
        # Test API endpoint
        test_chunks_endpoint(video_id)
    else:
        print("\n⚠ Skipping API test - local files not found")
