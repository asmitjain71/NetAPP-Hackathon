// Dashboard JavaScript
const API_BASE = '/api';
let socket;
let tierChart;
let streamingActive = false;

// Initialize Socket.IO connection
function initSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('data_object_created', (data) => {
        loadDataObjects();
        loadStats();
    });
    
    socket.on('access_logged', (data) => {
        loadDataObjects();
        loadStats();
    });
    
    socket.on('optimization_complete', (data) => {
        showNotification('Optimization complete', 'success');
        loadDataObjects();
    });
    
    socket.on('migration_started', (data) => {
        loadMigrations();
        loadStats();
    });
    
    socket.on('prediction_complete', (data) => {
        showNotification('ML Prediction complete', 'success');
    });
}

// Load dashboard statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('total-objects').textContent = stats.total_objects;
        document.getElementById('total-size').textContent = `${stats.total_size_gb.toFixed(2)} GB`;
        document.getElementById('total-cost').textContent = `$${stats.total_monthly_cost.toFixed(2)}`;
        document.getElementById('active-migrations').textContent = stats.active_migrations;
        
        // Update tier chart
        updateTierChart(stats.tier_distribution);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Update tier distribution chart
function updateTierChart(distribution) {
    const ctx = document.getElementById('tier-chart').getContext('2d');
    
    if (tierChart) {
        tierChart.destroy();
    }
    
    tierChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Hot', 'Warm', 'Cold'],
            datasets: [{
                data: [
                    distribution.hot || 0,
                    distribution.warm || 0,
                    distribution.cold || 0
                ],
                backgroundColor: [
                    '#ff6b6b',
                    '#ffd93d',
                    '#6bcf7f'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Load data objects
async function loadDataObjects() {
    try {
        const response = await fetch(`${API_BASE}/data-objects`);
        const objects = await response.json();
        
        const tbody = document.getElementById('objects-tbody');
        tbody.innerHTML = '';
        
        objects.forEach(obj => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${obj.id}</td>
                <td>${obj.name}</td>
                <td>${obj.size_gb.toFixed(2)}</td>
                <td><span class="tier-badge tier-${obj.current_tier}">${obj.current_tier}</span></td>
                <td>${obj.current_location || 'N/A'}</td>
                <td>${obj.access_count}</td>
                <td>$${obj.monthly_cost.toFixed(2)}</td>
                <td>
                    <button class="action-btn btn-optimize" onclick="optimizeObject(${obj.id})">Optimize</button>
                    <button class="action-btn btn-predict" onclick="predictTier(${obj.id})">Predict</button>
                    <button class="action-btn btn-migrate" onclick="showMigrationModal(${obj.id})">Migrate</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading data objects:', error);
    }
}

// Load migrations
async function loadMigrations() {
    try {
        const response = await fetch(`${API_BASE}/migrations?status=active`);
        const migrations = await response.json();
        
        const tbody = document.getElementById('migrations-tbody');
        tbody.innerHTML = '';
        
        if (migrations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No active migrations</td></tr>';
            return;
        }
        
        migrations.forEach(migration => {
            const row = document.createElement('tr');
            const progress = migration.progress_percent || 0;
            row.innerHTML = `
                <td>${migration.id}</td>
                <td>Object #${migration.data_object_id}</td>
                <td>${migration.source_tier} → ${migration.target_tier}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%">${progress.toFixed(1)}%</div>
                    </div>
                </td>
                <td><span class="status-badge status-${migration.status}">${migration.status}</span></td>
                <td>
                    ${migration.status === 'failed' ? 
                        `<button class="action-btn btn-secondary" onclick="retryMigration(${migration.id})">Retry</button>` : 
                        ''
                    }
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading migrations:', error);
    }
}

// Optimize object placement
async function optimizeObject(objId) {
    try {
        const response = await fetch(`${API_BASE}/optimize/${objId}`, {
            method: 'POST'
        });
        const result = await response.json();
        
        showModal('Optimization Result', `
            <h3>Optimization Analysis</h3>
            <p><strong>Current Tier:</strong> ${result.current_tier}</p>
            <p><strong>Recommended Tier:</strong> ${result.recommended_tier}</p>
            <p><strong>Optimization Score:</strong> ${result.optimization_score.toFixed(1)}/100</p>
            <p><strong>Cost Savings:</strong> $${result.cost_analysis.cost_savings.toFixed(2)}/month</p>
            <p><strong>Reasoning:</strong> ${result.reasoning}</p>
            ${result.should_migrate ? 
                `<button class="btn-primary" onclick="migrateObject(${objId}, '${result.recommended_tier}')">Migrate Now</button>` : 
                '<p>No migration recommended at this time.</p>'
            }
        `);
    } catch (error) {
        console.error('Error optimizing object:', error);
        showNotification('Error optimizing object', 'error');
    }
}

// Predict tier using ML
async function predictTier(objId) {
    try {
        const response = await fetch(`${API_BASE}/predict/${objId}`, {
            method: 'POST'
        });
        const result = await response.json();
        
        showModal('ML Prediction', `
            <h3>ML Prediction Result</h3>
            <p><strong>Predicted Tier:</strong> ${result.predicted_tier}</p>
            <p><strong>Confidence:</strong> ${(result.confidence_score * 100).toFixed(1)}%</p>
            <p><strong>Reasoning:</strong> ${result.reasoning}</p>
            <h4>All Tier Scores:</h4>
            <ul>
                <li>Hot: ${(result.all_scores.hot * 100).toFixed(1)}%</li>
                <li>Warm: ${(result.all_scores.warm * 100).toFixed(1)}%</li>
                <li>Cold: ${(result.all_scores.cold * 100).toFixed(1)}%</li>
            </ul>
        `);
    } catch (error) {
        console.error('Error predicting tier:', error);
        showNotification('Error predicting tier', 'error');
    }
}

// Show migration modal
async function showMigrationModal(objId) {
    const response = await fetch(`${API_BASE}/data-objects/${objId}`);
    const obj = await response.json();
    
    showModal('Migrate Data Object', `
        <h3>Migrate: ${obj.name}</h3>
        <p>Current: ${obj.current_tier} tier at ${obj.current_location}</p>
        <label>Target Tier:</label>
        <select id="target-tier" class="form-control">
            <option value="hot">Hot</option>
            <option value="warm">Warm</option>
            <option value="cold">Cold</option>
        </select>
        <button class="btn-primary" style="margin-top: 15px;" onclick="migrateObject(${objId}, document.getElementById('target-tier').value)">Start Migration</button>
    `);
}

// Migrate object
async function migrateObject(objId, targetTier) {
    try {
        const response = await fetch(`${API_BASE}/migrations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                data_object_id: objId,
                target_tier: targetTier
            })
        });
        
        if (response.ok) {
            showNotification('Migration started', 'success');
            closeModal();
            loadMigrations();
        } else {
            showNotification('Error starting migration', 'error');
        }
    } catch (error) {
        console.error('Error migrating object:', error);
        showNotification('Error migrating object', 'error');
    }
}

// Retry failed migration
async function retryMigration(migrationId) {
    try {
        const response = await fetch(`${API_BASE}/migrations/${migrationId}/retry`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('Migration retry initiated', 'success');
            loadMigrations();
        }
    } catch (error) {
        console.error('Error retrying migration:', error);
    }
}

// Batch optimize
async function batchOptimize() {
    try {
        const response = await fetch(`${API_BASE}/optimize/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ limit: 100 })
        });
        
        const results = await response.json();
        showNotification(`Optimized ${results.length} objects`, 'success');
        loadDataObjects();
    } catch (error) {
        console.error('Error batch optimizing:', error);
    }
}

// Create sample data
async function createSampleData() {
    const sampleObjects = [
        { name: 'database_backup_2024.db', size_gb: 50, tier: 'hot', location: 'On-Premise Data Center' },
        { name: 'video_archive_2023.mp4', size_gb: 200, tier: 'cold', location: 'AWS S3 - us-east-1' },
        { name: 'user_uploads_batch_1.zip', size_gb: 10, tier: 'warm', location: 'Private Cloud Infrastructure' },
        { name: 'analytics_data_2024.json', size_gb: 5, tier: 'hot', location: 'On-Premise Data Center' },
        { name: 'old_documents_archive.tar', size_gb: 100, tier: 'cold', location: 'Azure Blob Storage - eastus' }
    ];
    
    for (const obj of sampleObjects) {
        try {
            await fetch(`${API_BASE}/data-objects`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(obj)
            });
            
            // Simulate some access logs
            const objResponse = await fetch(`${API_BASE}/data-objects`);
            const objects = await objResponse.json();
            const createdObj = objects.find(o => o.name === obj.name);
            
            if (createdObj) {
                for (let i = 0; i < Math.floor(Math.random() * 20) + 5; i++) {
                    await fetch(`${API_BASE}/data-objects/${createdObj.id}/access`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            access_type: 'read',
                            latency_ms: Math.random() * 100 + 10
                        })
                    });
                }
            }
        } catch (error) {
            console.error('Error creating sample data:', error);
        }
    }
    
    showNotification('Sample data created', 'success');
    loadDataObjects();
    loadStats();
}

// Toggle streaming
async function toggleStreaming() {
    const btn = document.getElementById('stream-btn');
    
    if (streamingActive) {
        await fetch(`${API_BASE}/streaming/stop`, { method: 'POST' });
        streamingActive = false;
        btn.textContent = 'Start Streaming';
        showNotification('Streaming stopped', 'info');
    } else {
        await fetch(`${API_BASE}/streaming/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ interval: 5 })
        });
        streamingActive = true;
        btn.textContent = 'Stop Streaming';
        showNotification('Streaming started', 'success');
        loadStreamingEvents();
    }
}

