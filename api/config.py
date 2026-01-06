"""
Configuration for API server
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'av_bn_dataset')
    DB_USER = os.getenv('DB_USER', 'dataset_admin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme123')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '5000'))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Job settings
    MAX_RETRY_COUNT = int(os.getenv('MAX_RETRY_COUNT', '3'))
    JOB_TIMEOUT_HOURS = int(os.getenv('JOB_TIMEOUT_HOURS', '2'))
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"