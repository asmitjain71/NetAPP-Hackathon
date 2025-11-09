# Start the NetApp Intelligent Data Management System
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NetApp Intelligent Data Management System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Yellow
python -c "from models import init_db; init_db(); print('Database initialized')"

Write-Host ""
Write-Host "Starting Flask application..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the application
python app.py

