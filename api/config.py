"""
Configuration for API server
"""
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

class Config:
    # Check if DATABASE_URL is provided (for Render or other cloud providers)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        # Parse DATABASE_URL
        parsed = urlparse(DATABASE_URL)
        DB_HOST = parsed.hostname
        DB_NAME = parsed.path[1:]  # Remove leading /
        DB_USER = parsed.username
        DB_PASSWORD = parsed.password
        DB_PORT = parsed.port or 5432
    else:
        # Fallback to individual environment variables
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_NAME = os.getenv('DB_NAME', 'av_bn_dataset')
        DB_USER = os.getenv('DB_USER', 'dataset_admin')
        DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme123')
        DB_PORT = int(os.getenv('DB_PORT', '5432'))
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '5000'))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Job settings
    MAX_RETRY_COUNT = int(os.getenv('MAX_RETRY_COUNT', '3'))
    JOB_TIMEOUT_HOURS = int(os.getenv('JOB_TIMEOUT_HOURS', '2'))