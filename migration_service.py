"""
Multi-Cloud Data Migration Service
Handles data migration and synchronization across storage tiers and cloud providers
"""
import time
import threading
from datetime import datetime
from sqlalchemy import and_
from models import DataObject, Migration, SessionLocal
from config import STORAGE_TIERS, CLOUD_PROVIDERS, MIGRATION_BATCH_SIZE, MIGRATION_MAX_CONCURRENT, MIGRATION_RETRY_ATTEMPTS
import json

class MigrationService:
    """Service for managing data migrations across storage tiers"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.active_migrations = {}
        self.migration_lock = threading.Lock()
    
    def create_migration(self, data_object_id, target_tier, target_location=None, target_provider=None):
        """Create a new migration task"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return None
        
        # Check if migration already in progress
        existing = self.db.query(Migration).filter(
            and_(
                Migration.data_object_id == data_object_id,
                Migration.status.in_(['pending', 'in_progress'])
            )
        ).first()
        
        if existing:
            return existing.to_dict()
        
        # Determine target location if not specified
        if not target_location:
            target_location = self._determine_target_location(target_tier, target_provider)
        
        # Create migration record
        migration = Migration(
            data_object_id=data_object_id,
            source_tier=data_object.current_tier,
            target_tier=target_tier,
            source_location=data_object.current_location,
            target_location=target_location,
            total_bytes=int(data_object.size_gb * 1024 * 1024 * 1024),  # Convert GB to bytes
            status='pending'
        )
        
        self.db.add(migration)
        self.db.commit()
        self.db.refresh(migration)
        
        return migration.to_dict()
    
    def _determine_target_location(self, tier, provider=None):
        """Determine target location based on tier and provider"""
        tier_config = STORAGE_TIERS.get(tier, {})
        
        if provider and provider in CLOUD_PROVIDERS:
            provider_config = CLOUD_PROVIDERS[provider]
            return f"{provider_config['name']} - {provider_config['regions'][0]}"
        
        tier_type = tier_config.get('type', 'public-cloud')
        
        if tier_type == 'on-premise':
            return 'On-Premise Data Center'
        elif tier_type == 'private-cloud':
            return 'Private Cloud Infrastructure'
        else:
            # Default to AWS for public cloud
            return f"{CLOUD_PROVIDERS['aws']['name']} - {CLOUD_PROVIDERS['aws']['regions'][0]}"
    
    def execute_migration(self, migration_id, simulate=True):
        """Execute a migration (simulated or real)"""
        migration = self.db.query(Migration).filter(
            Migration.id == migration_id
        ).first()
        
        if not migration:
            return None
        
        if migration.status != 'pending':
            return migration.to_dict()
        
        # Check concurrent migration limit
        active_count = self.db.query(Migration).filter(
            Migration.status == 'in_progress'
        ).count()
        
        if active_count >= MIGRATION_MAX_CONCURRENT:
            return {'error': 'Maximum concurrent migrations reached'}
        
        # Start migration in background thread
        thread = threading.Thread(
            target=self._migrate_data,
            args=(migration_id, simulate),
            daemon=True
        )
        thread.start()
        
        return migration.to_dict()
    
    def _migrate_data(self, migration_id, simulate=True):
        """Internal method to perform the actual migration"""
        with self.migration_lock:
            migration = self.db.query(Migration).filter(
                Migration.id == migration_id
            ).first()
            
            if not migration:
                return
            
            migration.status = 'in_progress'
            self.db.commit()
            
            data_object = self.db.query(DataObject).filter(
                DataObject.id == migration.data_object_id
            ).first()
            
            if not data_object:
                migration.status = 'failed'
                migration.error_message = 'Data object not found'
                self.db.commit()
                return
        
        try:
            # Simulate migration progress
            total_bytes = migration.total_bytes
            bytes_transferred = 0
            batch_size = MIGRATION_BATCH_SIZE * 1024 * 1024  # Convert MB to bytes
            
            # Simulate transfer in chunks
            while bytes_transferred < total_bytes:
                if simulate:
                    # Simulate network transfer delay
                    time.sleep(0.1)  # 100ms per batch
                    bytes_transferred = min(bytes_transferred + batch_size, total_bytes)
                else:
                    # Real migration would call cloud APIs here
                    # Example: boto3 for AWS, azure-storage-blob for Azure
                    bytes_transferred = min(bytes_transferred + batch_size, total_bytes)
                
                # Update progress
                migration.bytes_transferred = bytes_transferred
                self.db.commit()
            
            # Migration complete - update data object
            data_object.current_tier = migration.target_tier
            data_object.current_location = migration.target_location
            
            # Update cost
            tier_config = STORAGE_TIERS.get(migration.target_tier, {})
            data_object.monthly_cost = tier_config.get('cost_per_gb', 0) * data_object.size_gb
            
            # Update migration status
            migration.status = 'completed'
            migration.completed_at = datetime.utcnow()
            migration.bytes_transferred = total_bytes
            
            self.db.commit()
            
        except Exception as e:
            migration.status = 'failed'
            migration.error_message = str(e)
            self.db.commit()
    
    def get_migration_status(self, migration_id):
        """Get status of a migration"""
        migration = self.db.query(Migration).filter(
            Migration.id == migration_id
        ).first()
        
        if not migration:
            return None
        
        return migration.to_dict()
    
    def get_active_migrations(self):
        """Get all active migrations"""
        migrations = self.db.query(Migration).filter(
            Migration.status.in_(['pending', 'in_progress'])
        ).order_by(Migration.started_at.desc()).all()
        
        return [m.to_dict() for m in migrations]
    
    def get_migration_history(self, data_object_id=None, limit=50):
        """Get migration history"""
        query = self.db.query(Migration)
        
        if data_object_id:
            query = query.filter(Migration.data_object_id == data_object_id)
        
        migrations = query.order_by(Migration.started_at.desc()).limit(limit).all()
        
        return [m.to_dict() for m in migrations]
    
    def retry_failed_migration(self, migration_id):
        """Retry a failed migration"""
        migration = self.db.query(Migration).filter(
            Migration.id == migration_id
        ).first()
        
        if not migration or migration.status != 'failed':
            return None
        
        # Reset migration
        migration.status = 'pending'
        migration.bytes_transferred = 0
        migration.error_message = None
        self.db.commit()
        
        # Execute again
        return self.execute_migration(migration_id)
    
    def sync_data(self, source_object_id, target_object_id):
        """Synchronize data between two objects (for multi-cloud sync)"""
        source = self.db.query(DataObject).filter(
            DataObject.id == source_object_id
        ).first()
        
        target = self.db.query(DataObject).filter(
            DataObject.id == target_object_id
        ).first()
        
        if not source or not target:
            return {'error': 'Source or target object not found'}
        
        # In a real implementation, this would:
        # 1. Compare checksums/hashes
        # 2. Transfer differences only
        # 3. Update metadata
        # 4. Handle conflicts
        
        return {
            'status': 'sync_initiated',
            'source_id': source_object_id,
            'target_id': target_object_id,
            'message': 'Synchronization initiated (simulated)'
        }
    
    def handle_network_failure(self, migration_id):
        """Handle network failure during migration"""
        migration = self.db.query(Migration).filter(
            Migration.id == migration_id
        ).first()
        
        if not migration:
            return None
        
        # Mark as failed with retry capability
        migration.status = 'failed'
        migration.error_message = 'Network failure detected'
        self.db.commit()
        
        # Auto-retry logic could be implemented here
        return migration.to_dict()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


