#!/usr/bin/env python3
"""
Test script to verify video processing setup
"""

import sys
from pathlib import Path

# Add worker to path
sys.path.insert(0, str(Path(__file__).parent / 'worker'))

from process_video import download_video, process_video
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_paths():
    """Test path resolution"""
    logger.info("Testing path resolution...")
    
    from worker.process_video import DOWNLOADS_DIR, PIPELINE_DIR, STORAGE_BASE
    
    logger.info(f"DOWNLOADS_DIR: {DOWNLOADS_DIR}")
    logger.info(f"PIPELINE_DIR: {PIPELINE_DIR}")
    logger.info(f"STORAGE_BASE: {STORAGE_BASE}")
    
    # Resolve downloads path
    script_dir = Path(__file__).parent
    downloads_path = (script_dir / DOWNLOADS_DIR).resolve()
    logger.info(f"Resolved downloads path: {downloads_path}")
    logger.info(f"Downloads path exists: {downloads_path.exists()}")
    
    if PIPELINE_DIR:
        pipeline_path = Path(PIPELINE_DIR)
        logger.info(f"Pipeline path exists: {pipeline_path.exists()}")
        pipeline_downloads = pipeline_path / 'downloads'
        logger.info(f"Pipeline downloads path: {pipeline_downloads}")
        logger.info(f"Pipeline downloads exists: {pipeline_downloads.exists()}")

def test_download():
    """Test downloading a short video"""
    logger.info("Testing video download...")
    
    # Use a very short test video (a few seconds)
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video, 19 seconds
    test_id = "jNQXAC9IVRw"
    
    try:
        video_path = download_video(test_url, test_id)
        logger.info(f"✅ Download successful: {video_path}")
        logger.info(f"File size: {video_path.stat().st_size / 1024 / 1024:.2f} MB")
        return test_id
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return None

def test_copy():
    """Test copying video to pipeline directory"""
    logger.info("Testing video copy to pipeline...")
    
    from worker.process_video import DOWNLOADS_DIR, PIPELINE_DIR
    import shutil
    
    script_dir = Path(__file__).parent
    
    # Check for any existing video
    downloads_path = (script_dir / DOWNLOADS_DIR).resolve()
    videos = list(downloads_path.glob('*.mp4'))
    
    if not videos:
        logger.error("❌ No videos found to test copy")
        return False
    
    test_video = videos[0]
    video_id = test_video.stem
    logger.info(f"Using test video: {test_video}")
    
    # Try copying
    pipeline_downloads = Path(PIPELINE_DIR) / 'downloads'
    pipeline_downloads.mkdir(exist_ok=True, parents=True)
    dest_video = pipeline_downloads / f'{video_id}.mp4'
    
    logger.info(f"Copying from: {test_video}")
    logger.info(f"Copying to: {dest_video}")
    
    try:
        shutil.copy2(test_video, dest_video)
        logger.info(f"✅ Copy successful")
        logger.info(f"Destination exists: {dest_video.exists()}")
        logger.info(f"Destination size: {dest_video.stat().st_size / 1024 / 1024:.2f} MB")
        return True
    except Exception as e:
        logger.error(f"❌ Copy failed: {e}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test video processing setup')
    parser.add_argument('--test', choices=['paths', 'download', 'copy', 'all'], default='all',
                       help='Which test to run')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Video Processing Mock Test")
    logger.info("=" * 60)
    
    if args.test in ['paths', 'all']:
        test_paths()
        logger.info("-" * 60)
    
    if args.test in ['download', 'all']:
        test_id = test_download()
        logger.info("-" * 60)
    
    if args.test in ['copy', 'all']:
        test_copy()
        logger.info("-" * 60)
    
    logger.info("✅ Mock test completed")
