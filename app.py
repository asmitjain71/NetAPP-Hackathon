"""
Main Flask Application for Intelligent Data Management System
Provides REST API and WebSocket support for real-time updates
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
from sqlalchemy import func
import json
import os
import threading

from models import init_db, DataObject, AccessLog, Migration, StreamingEvent, MLPrediction, SessionLocal
from data_placement_optimizer import DataPlacementOptimizer
from migration_service import MigrationService
from streaming_processor import StreamingProcessor
from ml_predictor import MLPredictor
from data_consistency_manager import DataConsistencyManager
from config import API_HOST, API_PORT, DEBUG

app = Flask(__name__)
app.config['SECRET_KEY'] = 'netapp-hackathon-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_db()

# Initialize services
optimizer = DataPlacementOptimizer()
migration_service = MigrationService()
streaming_processor = StreamingProcessor(use_kafka=False, use_mqtt=False)
ml_predictor = MLPredictor()
consistency_manager = DataConsistencyManager()

# Start streaming processor simulation
streaming_thread = None

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# Data Object Endpoints
@app.route('/api/data-objects', methods=['GET'])
def get_data_objects():
    """Get all data objects"""
    db = SessionLocal()
    try:
        objects = db.query(DataObject).all()
        return jsonify([obj.to_dict() for obj in objects])
    finally:
        db.close()

@app.route('/api/data-objects', methods=['POST'])
def create_data_object():
    """Create a new data object"""
    db = SessionLocal()
    try:
        data = request.json
        
        obj = DataObject(
            name=data.get('name', f'object_{datetime.utcnow().timestamp()}'),
            size_gb=data.get('size_gb', 1.0),
            current_tier=data.get('tier', 'warm'),
            current_location=data.get('location', 'On-Premise Data Center'),
            cloud_provider=data.get('cloud_provider'),
            region=data.get('region'),
            content_type=data.get('content_type'),
            encrypted=data.get('encrypted', False)
        )
        
        # Calculate initial cost
        from config import STORAGE_TIERS
        tier_config = STORAGE_TIERS.get(obj.current_tier, {})
        obj.monthly_cost = tier_config.get('cost_per_gb', 0) * obj.size_gb
        
        db.add(obj)
        db.commit()
        db.refresh(obj)
        
        # Emit event
        socketio.emit('data_object_created', obj.to_dict())
        
        return jsonify(obj.to_dict()), 201
    finally:
        db.close()

@app.route('/api/data-objects/<int:obj_id>', methods=['GET'])
def get_data_object(obj_id):
    """Get a specific data object"""
    db = SessionLocal()
    try:
        obj = db.query(DataObject).filter(DataObject.id == obj_id).first()
        if not obj:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(obj.to_dict())
    finally:
        db.close()

@app.route('/api/data-objects/<int:obj_id>/access', methods=['POST'])
def log_access(obj_id):
    """Log data access"""
    db = SessionLocal()
    try:
        obj = db.query(DataObject).filter(DataObject.id == obj_id).first()
        if not obj:
            return jsonify({'error': 'Not found'}), 404
        
        data = request.json
        access_log = AccessLog(
            data_object_id=obj_id,
            access_type=data.get('access_type', 'read'),
            latency_ms=data.get('latency_ms'),
            source_ip=data.get('source_ip', request.remote_addr)
        )
        
        db.add(access_log)
        
        # Update object metrics
        obj.access_count += 1
        obj.last_accessed = datetime.utcnow()
        
        db.commit()
        
        # Emit event
        socketio.emit('access_logged', access_log.to_dict())
        
        # Publish streaming event
        streaming_processor.publish_event('data-stream', {
            'type': 'access_event',
            'data_object_id': obj_id,
            'access_type': data.get('access_type', 'read'),
            'latency_ms': data.get('latency_ms'),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify(access_log.to_dict()), 201
    finally:
        db.close()

# Optimization Endpoints
@app.route('/api/optimize/<int:obj_id>', methods=['POST'])
def optimize_placement(obj_id):
    """Optimize placement for a data object"""
    result = optimizer.optimize_placement(obj_id)
    if not result:
        return jsonify({'error': 'Data object not found'}), 404
    
    # Emit event
    socketio.emit('optimization_complete', result)
    
    return jsonify(result)

@app.route('/api/optimize/batch', methods=['POST'])
def batch_optimize():
    """Batch optimize multiple data objects"""
    limit = request.json.get('limit', 100) if request.json else 100
    results = optimizer.batch_optimize(limit)
    return jsonify(results)

# Migration Endpoints
@app.route('/api/migrations', methods=['GET'])
def get_migrations():
    """Get all migrations"""
    status = request.args.get('status')
    if status:
        migrations = migration_service.get_active_migrations()
    else:
        migrations = migration_service.get_migration_history()
    return jsonify(migrations)

@app.route('/api/migrations', methods=['POST'])
def create_migration():
    """Create a new migration"""
    data = request.json
    obj_id = data.get('data_object_id')
    target_tier = data.get('target_tier')
    target_location = data.get('target_location')
    target_provider = data.get('target_provider')
    
    migration = migration_service.create_migration(
        obj_id, target_tier, target_location, target_provider
    )
    
    if not migration:
        return jsonify({'error': 'Failed to create migration'}), 400
    
    # Execute migration
    result = migration_service.execute_migration(migration['id'], simulate=True)
    
    # Emit event
    socketio.emit('migration_started', result)
    
    return jsonify(result), 201

@app.route('/api/migrations/<int:migration_id>', methods=['GET'])
def get_migration(migration_id):
    """Get migration status"""
    migration = migration_service.get_migration_status(migration_id)
    if not migration:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(migration)

@app.route('/api/migrations/<int:migration_id>/retry', methods=['POST'])
def retry_migration(migration_id):
    """Retry a failed migration"""
    result = migration_service.retry_failed_migration(migration_id)
    if not result:
        return jsonify({'error': 'Migration not found or not failed'}), 400
    return jsonify(result)

# ML Prediction Endpoints
@app.route('/api/predict/<int:obj_id>', methods=['POST'])
def predict_tier(obj_id):
    """Predict optimal tier using ML"""
    prediction = ml_predictor.predict_tier(obj_id)
    if not prediction:
        return jsonify({'error': 'Data object not found'}), 404
    
    # Emit event
    socketio.emit('prediction_complete', prediction)
    
    return jsonify(prediction)

@app.route('/api/predict/batch', methods=['POST'])
def batch_predict():
    """Batch predict tiers"""
    limit = request.json.get('limit', 100) if request.json else 100
    predictions = ml_predictor.batch_predict(limit)
    return jsonify(predictions)

@app.route('/api/ml/train', methods=['POST'])
def train_model():
    """Train the ML model"""
    ml_predictor.train_model()
    return jsonify({'status': 'training_complete'})

# Streaming Endpoints
@app.route('/api/streaming/start', methods=['POST'])
def start_streaming():
    """Start data streaming simulation"""
    global streaming_thread
    if streaming_thread and streaming_thread.is_alive():
        return jsonify({'error': 'Streaming already running'}), 400
    
    interval = request.json.get('interval', 5) if request.json else 5
    streaming_thread = threading.Thread(
        target=streaming_processor.simulate_data_stream,
        args=(interval,),
        daemon=True
    )
    streaming_thread.start()
    
    return jsonify({'status': 'streaming_started', 'interval': interval})

@app.route('/api/streaming/stop', methods=['POST'])
def stop_streaming():
    """Stop data streaming"""
    streaming_processor.stop()
    return jsonify({'status': 'streaming_stopped'})

@app.route('/api/streaming/events', methods=['GET'])
def get_streaming_events():
    """Get recent streaming events"""
    db = SessionLocal()
    try:
        limit = request.args.get('limit', 50, type=int)
        events = db.query(StreamingEvent).order_by(
            StreamingEvent.timestamp.desc()
        ).limit(limit).all()
        return jsonify([e.to_dict() for e in events])
    finally:
        db.close()

# Consistency Endpoints
@app.route('/api/consistency/<int:obj_id>', methods=['GET'])
def get_consistency(obj_id):
    """Get consistency status"""
    status = consistency_manager.get_consistency_status(obj_id)
    if not status:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(status)

@app.route('/api/consistency/<int:obj_id>/verify', methods=['POST'])
def verify_consistency(obj_id):
    """Verify data consistency"""
    locations = request.json.get('locations') if request.json else None
    result = consistency_manager.verify_consistency(obj_id, locations)
    return jsonify(result)

# Dashboard Statistics
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics"""
    db = SessionLocal()
    try:
        total_objects = db.query(DataObject).count()
        total_size = db.query(func.sum(DataObject.size_gb)).scalar() or 0
        total_cost = db.query(func.sum(DataObject.monthly_cost)).scalar() or 0
        
        tier_distribution = {}
        for tier in ['hot', 'warm', 'cold']:
            count = db.query(DataObject).filter(DataObject.current_tier == tier).count()
            tier_distribution[tier] = count
        
        active_migrations = db.query(Migration).filter(
            Migration.status.in_(['pending', 'in_progress'])
        ).count()
        
        recent_accesses = db.query(AccessLog).filter(
            AccessLog.accessed_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return jsonify({
            'total_objects': total_objects,
            'total_size_gb': round(total_size, 2),
            'total_monthly_cost': round(total_cost, 2),
            'tier_distribution': tier_distribution,
            'active_migrations': active_migrations,
            'recent_accesses_24h': recent_accesses
        })
    finally:
        db.close()

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'message': 'Connected to data management system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Train ML model on startup (if data exists)
    try:
        ml_predictor.train_model()
    except Exception as e:
        print(f"ML model training skipped: {e}")
    
    # Start streaming simulation
    import threading
    streaming_thread = threading.Thread(
        target=streaming_processor.simulate_data_stream,
        args=(10,),
        daemon=True
    )
    streaming_thread.start()
    
    # Run application
    socketio.run(app, host=API_HOST, port=API_PORT, debug=DEBUG)

