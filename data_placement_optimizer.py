"""
Intelligent Data Placement Optimizer
Determines optimal storage tier based on access patterns, cost, and latency requirements
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from models import DataObject, AccessLog, SessionLocal
from config import STORAGE_TIERS, ACCESS_THRESHOLDS
import math

class DataPlacementOptimizer:
    """Optimizes data placement across storage tiers"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def calculate_access_frequency(self, data_object_id, days=30):
        """Calculate access frequency for a data object"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get access count in the last N days
        access_count = self.db.query(AccessLog).filter(
            AccessLog.data_object_id == data_object_id,
            AccessLog.accessed_at >= cutoff_date
        ).count()
        
        # Calculate accesses per day
        accesses_per_day = access_count / days if days > 0 else 0
        
        # Get last access time
        last_access = self.db.query(func.max(AccessLog.accessed_at)).filter(
            AccessLog.data_object_id == data_object_id
        ).scalar()
        
        if last_access:
            hours_since_access = (datetime.utcnow() - last_access).total_seconds() / 3600
        else:
            hours_since_access = float('inf')
        
        return {
            'accesses_per_day': accesses_per_day,
            'total_accesses': access_count,
            'hours_since_access': hours_since_access,
            'last_access': last_access.isoformat() if last_access else None
        }
    
    def classify_data_tier(self, access_metrics):
        """Classify data into hot, warm, or cold tier based on access patterns"""
        accesses_per_day = access_metrics['accesses_per_day']
        hours_since_access = access_metrics['hours_since_access']
        
        hot_threshold = ACCESS_THRESHOLDS['hot']
        warm_threshold = ACCESS_THRESHOLDS['warm']
        
        # Hot tier: High frequency, recent access
        if (accesses_per_day >= hot_threshold['accesses_per_day'] and 
            hours_since_access <= hot_threshold['last_access_hours']):
            return 'hot'
        
        # Warm tier: Moderate frequency, somewhat recent
        elif (accesses_per_day >= warm_threshold['accesses_per_day'] and 
              hours_since_access <= warm_threshold['last_access_hours']):
            return 'warm'
        
        # Cold tier: Low frequency or old data
        else:
            return 'cold'
    
    def calculate_cost_benefit(self, data_object, target_tier):
        """Calculate cost benefit of moving to target tier"""
        current_tier = data_object.current_tier
        size_gb = data_object.size_gb
        
        current_cost = STORAGE_TIERS[current_tier]['cost_per_gb'] * size_gb
        target_cost = STORAGE_TIERS[target_tier]['cost_per_gb'] * size_gb
        
        cost_savings = current_cost - target_cost
        cost_savings_percent = (cost_savings / current_cost * 100) if current_cost > 0 else 0
        
        return {
            'current_cost': current_cost,
            'target_cost': target_cost,
            'cost_savings': cost_savings,
            'cost_savings_percent': cost_savings_percent
        }
    
    def evaluate_latency_requirement(self, data_object, target_tier):
        """Evaluate if target tier meets latency requirements"""
        target_latency = STORAGE_TIERS[target_tier]['latency_ms']
        
        # Get average latency from access logs
        avg_latency = self.db.query(func.avg(AccessLog.latency_ms)).filter(
            AccessLog.data_object_id == data_object.id,
            AccessLog.latency_ms.isnot(None)
        ).scalar()
        
        if avg_latency is None:
            avg_latency = 100  # Default assumption
        
        # Check if target tier latency is acceptable (within 2x of current)
        latency_acceptable = target_latency <= avg_latency * 2
        
        return {
            'current_avg_latency': avg_latency,
            'target_latency': target_latency,
            'latency_acceptable': latency_acceptable,
            'latency_penalty': target_latency - avg_latency
        }
    
    def optimize_placement(self, data_object_id):
        """Determine optimal placement for a data object"""
        data_object = self.db.query(DataObject).filter(
            DataObject.id == data_object_id
        ).first()
        
        if not data_object:
            return None
        
        # Calculate access metrics
        access_metrics = self.calculate_access_frequency(data_object_id)
        
        # Classify tier based on access patterns
        recommended_tier = self.classify_data_tier(access_metrics)
        
        # Calculate cost benefit
        cost_analysis = self.calculate_cost_benefit(data_object, recommended_tier)
        
        # Evaluate latency
        latency_analysis = self.evaluate_latency_requirement(data_object, recommended_tier)
        
        # Calculate overall score
        score = self._calculate_optimization_score(
            access_metrics, cost_analysis, latency_analysis, recommended_tier
        )
        
        # Determine if migration is recommended
        should_migrate = (
            recommended_tier != data_object.current_tier and
            cost_analysis['cost_savings'] > 0.01 and  # At least $0.01 savings
            latency_analysis['latency_acceptable']
        )
        
        return {
            'data_object_id': data_object_id,
            'current_tier': data_object.current_tier,
            'recommended_tier': recommended_tier,
            'access_metrics': access_metrics,
            'cost_analysis': cost_analysis,
            'latency_analysis': latency_analysis,
            'optimization_score': score,
            'should_migrate': should_migrate,
            'reasoning': self._generate_reasoning(
                access_metrics, cost_analysis, latency_analysis, recommended_tier
            )
        }
    
    def _calculate_optimization_score(self, access_metrics, cost_analysis, latency_analysis, tier):
        """Calculate overall optimization score (0-100)"""
        # Access pattern score (0-40 points)
        if tier == 'hot':
            access_score = min(40, access_metrics['accesses_per_day'] * 0.4)
        elif tier == 'warm':
            access_score = min(30, access_metrics['accesses_per_day'] * 3)
        else:
            access_score = 20  # Cold tier is appropriate for low access
        
        # Cost efficiency score (0-30 points)
        cost_score = min(30, cost_analysis['cost_savings_percent'] * 0.3)
        
        # Latency score (0-30 points)
        if latency_analysis['latency_acceptable']:
            latency_score = 30 - min(30, latency_analysis['latency_penalty'] * 0.1)
        else:
            latency_score = 0
        
        total_score = access_score + cost_score + latency_score
        return min(100, max(0, total_score))
    
    def _generate_reasoning(self, access_metrics, cost_analysis, latency_analysis, tier):
        """Generate human-readable reasoning for placement recommendation"""
        reasons = []
        
        if access_metrics['accesses_per_day'] > 50:
            reasons.append(f"High access frequency ({access_metrics['accesses_per_day']:.1f} accesses/day)")
        elif access_metrics['accesses_per_day'] > 5:
            reasons.append(f"Moderate access frequency ({access_metrics['accesses_per_day']:.1f} accesses/day)")
        else:
            reasons.append(f"Low access frequency ({access_metrics['accesses_per_day']:.1f} accesses/day)")
        
        if cost_analysis['cost_savings'] > 0:
            reasons.append(f"Cost savings: ${cost_analysis['cost_savings']:.2f}/month ({cost_analysis['cost_savings_percent']:.1f}%)")
        
        if latency_analysis['latency_acceptable']:
            reasons.append(f"Latency acceptable: {latency_analysis['target_latency']}ms")
        else:
            reasons.append(f"Latency concern: {latency_analysis['target_latency']}ms may be too high")
        
        return "; ".join(reasons)
    
    def batch_optimize(self, limit=100):
        """Optimize placement for multiple data objects"""
        data_objects = self.db.query(DataObject).limit(limit).all()
        results = []
        
        for obj in data_objects:
            optimization = self.optimize_placement(obj.id)
            if optimization:
                results.append(optimization)
        
        return results
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


