"""
Worker script for processing videos
Claim job from API, download video, process it, upload results
"""

import requests
import subprocess
import json
import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
import logging
from config import WorkerConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

config = WorkerConfig()

def claim_job():
    """Claim next available job from queue"""
    try:
        response = requests.post(
            f'{config.API_URL}/api/jobs/claim',
            json={'worker_id': config.WORKER_ID},
            timeout=30
        )
        
        if response.status_code == 404:
            logger.info("No jobs available")
            return None
        
        if response.status_code != 200:
            logger.error(f"Error claiming job: {response.text}")
            return None
        
        job = response.json()
        logger.info(f"Claimed job {job['job_id']}: {job['video_id']} - {job['title']}")
        return job
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None

def download_video(youtube_url, video_id):
    """Download video using yt-dlp"""
    downloads_dir = Path(config.DOWNLOADS_DIR)
    downloads_dir.mkdir(exist_ok=True)
    
    output_path = downloads_dir / f'{video_id}.mp4'
    
    # Check if already downloaded
    if output_path.exists():
        logger.info(f"Video {video_id} already downloaded")
        return output_path
    
    logger.info(f"Downloading video {video_id} from {youtube_url}")
    
    cmd = [
        'yt-dlp',
        '-f', config.VIDEO_QUALITY,
        '-o', str(output_path),
        '--no-playlist',
        '--no-warnings',
        youtube_url
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            check=True,
            timeout=config.DOWNLOAD_TIMEOUT,
            capture_output=True,
            text=True
        )
        
        if not output_path.exists():
            raise Exception("Download completed but file not found")
        
        logger.info(f"Downloaded {video_id}: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise Exception(f"Download timeout after {config.DOWNLOAD_TIMEOUT}s")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Download failed: {e.stderr}")

