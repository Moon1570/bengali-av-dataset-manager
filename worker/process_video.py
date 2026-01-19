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
STORAGE_BASE = os.getenv('STORAGE_BASE', './data/storage')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './data/downloads')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', './data/outputs')
DOCKER_IMAGE = os.getenv('DOCKER_IMAGE', 'bengali-pipeline:latest')

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
    # Resolve downloads directory relative to project root
    script_dir = Path(__file__).parent.parent
    downloads_dir = (script_dir / DOWNLOADS_DIR).resolve()
    downloads_dir.mkdir(exist_ok=True, parents=True)
    
    output_path = downloads_dir / f'{video_id}.mp4'
    
    # Check if already downloaded (with any extension)
    existing_files = list(downloads_dir.glob(f'{video_id}.*'))
    if existing_files:
        logger.info(f"Video already downloaded: {existing_files[0]}")
        return existing_files[0]
    
    logger.info(f"Downloading video: {video_id}")
    
    # Use yt-dlp from virtual environment
    venv_yt_dlp = script_dir / '.venv' / 'bin' / 'yt-dlp'
    
    # Use output template without extension - let yt-dlp add the correct one
    output_template = downloads_dir / f'{video_id}.%(ext)s'
    
    cmd = [
        str(venv_yt_dlp),
        '-f', 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
        '-o', str(output_template),
        '--merge-output-format', 'mp4',
        '--no-playlist',
        youtube_url
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        
        # Find the downloaded file (could have different extension)
        downloaded_files = list(downloads_dir.glob(f'{video_id}.*'))
        if not downloaded_files:
            raise Exception(f"Download completed but file not found: {output_path}")
        
        actual_path = downloaded_files[0]
        logger.info(f"Downloaded: {actual_path}")
        
        # If it's not .mp4, rename it
        if actual_path.suffix != '.mp4':
            final_path = downloads_dir / f'{video_id}.mp4'
            actual_path.rename(final_path)
            logger.info(f"Renamed to: {final_path}")
            return final_path
        
        return actual_path
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def process_video(video_id, preset='balanced', transcription_model='google'):
    """Run Docker pipeline with volume mounts"""
    logger.info(f"Processing video {video_id} with preset: {preset}, transcription_model: {transcription_model}")
    
    # Resolve paths relative to project root
    script_dir = Path(__file__).parent.parent
    downloads_dir = (script_dir / DOWNLOADS_DIR).resolve()
    outputs_dir = (script_dir / OUTPUTS_DIR).resolve()
    
    # Ensure directories exist
    downloads_dir.mkdir(exist_ok=True, parents=True)
    outputs_dir.mkdir(exist_ok=True, parents=True)
    
    # Check if video exists
    source_video = downloads_dir / f'{video_id}.mp4'
    if not source_video.exists():
        raise Exception(f"Video not found: {source_video}")
    
    logger.info(f"Downloads directory: {downloads_dir}")
    logger.info(f"Outputs directory: {outputs_dir}")
    
    # Remove video from processed cache to force reprocessing
    processed_json_path = outputs_dir / 'processed.json'
    if processed_json_path.exists():
        try:
            with open(processed_json_path, 'r') as f:
                processed_data = json.load(f)
            
            if video_id in processed_data:
                logger.info(f"Removing {video_id} from processed cache to force reprocessing")
                del processed_data[video_id]
                
                with open(processed_json_path, 'w') as f:
                    json.dump(processed_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not update processed cache: {e}")
    
    # Map preset to pipeline parameters
    preset_params = {
        'strict': ['--preset', 'high'],
        'balanced': ['--preset', 'medium'],
        'lenient': ['--preset', 'low', '--no-filter-faces', '--no-refine-chunks']
    }
    
    # Build Docker command with volume mounts
    # The complete_pipeline.sh requires: VIDEO_ID --syncnet-repo PATH [options]
    cmd = [
        'docker', 'run',
        '--rm',  # Remove container after completion
        '-v', f'{downloads_dir}:/app/bengali-pipeline/downloads',
        '-v', f'{outputs_dir}:/app/bengali-pipeline/outputs',
        DOCKER_IMAGE,
        '/app/bengali-pipeline/complete_pipeline.sh',
        video_id,
        '--syncnet-repo', '/app/syncnet_python',
        '--current-repo', '/app/bengali-pipeline'
    ] + preset_params.get(preset, preset_params['balanced']) + [
        '--transcription-model', transcription_model
    ]
    
    logger.info(f"Running Docker command: {' '.join(cmd)}")
    
    try:
        # Stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream and log output
        logger.info("🐳 Docker container started, streaming logs...")
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.info(f"[Docker] {line}")
        
        # Wait for completion
        return_code = process.wait(timeout=10800)
        
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
        
        logger.info(f"✅ Processing completed for {video_id}")
        return True
    except subprocess.TimeoutExpired:
        raise Exception("Processing timeout after 3 hours")
    except subprocess.CalledProcessError as e:
        error_msg = f"Exit code {e.returncode}"
        if e.stdout:
            logger.error(f"Pipeline stdout: {e.stdout}")
            error_msg += f"\nStdout: {e.stdout}"
        if e.stderr:
            logger.error(f"Pipeline stderr: {e.stderr}")
            error_msg += f"\nStderr: {e.stderr}"
        raise Exception(f"Processing failed: {error_msg}")
    except OSError as e:
        raise Exception(f"OS Error: {e}")

def collect_results(video_id):
    """Collect processing results"""
    script_dir = Path(__file__).parent.parent
    outputs_dir = (script_dir / OUTPUTS_DIR).resolve()
    
    # Try multiple possible locations for experiment data
    possible_paths = [
        outputs_dir / video_id / video_id,  # Organized structure
        outputs_dir / video_id,
    ]
    
    experiment_dir = None
    for path in possible_paths:
        if path.exists():
            experiment_dir = path
            logger.info(f"Found results at: {experiment_dir}")
            break
    
    if not experiment_dir:
        logger.error(f"Results not found in any expected location:")
        for path in possible_paths:
            logger.error(f"  - {path}: {'EXISTS' if path.exists() else 'NOT FOUND'}")
        
        if outputs_dir.exists():
            logger.info(f"Contents of {outputs_dir}:")
            for item in outputs_dir.iterdir():
                if video_id in str(item):
                    logger.info(f"  Found: {item}")
        
        raise Exception(f"Results not found for {video_id}. Checked: {', '.join(str(p) for p in possible_paths)}")
    
    # Cleanup: Remove google_summary.txt files
    logger.info("Cleaning up summary files...")
    for transcription_dir in experiment_dir.glob('*_transcription'):
        for summary_file in transcription_dir.glob('*_google_summary.txt'):
            logger.info(f"Removing summary file: {summary_file.name}")
            summary_file.unlink()
    
    # Verify consistent file counts across directories
    logger.info("Verifying file consistency across directories...")
    dirs_to_check = {
        'video_normal': experiment_dir / 'video_normal',
        'video_cropped': experiment_dir / 'video_cropped',
        'video_bbox': experiment_dir / 'video_bbox',
        'audio': experiment_dir / 'audio',
    }
    
    file_counts = {}
    for dir_name, dir_path in dirs_to_check.items():
        if dir_path.exists():
            if dir_name == 'video_bbox':
                # video_bbox has _with_bboxes.mp4 suffix
                count = len(list(dir_path.glob('*_with_bboxes.mp4')))
            elif dir_name == 'audio':
                count = len(list(dir_path.glob('*.wav')))
            else:
                count = len(list(dir_path.glob('*.mp4')))
            file_counts[dir_name] = count
            logger.info(f"   {dir_name}: {count} files")
    
    # Check if counts match
    if file_counts:
        expected_count = max(file_counts.values())
        mismatches = {k: v for k, v in file_counts.items() if v != expected_count}
        
        if mismatches:
            logger.warning(f"⚠️ File count mismatch detected!")
            logger.warning(f"   Expected: {expected_count} files in each directory")
            for dir_name, count in mismatches.items():
                logger.warning(f"   {dir_name}: {count} files (missing {expected_count - count})")
    
    # Calculate statistics from actual files
    logger.info("Calculating statistics from processed files...")
    
    # Count video chunks in video_normal directory
    video_normal_dir = experiment_dir / 'video_normal'
    video_chunks = list(video_normal_dir.glob('*.mp4')) if video_normal_dir.exists() else []
    chunks_passed = len(video_chunks)
    
    # Count original chunks from parent directory
    parent_chunks_dir = experiment_dir.parent / 'chunks' / 'video'
    original_chunks = list(parent_chunks_dir.glob('*.mp4')) if parent_chunks_dir.exists() else []
    chunks_created = len(original_chunks)
    
    # Calculate total duration from video files
    total_duration = 0.0
    try:
        import subprocess
        for video_file in video_chunks:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(video_file)],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                total_duration += float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not calculate duration: {e}")
    
    # Calculate file size
    file_size_mb = sum(f.stat().st_size for f in experiment_dir.rglob('*') if f.is_file()) / 1024 / 1024
    
    # Check for transcription files
    transcription_dirs = list(experiment_dir.glob('*_transcription'))
    has_transcription = len(transcription_dirs) > 0
    
    results = {
        'chunks_created': chunks_created,
        'chunks_passed_sync': chunks_passed,
        'chunks_manually_approved': 0,  # Will be updated by manual review
        'chunks_manually_rejected': 0,
        'avg_sync_score': 0.0,  # Not available without metadata
        'min_sync_score': 0.0,
        'max_sync_score': 0.0,
        'avg_face_presence': 0.0,
        'min_face_presence': 0.0,
        'max_face_presence': 0.0,
        'total_duration_seconds': total_duration,
        'usable_duration_seconds': total_duration,  # Same as total for now
        'storage_path': str(experiment_dir),
        'file_size_mb': round(file_size_mb, 2),
        'has_transcription': has_transcription
    }
    
    logger.info(f"✅ Statistics calculated:")
    logger.info(f"   - Original chunks: {chunks_created}")
    logger.info(f"   - Chunks passed SyncNet: {chunks_passed}")
    logger.info(f"   - Total duration: {total_duration:.1f}s")
    logger.info(f"   - File size: {file_size_mb:.2f} MB")
    logger.info(f"   - Has transcription: {has_transcription}")
    
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

def main(video_id, youtube_url, preset='balanced', transcription_model='google'):
    """Main processing function"""
    logger.info(f"Starting processing: {video_id}")
    
    try:
        # Step 1: Download
        logger.info("Step 1/4: Downloading video...")
        download_video(youtube_url, video_id)
        
        # Step 2: Process
        logger.info("Step 2/4: Processing with Docker pipeline...")
        process_video(video_id, preset, transcription_model)
        
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
        print("Usage: python process_video.py <video_id> <youtube_url> [preset] [transcription_model]")
        print("Presets: strict, balanced, lenient")
        print("Transcription models: google, whisper, both")
        sys.exit(1)
    
    video_id = sys.argv[1]
    youtube_url = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else 'balanced'
    transcription_model = sys.argv[4] if len(sys.argv) > 4 else 'google'
    
    try:
        results = main(video_id, youtube_url, preset, transcription_model)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)