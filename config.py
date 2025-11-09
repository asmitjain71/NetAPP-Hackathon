"""
Configuration file for the Intelligent Data Management System
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Storage Tier Configurations
STORAGE_TIERS = {
    'hot': {
        'name': 'Hot Storage',
        'type': 'on-premise',
        'cost_per_gb': 0.023,  # $0.023 per GB/month
        'latency_ms': 5,
        'capacity_gb': 10000
    },
    'warm': {
        'name': 'Warm Storage',
        'type': 'private-cloud',
        'cost_per_gb': 0.012,  # $0.012 per GB/month
        'latency_ms': 50,
        'capacity_gb': 50000
    },
    'cold': {
        'name': 'Cold Storage',
        'type': 'public-cloud',
        'cost_per_gb': 0.004,  # $0.004 per GB/month
        'latency_ms': 200,
        'capacity_gb': 100000
    }
}

# Cloud Provider Configurations
CLOUD_PROVIDERS = {
    'aws': {
        'name': 'AWS S3',
        'regions': ['us-east-1', 'us-west-2', 'eu-west-1'],
        'cost_per_gb': 0.023,
        'api_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'api_secret': os.getenv('AWS_SECRET_ACCESS_KEY', '')
    },
    'azure': {
        'name': 'Azure Blob Storage',
        'regions': ['eastus', 'westus2', 'westeurope'],
        'cost_per_gb': 0.018,
        'connection_string': os.getenv('AZURE_CONNECTION_STRING', '')
    },
    'gcp': {
        'name': 'Google Cloud Storage',
        'regions': ['us-central1', 'us-east1', 'europe-west1'],
        'cost_per_gb': 0.020,
        'credentials': os.getenv('GCP_CREDENTIALS_PATH', '')
    }
}

# Streaming Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = 'data/stream'

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data_management.db')

# ML Model Configuration
ML_MODEL_PATH = 'models/data_usage_predictor.pkl'
ML_RETRAIN_INTERVAL_HOURS = 24

# Migration Configuration
MIGRATION_BATCH_SIZE = 100  # MB
MIGRATION_MAX_CONCURRENT = 5
MIGRATION_RETRY_ATTEMPTS = 3

# Access Pattern Thresholds
ACCESS_THRESHOLDS = {
    'hot': {'accesses_per_day': 100, 'last_access_hours': 24},
    'warm': {'accesses_per_day': 10, 'last_access_hours': 168},  # 7 days
    'cold': {'accesses_per_day': 1, 'last_access_hours': 720}   # 30 days
}

# API Configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'