def process_video(video_id):
    """Run Docker pipeline on video"""
    logger.info(f"Processing video {video_id}")
    
    cmd = [
        './run_docker.sh',
        'run',
        video_id,
        '--preset', config.SYNC_PRESET,
        '--transcription-model', config.TRANSCRIPTION_MODEL
    ]
    
    if config.FILTER_FACES:
        cmd.append('--filter-faces')
    
    try:
        result = subprocess.run(
            cmd,
            cwd=config.PIPELINE_DIR,
            check=True,
            timeout=config.PROCESSING_TIMEOUT,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Processing completed for {video_id}")
        return True
        
    except subprocess.TimeoutExpired:
        raise Exception(f"Processing timeout after {config.PROCESSING_TIMEOUT}s")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Processing failed: {e.stderr}")

def collect_results(video_id):
    """Collect processing results and metadata"""
    experiment_dir = Path(config.PIPELINE_DIR) / 'experiments' / 'experiment_data' / video_id
    
    if not experiment_dir.exists():
        raise Exception(f"Results directory not found: {experiment_dir}")
    
    # Load metadata
    metadata_path = experiment_dir / 'metadata.json'
    if not metadata_path.exists():
        raise Exception(f"Metadata file not found: {metadata_path}")
    
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    results = {
        'chunks_created': metadata.get('total_chunks_before_filtering', 0),
        'chunks_passed_sync': metadata.get('chunks_after_filtering', 0),
        'avg_sync_score': metadata.get('statistics', {}).get('average_sync_score', 0.0),
        'avg_face_presence': metadata.get('statistics', {}).get('average_face_presence', 0.0),
        'total_duration_seconds': metadata.get('statistics', {}).get('total_duration_seconds', 0.0),
        'storage_path': '',  # Will be set after upload
        'metadata_json': metadata
    }
    
    logger.info(f"Results: {results['chunks_created']} created, {results['chunks_passed_sync']} passed")
    return results, experiment_dir

def upload_to_storage(video_id, local_path):
    """Upload results to shared storage"""
    storage_base = Path(config.STORAGE_BASE)
    storage_base.mkdir(exist_ok=True, parents=True)
    
    remote_path = storage_base / video_id
    
    logger.info(f"Uploading {video_id} to {remote_path}")
    
    try:
        # Use rsync for efficient transfer
        cmd = [
            'rsync',
            '-av',
            '--progress',
            str(local_path) + '/',
            str(remote_path) + '/'
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Verify upload
        if not remote_path.exists():
            raise Exception("Upload verification failed")
        
        logger.info(f"Upload complete: {remote_path}")
        return str(remote_path)
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Upload failed: {e}")

def report_completion(job_id, results):
    """Report job completion to API"""
    try:
        response = requests.post(
            f'{config.API_URL}/api/jobs/{job_id}/complete',
            json=results,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text}")
        
        logger.info(f"Job {job_id} reported as complete")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to report completion: {e}")
        return False

def report_failure(job_id, error_message):
    """Report job failure to API"""
    try:
        response = requests.post(
            f'{config.API_URL}/api/jobs/{job_id}/fail',
            json={'error_message': error_message},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Job {job_id} reported as failed")
        else:
            logger.error(f"Failed to report failure: {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to report failure: {e}")

def cleanup_local_files(video_id):
    """Clean up local files after processing"""
    try:
        # Remove downloaded video
        downloads_dir = Path(config.DOWNLOADS_DIR)
        video_file = downloads_dir / f'{video_id}.mp4'
        if video_file.exists():
            video_file.unlink()
            logger.info(f"Removed downloaded video: {video_file}")
        
        # Remove outputs (keep experiments for now)
        outputs_dir = Path(config.PIPELINE_DIR) / 'outputs' / video_id
        if outputs_dir.exists():
            shutil.rmtree(outputs_dir)
            logger.info(f"Removed outputs: {outputs_dir}")
            
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

def process_single_job():
    """Process a single job from start to finish"""
    job = claim_job()
    if not job:
        return False
    
    job_id = job['job_id']
    video_id = job['video_id']
    youtube_url = job['youtube_url']
    
    logger.info(f"Starting job {job_id}: {video_id}")
    logger.info(f"  Title: {job['title']}")
    logger.info(f"  Speaker: {job['speaker_name']} ({job['speaker_id']})")
    logger.info(f"  Domain: {job['domain']}")
    
    try:
        # Step 1: Download video
        logger.info("Step 1/4: Downloading video...")
        download_video(youtube_url, video_id)
        
        # Step 2: Process video
        logger.info("Step 2/4: Processing video...")
        process_video(video_id)
        
        # Step 3: Collect results
        logger.info("Step 3/4: Collecting results...")
        results, local_path = collect_results(video_id)
        
        # Step 4: Upload to storage
        logger.info("Step 4/4: Uploading to storage...")
        storage_path = upload_to_storage(video_id, local_path)
        results['storage_path'] = storage_path
        
        # Report completion
        logger.info("Reporting completion to API...")
        report_completion(job_id, results)
        
        # Cleanup
        logger.info("Cleaning up local files...")
        cleanup_local_files(video_id)
        
        logger.info(f"✓ Job {job_id} completed successfully!")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ Job {job_id} failed: {error_msg}")
        report_failure(job_id, error_msg)
        
        # Cleanup on failure too
        cleanup_local_files(video_id)
        return False

def main():
    """Main worker loop"""
    logger.info("="*60)
    logger.info(f"Worker {config.WORKER_ID} starting...")
    logger.info(f"API: {config.API_URL}")
    logger.info(f"Pipeline: {config.PIPELINE_DIR}")
    logger.info(f"Storage: {config.STORAGE_BASE}")
    logger.info("="*60)
    
    # Check dependencies
    dependencies = ['yt-dlp', 'rsync', 'docker']
    missing = []
    for dep in dependencies:
        if shutil.which(dep) is None:
            missing.append(dep)
    
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Install with: sudo apt-get install yt-dlp rsync docker.io")
        sys.exit(1)
    
    # Process one job
    success = process_single_job()
    
    if success:
        logger.info("Job processing complete")
        sys.exit(0)
    else:
        logger.error("Job processing failed")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)