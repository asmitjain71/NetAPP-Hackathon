# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Local Python Setup (Recommended for Development)

1. **Install Python 3.11+**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**
   ```bash
   python -c "from models import init_db; init_db()"
   ```

5. **Run Application**
   ```bash
   python app.py
   # OR
   python run.py
   ```

6. **Open Dashboard**
   - Navigate to: http://localhost:5000
   - Click "Create Sample Data" to get started

### Option 2: Docker Setup (Recommended for Production)

1. **Build and Run**
   ```bash
   docker-compose up --build
   ```

2. **Open Dashboard**
   - Navigate to: http://localhost:5000

## 📝 First Steps

### 1. Create Sample Data
- Click the "Create Sample Data" button in the dashboard
- This creates 5 sample data objects with various access patterns

### 2. Explore the Dashboard
- View statistics: Total objects, size, cost, active migrations
- Check tier distribution chart
- Browse data objects table

### 3. Optimize Data Placement
- Click "Optimize" on any data object
- View optimization analysis with cost savings
- Optionally migrate to recommended tier

### 4. Try ML Predictions
- Click "Predict" on any data object
- View ML-based tier predictions
- Train the model with "Train Model" button

### 5. Test Data Migration
- Click "Migrate" on any data object
- Select target tier
- Monitor migration progress

### 6. Enable Real-Time Streaming
- Click "Start Streaming" button
- View real-time events in the dashboard
- See data ingestion, access, and alert events

## 🔧 Configuration

### Environment Variables
Create a `.env` file (copy from `.env.example`):
```env
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=True
DATABASE_URL=sqlite:///data_management.db
```

### Cloud Provider Setup (Optional)
For real cloud integration, add credentials to `.env`:
```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AZURE_CONNECTION_STRING=your_connection_string
GCP_CREDENTIALS_PATH=path/to/credentials.json
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Change port in .env or config.py
API_PORT=5001
```

### Database Errors
```bash
# Delete existing database and reinitialize
rm data_management.db
python -c "from models import init_db; init_db()"
```

### Import Errors
```bash
# Make sure all dependencies are installed
pip install -r requirements.txt
```

### Docker Issues
```bash
# Rebuild containers
docker-compose down
docker-compose up --build
```

## 📚 Next Steps

1. **Read the README.md** for detailed documentation
2. **Check PRESENTATION.md** for presentation outline
3. **Explore the API** at http://localhost:5000/api/health
4. **Review the code** in the main components:
   - `data_placement_optimizer.py` - Optimization logic
   - `migration_service.py` - Migration handling
   - `ml_predictor.py` - ML predictions
   - `streaming_processor.py` - Real-time processing

## 🎯 Testing the System

### Test Optimization
```bash
# Create sample data via dashboard
# Click "Optimize" on objects
# Verify recommendations make sense
```

### Test Migration
```bash
# Create migration via dashboard
# Monitor progress in real-time
# Verify object location updates
```

### Test ML Predictions
```bash
# Train model: Click "Train Model"
# Make predictions: Click "Predict" on objects
# Verify confidence scores
```

### Test Streaming
```bash
# Start streaming: Click "Start Streaming"
# View events in real-time
# Verify event processing
```

## 💡 Tips

- **Start with sample data** to see the system in action
- **Use batch operations** for multiple objects
- **Monitor migrations** in the migrations table
- **Check real-time events** for streaming activity
- **Train ML model** after creating sample data for better predictions

## 🆘 Need Help?

- Check the README.md for detailed documentation
- Review the code comments for implementation details
- Check the API endpoints at `/api/health`
- Review PRESENTATION.md for architecture overview

---

**Happy Hacking! 🚀**


