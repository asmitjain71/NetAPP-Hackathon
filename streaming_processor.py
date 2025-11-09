"""
Real-Time Data Streaming Processor
Handles continuous data flow using Kafka or MQTT
"""
import json
import threading
import time
from datetime import datetime
from models import StreamingEvent, DataObject, AccessLog, SessionLocal
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, KAFKA_BOOTSTRAP_SERVERS
import random

try:
    from kafka import KafkaConsumer, KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: kafka-python not available, using simulation mode")

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Warning: paho-mqtt not available, using simulation mode")

class StreamingProcessor:
    """Processes real-time data streams"""
    
    def __init__(self, use_kafka=True, use_mqtt=False):
        self.db = SessionLocal()
        self.use_kafka = use_kafka and KAFKA_AVAILABLE
        self.use_mqtt = use_mqtt and MQTT_AVAILABLE
        self.running = False
        self.consumer = None
        self.producer = None
        self.mqtt_client = None
        self.event_handlers = []
    
    def start_kafka_consumer(self):
        """Start Kafka consumer for real-time data processing"""
        if not self.use_kafka:
            return False
        
        try:
            self.consumer = KafkaConsumer(
                'data-stream',
                'access-events',
                'migration-events',
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            self.running = True
            thread = threading.Thread(target=self._kafka_consume_loop, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"Kafka initialization failed: {e}")
            return False
    
    def start_mqtt_subscriber(self):
        """Start MQTT subscriber for real-time data processing"""
        if not self.use_mqtt:
            return False
        
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.running = True
            
            thread = threading.Thread(target=self._mqtt_loop, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"MQTT initialization failed: {e}")
            return False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
            print(f"Connected to MQTT broker, subscribed to {MQTT_TOPIC}")
        else:
            print(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self._process_streaming_event(payload)
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
    
    def _mqtt_loop(self):
        """MQTT event loop"""
        self.mqtt_client.loop_forever()
    
    def _kafka_consume_loop(self):
        """Kafka consumer loop"""
        while self.running:
            try:
                message_pack = self.consumer.poll(timeout_ms=1000)
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        self._process_streaming_event(message.value)
            except Exception as e:
                print(f"Error in Kafka consumer loop: {e}")
                time.sleep(1)
    
    def _process_streaming_event(self, event_data):
        """Process a streaming event"""
        event_type = event_data.get('type', 'unknown')
        
        # Store event in database
        streaming_event = StreamingEvent(
            event_type=event_type,
            data_object_id=event_data.get('data_object_id'),
            payload=json.dumps(event_data),
            timestamp=datetime.utcnow()
        )
        
        self.db.add(streaming_event)
        
        # Process based on event type
        if event_type == 'data_ingestion':
            self._handle_data_ingestion(event_data)
        elif event_type == 'access_event':
            self._handle_access_event(event_data)
        elif event_type == 'migration_event':
            self._handle_migration_event(event_data)
        elif event_type == 'alert':
            self._handle_alert(event_data)
        
        self.db.commit()
        
        # Notify event handlers
        for handler in self.event_handlers:
            try:
                handler(event_data)
            except Exception as e:
                print(f"Error in event handler: {e}")
    
    def _handle_data_ingestion(self, event_data):
        """Handle new data ingestion event"""
        # Create or update data object
        data_object_id = event_data.get('data_object_id')
        if data_object_id:
            data_object = self.db.query(DataObject).filter(
                DataObject.id == data_object_id
            ).first()
            
            if data_object:
                # Update metadata
                if 'size_gb' in event_data:
                    data_object.size_gb = event_data['size_gb']
                if 'content_type' in event_data:
                    data_object.content_type = event_data['content_type']
                
                self.db.commit()
    
    def _handle_access_event(self, event_data):
        """Handle data access event"""
        data_object_id = event_data.get('data_object_id')
        if not data_object_id:
            return
        
        # Create access log
        access_log = AccessLog(
            data_object_id=data_object_id,
            accessed_at=datetime.utcnow(),
            access_type=event_data.get('access_type', 'read'),
            latency_ms=event_data.get('latency_ms'),
            source_ip=event_data.get('source_ip')
        )
        
        self.db.add(access_log)
        
        # Update data object access metrics
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if data_object:
            data_object.access_count += 1
            data_object.last_accessed = datetime.utcnow()
        
        self.db.commit()
    
    def _handle_migration_event(self, event_data):
        """Handle migration event"""
        # Migration events are handled by migration service
        pass
    
    def _handle_alert(self, event_data):
        """Handle alert event"""
        # Alerts can trigger automated actions
        alert_type = event_data.get('alert_type')
        message = event_data.get('message', '')
        
        print(f"Alert: {alert_type} - {message}")
    
    def publish_event(self, topic, event_data):
        """Publish an event to the stream"""
        if self.use_kafka and self.producer:
            try:
                self.producer.send(topic, event_data)
                self.producer.flush()
                return True
            except Exception as e:
                print(f"Error publishing to Kafka: {e}")
                return False
        elif self.use_mqtt and self.mqtt_client:
            try:
                self.mqtt_client.publish(topic, json.dumps(event_data))
                return True
            except Exception as e:
                print(f"Error publishing to MQTT: {e}")
                return False
        else:
            # Simulate event processing
            self._process_streaming_event(event_data)
            return True
    
    def simulate_data_stream(self, interval=5):
        """Simulate continuous data stream for testing"""
        def generate_event():
            event_types = ['data_ingestion', 'access_event', 'alert']
            event_type = random.choice(event_types)
            
            event_data = {
                'type': event_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if event_type == 'data_ingestion':
                event_data.update({
                    'data_object_id': random.randint(1, 100),
                    'size_gb': round(random.uniform(0.1, 100), 2),
                    'content_type': random.choice(['image', 'video', 'document', 'database'])
                })
            elif event_type == 'access_event':
                event_data.update({
                    'data_object_id': random.randint(1, 100),
                    'access_type': random.choice(['read', 'write', 'delete']),
                    'latency_ms': round(random.uniform(5, 500), 2),
                    'source_ip': f"192.168.1.{random.randint(1, 255)}"
                })
            elif event_type == 'alert':
                event_data.update({
                    'alert_type': random.choice(['cost_threshold', 'latency_spike', 'capacity_warning']),
                    'message': f"Alert: {random.choice(['High cost detected', 'Latency spike', 'Capacity warning'])}"
                })
            
            self.publish_event('data-stream', event_data)
        
        self.running = True
        while self.running:
            generate_event()
            time.sleep(interval)
    
    def add_event_handler(self, handler):
        """Add custom event handler"""
        self.event_handlers.append(handler)
    
    def stop(self):
        """Stop streaming processor"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.mqtt_client:
            self.mqtt_client.disconnect()
    
    def __del__(self):
        self.stop()
        if hasattr(self, 'db'):
            self.db.close()


