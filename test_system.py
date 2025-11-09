#!/usr/bin/env python
"""
Test script for the Intelligent Data Management System
Verifies all components are working correctly
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    try:
        from models import init_db, DataObject, AccessLog, Migration
        from data_placement_optimizer import DataPlacementOptimizer
        from migration_service import MigrationService
        from streaming_processor import StreamingProcessor
        from ml_predictor import MLPredictor
        from data_consistency_manager import DataConsistencyManager
        from config import STORAGE_TIERS, CLOUD_PROVIDERS
        print("[OK] All imports successful")
        return True
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from models import init_db, DataObject, SessionLocal
        init_db()
        db = SessionLocal()
        count = db.query(DataObject).count()
        print(f"[OK] Database initialized (current objects: {count})")
        db.close()
        return True
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        return False

def test_optimizer():
    """Test data placement optimizer"""
    print("\nTesting optimizer...")
    try:
        from data_placement_optimizer import DataPlacementOptimizer
        optimizer = DataPlacementOptimizer()
        print("[OK] Optimizer initialized")
        return True
    except Exception as e:
        print(f"[ERROR] Optimizer error: {e}")
        return False

def test_migration_service():
    """Test migration service"""
    print("\nTesting migration service...")
    try:
        from migration_service import MigrationService
        service = MigrationService()
        print("[OK] Migration service initialized")
        return True
    except Exception as e:
        print(f"[ERROR] Migration service error: {e}")
        return False

def test_streaming_processor():
    """Test streaming processor"""
    print("\nTesting streaming processor...")
    try:
        from streaming_processor import StreamingProcessor
        processor = StreamingProcessor(use_kafka=False, use_mqtt=False)
        print("[OK] Streaming processor initialized")
        return True
    except Exception as e:
        print(f"[ERROR] Streaming processor error: {e}")
        return False

def test_ml_predictor():
    """Test ML predictor"""
    print("\nTesting ML predictor...")
    try:
        from ml_predictor import MLPredictor
        predictor = MLPredictor()
        print("[OK] ML predictor initialized")
        return True
    except Exception as e:
        print(f"[ERROR] ML predictor error: {e}")
        return False

def test_consistency_manager():
    """Test consistency manager"""
    print("\nTesting consistency manager...")
    try:
        from data_consistency_manager import DataConsistencyManager
        manager = DataConsistencyManager()
        print("[OK] Consistency manager initialized")
        return True
    except Exception as e:
        print(f"[ERROR] Consistency manager error: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from config import STORAGE_TIERS, CLOUD_PROVIDERS, ACCESS_THRESHOLDS
        assert 'hot' in STORAGE_TIERS
        assert 'warm' in STORAGE_TIERS
        assert 'cold' in STORAGE_TIERS
        print("[OK] Configuration loaded correctly")
        return True
    except Exception as e:
        print(f"[ERROR] Configuration error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("NetApp Intelligent Data Management System - Test Suite")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_optimizer,
        test_migration_service,
        test_streaming_processor,
        test_ml_predictor,
        test_consistency_manager
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("[SUCCESS] All tests passed! System is ready to use.")
        return 0
    else:
        print("[FAILED] Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())


