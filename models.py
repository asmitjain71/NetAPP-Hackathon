"""
Database models for the Intelligent Data Management System
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class DataObject(Base):
    """Represents a data object in the system"""
    __tablename__ = 'data_objects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    size_gb = Column(Float, nullable=False)
    current_tier = Column(String(50), nullable=False)  # hot, warm, cold
    current_location = Column(String(255), nullable=False)  # on-premise, private-cloud, public-cloud
    cloud_provider = Column(String(50))  # aws, azure, gcp, on-premise
    region = Column(String(100))
    
    # Access metrics
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    first_created = Column(DateTime, default=datetime.utcnow)
    
    # Cost tracking
    monthly_cost = Column(Float, default=0.0)
    
    # Metadata
    content_type = Column(String(100))
    tags = Column(Text)  # JSON string
    encrypted = Column(Boolean, default=False)
    
    # Relationships
    access_logs = relationship("AccessLog", back_populates="data_object", cascade="all, delete-orphan")
    migrations = relationship("Migration", back_populates="data_object", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'size_gb': self.size_gb,
            'current_tier': self.current_tier,
            'current_location': self.current_location,
            'cloud_provider': self.cloud_provider,
            'region': self.region,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'first_created': self.first_created.isoformat() if self.first_created else None,
            'monthly_cost': self.monthly_cost,
            'content_type': self.content_type,
            'encrypted': self.encrypted
        }

class AccessLog(Base):
    """Tracks access patterns for data objects"""
    __tablename__ = 'access_logs'
    
    id = Column(Integer, primary_key=True)
    data_object_id = Column(Integer, ForeignKey('data_objects.id'), nullable=False)
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_type = Column(String(50))  # read, write, delete
    latency_ms = Column(Float)
    source_ip = Column(String(50))
    
    data_object = relationship("DataObject", back_populates="access_logs")
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_object_id': self.data_object_id,
            'accessed_at': self.accessed_at.isoformat(),
            'access_type': self.access_type,
            'latency_ms': self.latency_ms,
            'source_ip': self.source_ip
        }

class Migration(Base):
    """Tracks data migrations between storage tiers"""
    __tablename__ = 'migrations'
    
    id = Column(Integer, primary_key=True)
    data_object_id = Column(Integer, ForeignKey('data_objects.id'), nullable=False)
    source_tier = Column(String(50), nullable=False)
    target_tier = Column(String(50), nullable=False)
    source_location = Column(String(255), nullable=False)
    target_location = Column(String(255), nullable=False)
    
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    bytes_transferred = Column(Integer, default=0)
    total_bytes = Column(Integer, nullable=False)
    error_message = Column(Text)
    
    data_object = relationship("DataObject", back_populates="migrations")
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_object_id': self.data_object_id,
            'source_tier': self.source_tier,
            'target_tier': self.target_tier,
            'source_location': self.source_location,
            'target_location': self.target_location,
            'status': self.status,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'bytes_transferred': self.bytes_transferred,
            'total_bytes': self.total_bytes,
            'progress_percent': (self.bytes_transferred / self.total_bytes * 100) if self.total_bytes > 0 else 0,
            'error_message': self.error_message
        }

class StreamingEvent(Base):
    """Stores real-time streaming events"""
    __tablename__ = 'streaming_events'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)  # data_ingestion, access_pattern, alert
    data_object_id = Column(Integer, ForeignKey('data_objects.id'))
    payload = Column(Text)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'data_object_id': self.data_object_id,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'processed': self.processed
        }

class MLPrediction(Base):
    """Stores ML predictions for data placement"""
    __tablename__ = 'ml_predictions'
    
    id = Column(Integer, primary_key=True)
    data_object_id = Column(Integer, ForeignKey('data_objects.id'), nullable=False)
    predicted_tier = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    predicted_at = Column(DateTime, default=datetime.utcnow)
    reasoning = Column(Text)  # Explanation of prediction
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_object_id': self.data_object_id,
            'predicted_tier': self.predicted_tier,
            'confidence_score': self.confidence_score,
            'predicted_at': self.predicted_at.isoformat(),
            'reasoning': self.reasoning
        }

# Database setup
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database with all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


