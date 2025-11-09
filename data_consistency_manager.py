"""
Data Consistency and Availability Manager
Handles synchronization and conflict resolution across distributed environments
"""
import hashlib
import json
from datetime import datetime, timedelta
from sqlalchemy import and_
from models import DataObject, Migration, SessionLocal
from config import STORAGE_TIERS
import threading

class DataConsistencyManager:
    """Manages data consistency and availability across distributed storage"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.sync_lock = threading.Lock()
        self.replication_status = {}
    
    def calculate_checksum(self, data_object_id):
        """Calculate checksum for a data object (simulated)"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return None
        
        # In real implementation, this would calculate actual file checksum
        # For simulation, we use object metadata
        content = f"{data_object.id}_{data_object.name}_{data_object.size_gb}_{data_object.last_accessed}"
        checksum = hashlib.md5(content.encode()).hexdigest()
        
        return checksum
    
    def verify_consistency(self, data_object_id, locations=None):
        """Verify data consistency across multiple locations"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        # Calculate primary checksum
        primary_checksum = self.calculate_checksum(data_object_id)
        
        # In real implementation, would compare checksums from all locations
        # For simulation, we assume consistency if no recent migrations
        recent_migrations = self.db.query(Migration).filter(
            and_(
                Migration.data_object_id == data_object_id,
                Migration.status == 'in_progress',
                Migration.started_at >= datetime.utcnow() - timedelta(hours=1)
            )
        ).count()
        
        is_consistent = recent_migrations == 0
        
        return {
            'data_object_id': data_object_id,
            'checksum': primary_checksum,
            'is_consistent': is_consistent,
            'locations_checked': locations or [data_object.current_location],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_conflict(self, data_object_id, conflicting_versions):
        """Handle data conflicts between versions"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        # Conflict resolution strategies:
        # 1. Last-write-wins (default)
        # 2. Version-based
        # 3. Manual resolution
        
        strategy = 'last_write_wins'
        
        if strategy == 'last_write_wins':
            # Use most recent version
            latest_version = max(conflicting_versions, key=lambda v: v.get('timestamp', ''))
            resolved_version = latest_version
        else:
            # Other strategies would be implemented here
            resolved_version = conflicting_versions[0]
        
        return {
            'data_object_id': data_object_id,
            'conflict_resolved': True,
            'strategy': strategy,
            'resolved_version': resolved_version,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def replicate_data(self, data_object_id, target_locations):
        """Replicate data to multiple locations for availability"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        replication_tasks = []
        
        for location in target_locations:
            # Create replication task (simulated)
            task = {
                'data_object_id': data_object_id,
                'source_location': data_object.current_location,
                'target_location': location,
                'status': 'pending',
                'started_at': datetime.utcnow().isoformat()
            }
            
            replication_tasks.append(task)
            
            # Update replication status
            key = f"{data_object_id}_{location}"
            self.replication_status[key] = {
                'status': 'in_progress',
                'started_at': datetime.utcnow(),
                'progress': 0
            }
        
        return {
            'data_object_id': data_object_id,
            'replication_tasks': replication_tasks,
            'total_locations': len(target_locations) + 1  # +1 for primary
        }
    
    def handle_network_failure(self, data_object_id, failed_location):
        """Handle network failure for a specific location"""
        # Mark location as unavailable
        key = f"{data_object_id}_{failed_location}"
        if key in self.replication_status:
            self.replication_status[key]['status'] = 'failed'
            self.replication_status[key]['error'] = 'Network failure'
        
        # Check if data is available in other locations
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        # In real implementation, would check other replicas
        is_available = data_object.current_location != failed_location
        
        return {
            'data_object_id': data_object_id,
            'failed_location': failed_location,
            'is_available': is_available,
            'fallback_location': data_object.current_location if is_available else None,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def ensure_availability(self, data_object_id, min_replicas=2):
        """Ensure minimum number of replicas for availability"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        # Count current replicas
        current_replicas = 1  # Primary location
        
        # Check replication status
        for key, status in self.replication_status.items():
            if key.startswith(f"{data_object_id}_") and status['status'] == 'completed':
                current_replicas += 1
        
        if current_replicas < min_replicas:
            # Create additional replicas
            additional_needed = min_replicas - current_replicas
            target_locations = [
                f"Replica-{i+1}" for i in range(additional_needed)
            ]
            
            return self.replicate_data(data_object_id, target_locations)
        
        return {
            'data_object_id': data_object_id,
            'current_replicas': current_replicas,
            'min_replicas': min_replicas,
            'status': 'sufficient'
        }
    
    def sync_across_environments(self, data_object_id, environments):
        """Synchronize data across multiple cloud environments"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return {'error': 'Data object not found'}
        
        sync_results = []
        
        for env in environments:
            # Simulate sync operation
            sync_result = {
                'environment': env,
                'status': 'synced',
                'timestamp': datetime.utcnow().isoformat(),
                'checksum': self.calculate_checksum(data_object_id)
            }
            sync_results.append(sync_result)
        
        return {
            'data_object_id': data_object_id,
            'sync_results': sync_results,
            'total_environments': len(environments)
        }
    
    def get_consistency_status(self, data_object_id):
        """Get consistency status for a data object"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return None
        
        checksum = self.calculate_checksum(data_object_id)
        
        # Check for active migrations
        active_migrations = self.db.query(Migration).filter(
            and_(
                Migration.data_object_id == data_object_id,
                Migration.status.in_(['pending', 'in_progress'])
            )
        ).count()
        
        is_consistent = active_migrations == 0
        
        return {
            'data_object_id': data_object_id,
            'checksum': checksum,
            'is_consistent': is_consistent,
            'active_migrations': active_migrations,
            'current_location': data_object.current_location,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