// Load streaming events
async function loadStreamingEvents() {
    try {
        const response = await fetch(`${API_BASE}/streaming/events?limit=20`);
        const events = await response.json();
        
        const container = document.getElementById('events-container');
        container.innerHTML = '';
        
        events.reverse().forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event-item';
            eventDiv.innerHTML = `
                <div class="event-type">${event.event_type}</div>
                <div class="event-time">${new Date(event.timestamp).toLocaleString()}</div>
            `;
            container.appendChild(eventDiv);
        });
    } catch (error) {
        console.error('Error loading streaming events:', error);
    }
}

// Train ML model
async function trainModel() {
    try {
        const response = await fetch(`${API_BASE}/ml/train`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('ML model training started', 'success');
        }
    } catch (error) {
        console.error('Error training model:', error);
    }
}

// Show modal
function showModal(title, content) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `<h2>${title}</h2>${content}`;
    modal.style.display = 'block';
}

// Close modal
function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple notification - can be enhanced with a toast library
    alert(message);
}

// Initialize dashboard
function init() {
    initSocket();
    loadStats();
    loadDataObjects();
    loadMigrations();
    loadStreamingEvents();
    
    // Refresh data every 5 seconds
    setInterval(() => {
        loadStats();
        loadDataObjects();
        loadMigrations();
        if (streamingActive) {
            loadStreamingEvents();
        }
    }, 5000);
}

// Start when page loads
window.addEventListener('DOMContentLoaded', init);


