"""
Machine Learning Predictor for Data Usage Patterns
Learns from access patterns and predicts optimal data placement
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func
from models import DataObject, AccessLog, MLPrediction, SessionLocal
from config import STORAGE_TIERS
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class MLPredictor:
    """Machine learning predictor for data placement optimization"""
    
    def __init__(self, model_path='models/data_usage_predictor.pkl'):
        self.db = SessionLocal()
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'size_gb',
            'access_count',
            'accesses_per_day',
            'hours_since_access',
            'avg_latency_ms',
            'current_cost',
            'days_since_creation'
        ]
        
        # Load or create model
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.scaler = model_data['scaler']
                    print(f"Loaded ML model from {self.model_path}")
            except Exception as e:
                print(f"Error loading model: {e}, creating new model")
                self._create_model()
        else:
            self._create_model()
    
    def _create_model(self):
        """Create new ML model"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        print("Created new ML model")
    
    def extract_features(self, data_object_id):
        """Extract features for a data object"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return None
        
        # Calculate access metrics
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        access_count = self.db.query(func.count(AccessLog.id)).filter(
            AccessLog.data_object_id == data_object_id,
            AccessLog.accessed_at >= cutoff_date
        ).scalar() or 0
        
        accesses_per_day = access_count / 30.0 if access_count > 0 else 0
        
        # Get last access time
        last_access = self.db.query(func.max(AccessLog.accessed_at)).filter(
            AccessLog.data_object_id == data_object_id
        ).scalar()
        
        if last_access:
            hours_since_access = (datetime.utcnow() - last_access).total_seconds() / 3600
        else:
            hours_since_access = (datetime.utcnow() - data_object.first_created).total_seconds() / 3600
        
        # Calculate average latency
        avg_latency = self.db.query(func.avg(AccessLog.latency_ms)).filter(
            AccessLog.data_object_id == data_object_id,
            AccessLog.latency_ms.isnot(None)
        ).scalar() or 100.0  # Default
        
        # Current cost
        current_cost = data_object.monthly_cost
        
        # Days since creation
        days_since_creation = (datetime.utcnow() - data_object.first_created).total_seconds() / 86400
        
        features = np.array([[
            data_object.size_gb,
            access_count,
            accesses_per_day,
            hours_since_access,
            avg_latency,
            current_cost,
            days_since_creation
        ]])
        
        return features
    
    def predict_tier(self, data_object_id):
        """Predict optimal tier for a data object"""
        features = self.extract_features(data_object_id)
        
        if features is None:
            return None
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict
        tier_prediction = self.model.predict(features_scaled)[0]
        confidence_scores = self.model.predict_proba(features_scaled)[0]
        
        # Map prediction to tier
        tier_map = {0: 'hot', 1: 'warm', 2: 'cold'}
        predicted_tier = tier_map.get(tier_prediction, 'warm')
        
        # Get confidence score
        tier_indices = {'hot': 0, 'warm': 1, 'cold': 2}
        confidence = confidence_scores[tier_indices[predicted_tier]]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(features[0], predicted_tier, confidence)
        
        # Store prediction
        prediction = MLPrediction(
            data_object_id=data_object_id,
            predicted_tier=predicted_tier,
            confidence_score=float(confidence),
            reasoning=reasoning
        )
        
        self.db.add(prediction)
        self.db.commit()
        
        return {
            'data_object_id': data_object_id,
            'predicted_tier': predicted_tier,
            'confidence_score': float(confidence),
            'reasoning': reasoning,
            'all_scores': {
                'hot': float(confidence_scores[0]),
                'warm': float(confidence_scores[1]),
                'cold': float(confidence_scores[2])
            }
        }
    
    def _generate_reasoning(self, features, tier, confidence):
        """Generate human-readable reasoning for prediction"""
        size_gb, access_count, accesses_per_day, hours_since_access, avg_latency, current_cost, days_since_creation = features[0]
        
        reasons = []
        
        if accesses_per_day > 50:
            reasons.append(f"Very high access frequency ({accesses_per_day:.1f}/day)")
        elif accesses_per_day > 10:
            reasons.append(f"High access frequency ({accesses_per_day:.1f}/day)")
        elif accesses_per_day > 1:
            reasons.append(f"Moderate access frequency ({accesses_per_day:.1f}/day)")
        else:
            reasons.append(f"Low access frequency ({accesses_per_day:.1f}/day)")
        
        if hours_since_access < 24:
            reasons.append("Recently accessed")
        elif hours_since_access < 168:
            reasons.append("Accessed within last week")
        else:
            reasons.append("Not accessed recently")
        
        if tier == 'hot':
            reasons.append("Recommended for hot tier due to high access")
        elif tier == 'warm':
            reasons.append("Recommended for warm tier for balanced performance/cost")
        else:
            reasons.append("Recommended for cold tier due to low access")
        
        reasons.append(f"Confidence: {confidence:.1%}")
        
        return "; ".join(reasons)
    
    def train_model(self):
        """Train the ML model on historical data"""
        print("Training ML model...")
        
        # Get all data objects with access logs
        data_objects = self.db.query(DataObject).all()
        
        if len(data_objects) < 10:
            print("Not enough data for training, using default model")
            return
        
        X = []
        y = []
        
        for obj in data_objects:
            features = self.extract_features(obj.id)
            if features is None:
                continue
            
            # Determine actual tier based on access patterns
            access_count = self.db.query(func.count(AccessLog.id)).filter(
                AccessLog.data_object_id == obj.id
            ).scalar() or 0
            
            last_access = self.db.query(func.max(AccessLog.accessed_at)).filter(
                AccessLog.data_object_id == obj.id
            ).scalar()
            
            if last_access:
                hours_since = (datetime.utcnow() - last_access).total_seconds() / 3600
            else:
                hours_since = (datetime.utcnow() - obj.first_created).total_seconds() / 3600
            
            # Label based on access patterns
            if access_count > 100 and hours_since < 24:
                label = 0  # hot
            elif access_count > 10 and hours_since < 168:
                label = 1  # warm
            else:
                label = 2  # cold
            
            X.append(features[0])
            y.append(label)
        
        if len(X) < 10:
            print("Not enough labeled data for training")
            return
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        print(f"Model training complete - Train accuracy: {train_score:.2%}, Test accuracy: {test_score:.2%}")
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, f)
        
        print(f"Model saved to {self.model_path}")
    
    def batch_predict(self, limit=100):
        """Predict tiers for multiple data objects"""
        data_objects = self.db.query(DataObject).limit(limit).all()
        predictions = []
        
        for obj in data_objects:
            prediction = self.predict_tier(obj.id)
            if prediction:
                predictions.append(prediction)
        
        return predictions
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


