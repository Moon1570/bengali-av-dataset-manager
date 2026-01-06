"""
Worker configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class WorkerConfig:
    # Worker identity
    WORKER_ID = os.getenv('WORKER_ID', 'worker_unknown')
    
    # API connection
    API_URL = os.getenv('API_URL', 'http://localhost:5000')
    
    # Paths
    PIPELINE_DIR = os.getenv('PIPELINE_DIR', '/path/to/bengali-pipeline')
    DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './downloads')
    STORAGE_BASE = os.getenv('STORAGE_BASE', '/mnt/dataset_storage')
    
    # Processing settings
    SYNC_PRESET = os.getenv('SYNC_PRESET', 'medium')
    FILTER_FACES = os.getenv('FILTER_FACES', 'true').lower() == 'true'
    TRANSCRIPTION_MODEL = os.getenv('TRANSCRIPTION_MODEL', 'google')
    
    # Video download settings
    VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', 'bestvideo[height<=720]+bestaudio/best[height<=720]')
    
    # Timeouts
    DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', '600'))  # 10 minutes
    PROCESSING_TIMEOUT = int(os.getenv('PROCESSING_TIMEOUT', '3600'))  # 1 hour
    
    # Retry settings
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '60'))  # seconds