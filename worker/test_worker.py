"""
Test script for worker processing
Tests the full pipeline with a small video
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from process_video import main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_worker():
    """Test the worker with a small Bengali video"""
    
    # Small test videos (choose one or add your own)
    # These should be very short (10-30 seconds) for quick testing
    test_videos = [
        "test_video_123",  # Replace with actual short video ID
        "short_sample",     # Another option
        "wKv-fqH77W8",     # Original (longer video - 85 chunks)
    ]
    
    # Use the first video ID from command line argument or default to first in list
    test_video_id = sys.argv[1] if len(sys.argv) > 1 else test_videos[0]
    test_youtube_url = f"https://www.youtube.com/watch?v={test_video_id}"
    
    logger.info("=" * 80)
    logger.info("TESTING WORKER SCRIPT")
    logger.info("=" * 80)
    logger.info(f"Video ID: {test_video_id}")
    logger.info(f"YouTube URL: {test_youtube_url}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("💡 TIP: Pass a different video ID as argument:")
    logger.info(f"   python test_worker.py <VIDEO_ID>")
    logger.info("")
    logger.info("=" * 80)
    
    try:
        # Test with balanced preset and google transcription
        logger.info("Starting test with balanced preset and google transcription...")
        
        results = main(
            video_id=test_video_id,
            youtube_url=test_youtube_url,
            preset='balanced',
            transcription_model='google'
        )
        
        logger.info("=" * 80)
        logger.info("✅ TEST PASSED!")
        logger.info("=" * 80)
        logger.info("Results:")
        logger.info(f"  - Chunks created: {results.get('chunks_created', 0)}")
        logger.info(f"  - Chunks passed sync: {results.get('chunks_passed_sync', 0)}")
        logger.info(f"  - Avg sync score: {results.get('avg_sync_score', 0.0):.2f}")
        logger.info(f"  - Avg face presence: {results.get('avg_face_presence', 0.0):.2%}")
        logger.info(f"  - Total duration: {results.get('total_duration_seconds', 0.0):.1f}s")
        logger.info(f"  - Usable duration: {results.get('usable_duration_seconds', 0.0):.1f}s")
        logger.info(f"  - Storage path: {results.get('storage_path', 'N/A')}")
        logger.info(f"  - File size: {results.get('file_size_mb', 0.0):.2f} MB")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ TEST FAILED!")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 80)
        return False

if __name__ == '__main__':
    logger.info("Starting worker test...")
    success = test_worker()
    
    if success:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Tests failed!")
        sys.exit(1)
