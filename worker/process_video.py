"""
Worker script for hybrid processing
Students run this after claiming video in UI
"""

import requests
import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:5000')
PIPELINE_DIR = os.getenv('PIPELINE_DIR')
STORAGE_BASE = os.getenv('STORAGE_BASE', './data/storage')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './data/downloads')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def download_video(youtube_url, video_id):
    """Download video using yt-dlp"""
    downloads_dir = Path(DOWNLOADS_DIR)
    downloads_dir.mkdir(exist_ok=True, parents=True)
    
    output_path = downloads_dir / f'{video_id}.mp4'
    
    if output_path.exists():
        logger.info(f"Video already downloaded: {output_path}")
        return output_path
    
    logger.info(f"Downloading video: {video_id}")
    
    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '-o', str(output_path),
        '--no-playlist',
        youtube_url
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        logger.info(f"Downloaded: {output_path}")
        return output_path
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def process_video(video_id, preset='balanced'):
    """Run Docker pipeline"""
    logger.info(f"Processing video {video_id} with preset: {preset}")
    logger.info(f"PIPELINE_DIR: {repr(PIPELINE_DIR)}")
    logger.info(f"PIPELINE_DIR exists: {os.path.exists(PIPELINE_DIR) if PIPELINE_DIR else False}")
    
    if not PIPELINE_DIR:
        raise Exception("PIPELINE_DIR not set in environment")
    
    if not os.path.exists(PIPELINE_DIR):
        raise Exception(f"PIPELINE_DIR does not exist: {PIPELINE_DIR}")
    
    # Map preset to pipeline parameters
    preset_params = {
        'strict': ['--preset', 'high', '--filter-faces', '--refine-chunks'],
        'balanced': ['--preset', 'medium', '--filter-faces'],
        'lenient': ['--preset', 'low']
    }
    
    cmd = [
        './run_docker.sh',
        'run',
        video_id
    ] + preset_params.get(preset, preset_params['balanced'])
    
    logger.info(f"Running command: {cmd}")
    logger.info(f"Working directory: {PIPELINE_DIR}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PIPELINE_DIR,
            check=True,
            capture_output=True,
            timeout=3600,
            text=True
        )
        logger.info(f"Processing completed for {video_id}")
        return True
    except subprocess.TimeoutExpired:
        raise Exception("Processing timeout after 1 hour")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Processing failed: {e.stderr}")
    except OSError as e:
        raise Exception(f"OS Error: {e}")

def collect_results(video_id):
    """Collect processing results"""
    experiment_dir = Path(PIPELINE_DIR) / 'experiments' / 'experiment_data' / video_id
    
    if not experiment_dir.exists():
        raise Exception(f"Results not found: {experiment_dir}")
    
    metadata_path = experiment_dir / 'metadata.json'
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    stats = metadata.get('statistics', {})
    
    results = {
        'chunks_created': metadata.get('total_chunks_before_filtering', 0),
        'chunks_passed_sync': metadata.get('chunks_after_filtering', 0),
        'avg_sync_score': stats.get('average_sync_score', 0.0),
        'min_sync_score': stats.get('min_sync_score', 0.0),
        'max_sync_score': stats.get('max_sync_score', 0.0),
        'avg_face_presence': stats.get('average_face_presence', 0.0),
        'min_face_presence': stats.get('min_face_presence', 0.0),
        'max_face_presence': stats.get('max_face_presence', 0.0),
        'total_duration_seconds': stats.get('total_duration_seconds', 0.0),
        'usable_duration_seconds': stats.get('usable_duration_seconds', 0.0),
        'storage_path': str(experiment_dir),
        'file_size_mb': sum(f.stat().st_size for f in experiment_dir.rglob('*') if f.is_file()) / 1024 / 1024,
        'metadata': metadata
    }
    
    return results, experiment_dir

def upload_to_storage(video_id, local_path):
    """Copy results to storage"""
    storage_base = Path(STORAGE_BASE)
    storage_base.mkdir(exist_ok=True, parents=True)
    
    remote_path = storage_base / video_id
    
    logger.info(f"Copying to storage: {remote_path}")
    
    import shutil
    shutil.copytree(local_path, remote_path, dirs_exist_ok=True)
    
    return str(remote_path)

def main(video_id, youtube_url, preset='balanced'):
    """Main processing function"""
    logger.info(f"Starting processing: {video_id}")
    
    try:
        # Step 1: Download
        logger.info("Step 1/4: Downloading video...")
        download_video(youtube_url, video_id)
        
        # Step 2: Process
        logger.info("Step 2/4: Processing with Docker pipeline...")
        process_video(video_id, preset)
        
        # Step 3: Collect results
        logger.info("Step 3/4: Collecting results...")
        results, local_path = collect_results(video_id)
        
        # Step 4: Upload
        logger.info("Step 4/4: Uploading to storage...")
        storage_path = upload_to_storage(video_id, local_path)
        results['storage_path'] = storage_path
        
        logger.info(f"✅ Processing complete: {video_id}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        raise

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python process_video.py <video_id> <youtube_url> [preset]")
        print("Presets: strict, balanced, lenient")
        sys.exit(1)
    
    video_id = sys.argv[1]
    youtube_url = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else 'balanced'
    
    try:
        results = main(video_id, youtube_url, preset)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)