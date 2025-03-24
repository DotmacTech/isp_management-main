"""
Dashboard service for the ISP Management Platform.

This module provides a web-based dashboard for visualizing monitoring data,
system metrics, and logs from the central logging and monitoring services.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from isp_management.backend_core.database import get_db
from isp_management.backend_core.auth_service import get_current_active_user
from isp_management.backend_core.models import User
from isp_management.backend_core.logging_service import get_logger
from isp_management.backend_core.monitoring_service import get_monitoring_service

# Get the logger and monitoring service
logger = get_logger()
monitoring_service = get_monitoring_service()

# Create router for dashboard
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Connection manager for WebSocket connections
class ConnectionManager:
    """Manager for WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Connect a WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific client."""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)


# Create connection manager
manager = ConnectionManager()


@dashboard_router.get("/", response_class=HTMLResponse)
async def get_dashboard(current_user: User = Depends(get_current_active_user)):
    """
    Get the dashboard HTML page.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        HTML response with the dashboard page
    """
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access dashboard")
    
    # Return dashboard HTML
    return HTMLResponse(content=_get_dashboard_html())


@dashboard_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)
    
    try:
        # Send initial data
        await send_dashboard_data(websocket)
        
        # Start periodic updates
        while True:
            # Wait for a message (or timeout)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                # Process any incoming messages if needed
                await process_websocket_message(data, websocket)
            except asyncio.TimeoutError:
                # Send updated data periodically
                await send_dashboard_data(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def process_websocket_message(data: str, websocket: WebSocket):
    """
    Process a message from a WebSocket client.
    
    Args:
        data: Message data
        websocket: WebSocket connection
    """
    try:
        message = json.loads(data)
        
        # Handle different message types
        if message.get("type") == "get_data":
            await send_dashboard_data(websocket)
        elif message.get("type") == "set_threshold":
            # Update alert threshold
            metric = message.get("metric")
            threshold = message.get("threshold")
            if metric and threshold:
                monitoring_service.set_alert_threshold(metric, float(threshold))
                await manager.send_personal_message(
                    json.dumps({"type": "threshold_updated", "metric": metric, "threshold": threshold}),
                    websocket
                )
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {str(e)}", "dashboard", exception=e)
        await manager.send_personal_message(
            json.dumps({"type": "error", "message": str(e)}),
            websocket
        )


async def send_dashboard_data(websocket: WebSocket):
    """
    Send dashboard data to a WebSocket client.
    
    Args:
        websocket: WebSocket connection
    """
    try:
        # Get system metrics
        system_metrics = {
            "cpu_usage": monitoring_service.cpu_usage._value,
            "memory_usage": monitoring_service.memory_usage._value,
            "disk_usage": monitoring_service.disk_usage._value,
            "network_sent": monitoring_service.network_sent._value,
            "network_received": monitoring_service.network_received._value,
        }
        
        # Get database metrics
        db_metrics = {
            "connections": getattr(monitoring_service.db_connections, "_value", 0),
            "size": getattr(monitoring_service.db_size, "_value", 0),
        }
        
        # Get recent logs
        logs = await get_recent_logs(limit=100)
        
        # Get recent alerts
        alerts = await get_recent_alerts(limit=10)
        
        # Get alert thresholds
        thresholds = monitoring_service.alert_thresholds
        
        # Combine all data
        data = {
            "type": "dashboard_data",
            "timestamp": datetime.utcnow().isoformat(),
            "system_metrics": system_metrics,
            "db_metrics": db_metrics,
            "logs": logs,
            "alerts": alerts,
            "thresholds": thresholds,
        }
        
        # Send data to client
        await manager.send_personal_message(json.dumps(data), websocket)
    except Exception as e:
        logger.error(f"Error sending dashboard data: {str(e)}", "dashboard", exception=e)
        await manager.send_personal_message(
            json.dumps({"type": "error", "message": str(e)}),
            websocket
        )


async def get_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent logs from Elasticsearch.
    
    Args:
        limit: Maximum number of logs to return
    
    Returns:
        List of log entries
    """
    logs = []
    
    # Check if Elasticsearch client is available
    es_client = logger.es_client
    if not es_client:
        return logs
    
    try:
        # Query Elasticsearch for recent logs
        index_pattern = f"isp-logs-{datetime.utcnow().strftime('%Y-%m-%d')}"
        response = es_client.search(
            index=index_pattern,
            body={
                "query": {
                    "match_all": {}
                },
                "sort": [
                    {"timestamp": {"order": "desc"}}
                ],
                "size": limit
            }
        )
        
        # Extract logs from response
        for hit in response["hits"]["hits"]:
            logs.append(hit["_source"])
    except Exception as e:
        logger.error(f"Error retrieving logs from Elasticsearch: {str(e)}", "dashboard", exception=e)
    
    return logs


async def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent alerts.
    
    Args:
        limit: Maximum number of alerts to return
    
    Returns:
        List of alert entries
    """
    alerts = []
    
    # Check if Elasticsearch client is available
    es_client = logger.es_client
    if not es_client:
        return alerts
    
    try:
        # Query Elasticsearch for recent alerts
        index_pattern = f"isp-logs-{datetime.utcnow().strftime('%Y-%m-%d')}"
        response = es_client.search(
            index=index_pattern,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"module": "monitoring"}},
                            {"prefix": {"message": "Alert:"}}
                        ]
                    }
                },
                "sort": [
                    {"timestamp": {"order": "desc"}}
                ],
                "size": limit
            }
        )
        
        # Extract alerts from response
        for hit in response["hits"]["hits"]:
            alerts.append(hit["_source"])
    except Exception as e:
        logger.error(f"Error retrieving alerts from Elasticsearch: {str(e)}", "dashboard", exception=e)
    
    return alerts


@dashboard_router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current system metrics.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Dictionary of system metrics
    """
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access metrics")
    
    # Get system metrics
    system_metrics = {
        "cpu_usage": monitoring_service.cpu_usage._value,
        "memory_usage": monitoring_service.memory_usage._value,
        "disk_usage": monitoring_service.disk_usage._value,
        "network_sent": monitoring_service.network_sent._value,
        "network_received": monitoring_service.network_received._value,
    }
    
    # Get database metrics
    db_metrics = {
        "connections": getattr(monitoring_service.db_connections, "_value", 0),
        "size": getattr(monitoring_service.db_size, "_value", 0),
    }
    
    # Get business metrics
    business_metrics = {
        "active_users": getattr(monitoring_service.active_users, "_value", 0),
        "active_sessions": getattr(monitoring_service.active_sessions, "_value", 0),
        "customer_count": getattr(monitoring_service.customer_count, "_value", 0),
    }
    
    # Combine all metrics
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_metrics,
        "database": db_metrics,
        "business": business_metrics,
    }
    
    return metrics


@dashboard_router.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    module: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get logs with optional filtering.
    
    Args:
        level: Log level filter
        module: Module name filter
        start_time: Start time filter (ISO format)
        end_time: End time filter (ISO format)
        limit: Maximum number of logs to return
        current_user: Current authenticated user
    
    Returns:
        List of log entries
    """
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access logs")
    
    # Check if Elasticsearch client is available
    es_client = logger.es_client
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    try:
        # Build Elasticsearch query
        query = {"bool": {"must": []}}
        
        # Add level filter
        if level:
            query["bool"]["must"].append({"term": {"level": level.upper()}})
        
        # Add module filter
        if module:
            query["bool"]["must"].append({"term": {"module": module}})
        
        # Add time range filter
        time_range = {}
        if start_time:
            time_range["gte"] = start_time
        if end_time:
            time_range["lte"] = end_time
        
        if time_range:
            query["bool"]["must"].append({"range": {"timestamp": time_range}})
        
        # If no filters, use match_all query
        if not query["bool"]["must"]:
            query = {"match_all": {}}
        
        # Query Elasticsearch
        index_pattern = "isp-logs-*"
        response = es_client.search(
            index=index_pattern,
            body={
                "query": query,
                "sort": [
                    {"timestamp": {"order": "desc"}}
                ],
                "size": limit
            }
        )
        
        # Extract logs from response
        logs = []
        for hit in response["hits"]["hits"]:
            logs.append(hit["_source"])
        
        return logs
    except Exception as e:
        logger.error(f"Error retrieving logs from Elasticsearch: {str(e)}", "dashboard", exception=e)
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")


@dashboard_router.get("/alerts")
async def get_alerts(
    alert_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get alerts with optional filtering.
    
    Args:
        alert_type: Alert type filter
        start_time: Start time filter (ISO format)
        end_time: End time filter (ISO format)
        limit: Maximum number of alerts to return
        current_user: Current authenticated user
    
    Returns:
        List of alert entries
    """
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access alerts")
    
    # Check if Elasticsearch client is available
    es_client = logger.es_client
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    try:
        # Build Elasticsearch query
        query = {
            "bool": {
                "must": [
                    {"term": {"module": "monitoring"}},
                    {"prefix": {"message": "Alert:"}}
                ]
            }
        }
        
        # Add alert type filter
        if alert_type:
            query["bool"]["must"].append({"term": {"context.type": alert_type}})
        
        # Add time range filter
        time_range = {}
        if start_time:
            time_range["gte"] = start_time
        if end_time:
            time_range["lte"] = end_time
        
        if time_range:
            query["bool"]["must"].append({"range": {"timestamp": time_range}})
        
        # Query Elasticsearch
        index_pattern = "isp-logs-*"
        response = es_client.search(
            index=index_pattern,
            body={
                "query": query,
                "sort": [
                    {"timestamp": {"order": "desc"}}
                ],
                "size": limit
            }
        )
        
        # Extract alerts from response
        alerts = []
        for hit in response["hits"]["hits"]:
            alerts.append(hit["_source"])
        
        return alerts
    except Exception as e:
        logger.error(f"Error retrieving alerts from Elasticsearch: {str(e)}", "dashboard", exception=e)
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@dashboard_router.post("/thresholds/{metric}")
async def update_threshold(
    metric: str,
    threshold: float,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an alert threshold.
    
    Args:
        metric: Metric name
        threshold: New threshold value
        current_user: Current authenticated user
    
    Returns:
        Success message
    """
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update thresholds")
    
    # Update threshold
    if metric in monitoring_service.alert_thresholds:
        monitoring_service.set_alert_threshold(metric, threshold)
        return {"message": f"Threshold for {metric} updated to {threshold}"}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")


def _get_dashboard_html() -> str:
    """
    Get the HTML for the dashboard page.
    
    Returns:
        HTML content
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ISP Management Platform - Monitoring Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f8f9fa;
                padding-top: 20px;
            }
            .card {
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .card-header {
                background-color: #4a6fdc;
                color: white;
                font-weight: bold;
                border-radius: 10px 10px 0 0 !important;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
            }
            .metric-label {
                font-size: 14px;
                color: #6c757d;
            }
            .alert-item {
                border-left: 4px solid #dc3545;
                padding-left: 10px;
                margin-bottom: 10px;
            }
            .log-item {
                border-left: 4px solid #6c757d;
                padding-left: 10px;
                margin-bottom: 5px;
                font-size: 14px;
            }
            .log-item.DEBUG {
                border-left-color: #6c757d;
            }
            .log-item.INFO {
                border-left-color: #0d6efd;
            }
            .log-item.WARNING {
                border-left-color: #ffc107;
            }
            .log-item.ERROR, .log-item.CRITICAL {
                border-left-color: #dc3545;
            }
            .threshold-form {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            .threshold-form select, .threshold-form input {
                margin-right: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">ISP Management Platform - Monitoring Dashboard</h1>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">System Metrics</div>
                        <div class="card-body">
                            <canvas id="systemMetricsChart" height="200"></canvas>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">Database Metrics</div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6 text-center">
                                    <div class="metric-value" id="dbConnections">0</div>
                                    <div class="metric-label">Active Connections</div>
                                </div>
                                <div class="col-md-6 text-center">
                                    <div class="metric-value" id="dbSize">0 MB</div>
                                    <div class="metric-label">Database Size</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">Alert Thresholds</div>
                        <div class="card-body">
                            <div class="threshold-form">
                                <select id="thresholdMetric" class="form-select" style="width: 200px;">
                                    <option value="cpu_usage">CPU Usage</option>
                                    <option value="memory_usage">Memory Usage</option>
                                    <option value="disk_usage">Disk Usage</option>
                                    <option value="db_connection_count">DB Connections</option>
                                    <option value="api_error_rate">API Error Rate</option>
                                    <option value="api_response_time">API Response Time</option>
                                </select>
                                <input type="number" id="thresholdValue" class="form-control" style="width: 100px;" min="0" step="0.1">
                                <button id="updateThreshold" class="btn btn-primary">Update</button>
                            </div>
                            <div id="thresholdsList" class="mt-3">
                                <!-- Thresholds will be displayed here -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">Recent Alerts</div>
                        <div class="card-body">
                            <div id="alertsList">
                                <!-- Alerts will be displayed here -->
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">Recent Logs</div>
                        <div class="card-body">
                            <div id="logsList" style="max-height: 400px; overflow-y: auto;">
                                <!-- Logs will be displayed here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // WebSocket connection
            let socket;
            let systemMetricsChart;
            
            // Connect to WebSocket
            function connectWebSocket() {
                socket = new WebSocket(`ws://${window.location.host}/api/dashboard/ws`);
                
                socket.onopen = function(e) {
                    console.log("WebSocket connection established");
                };
                
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === "dashboard_data") {
                        updateDashboard(data);
                    } else if (data.type === "threshold_updated") {
                        // Refresh thresholds
                        updateThresholds(data.thresholds);
                    } else if (data.type === "error") {
                        console.error("Error:", data.message);
                    }
                };
                
                socket.onclose = function(event) {
                    console.log("WebSocket connection closed");
                    // Reconnect after a delay
                    setTimeout(connectWebSocket, 5000);
                };
                
                socket.onerror = function(error) {
                    console.error("WebSocket error:", error);
                };
            }
            
            // Initialize charts
            function initCharts() {
                const ctx = document.getElementById('systemMetricsChart').getContext('2d');
                systemMetricsChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['CPU Usage', 'Memory Usage', 'Disk Usage'],
                        datasets: [{
                            label: 'Percentage',
                            data: [0, 0, 0],
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.2)',
                                'rgba(54, 162, 235, 0.2)',
                                'rgba(255, 206, 86, 0.2)'
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Percentage'
                                }
                            }
                        }
                    }
                });
            }
            
            // Update dashboard with new data
            function updateDashboard(data) {
                // Update system metrics chart
                systemMetricsChart.data.datasets[0].data = [
                    data.system_metrics.cpu_usage,
                    data.system_metrics.memory_usage,
                    data.system_metrics.disk_usage
                ];
                systemMetricsChart.update();
                
                // Update database metrics
                document.getElementById('dbConnections').textContent = data.db_metrics.connections;
                document.getElementById('dbSize').textContent = formatBytes(data.db_metrics.size);
                
                // Update thresholds
                updateThresholds(data.thresholds);
                
                // Update alerts
                updateAlerts(data.alerts);
                
                // Update logs
                updateLogs(data.logs);
            }
            
            // Update thresholds display
            function updateThresholds(thresholds) {
                const thresholdsList = document.getElementById('thresholdsList');
                thresholdsList.innerHTML = '';
                
                for (const [metric, value] of Object.entries(thresholds)) {
                    const div = document.createElement('div');
                    div.innerHTML = `<strong>${formatMetricName(metric)}:</strong> ${value}`;
                    thresholdsList.appendChild(div);
                }
            }
            
            // Update alerts display
            function updateAlerts(alerts) {
                const alertsList = document.getElementById('alertsList');
                alertsList.innerHTML = '';
                
                if (alerts.length === 0) {
                    alertsList.innerHTML = '<p>No recent alerts</p>';
                    return;
                }
                
                for (const alert of alerts) {
                    const div = document.createElement('div');
                    div.className = 'alert-item';
                    div.innerHTML = `
                        <div><strong>${alert.message}</strong></div>
                        <div class="small text-muted">${formatTimestamp(alert.timestamp)}</div>
                    `;
                    alertsList.appendChild(div);
                }
            }
            
            // Update logs display
            function updateLogs(logs) {
                const logsList = document.getElementById('logsList');
                logsList.innerHTML = '';
                
                if (logs.length === 0) {
                    logsList.innerHTML = '<p>No logs available</p>';
                    return;
                }
                
                for (const log of logs) {
                    const div = document.createElement('div');
                    div.className = `log-item ${log.level}`;
                    div.innerHTML = `
                        <div><span class="badge bg-secondary">${log.level}</span> <strong>${log.module}</strong>: ${log.message}</div>
                        <div class="small text-muted">${formatTimestamp(log.timestamp)}</div>
                    `;
                    logsList.appendChild(div);
                }
            }
            
            // Format bytes to human-readable format
            function formatBytes(bytes, decimals = 2) {
                if (bytes === 0) return '0 Bytes';
                
                const k = 1024;
                const dm = decimals < 0 ? 0 : decimals;
                const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
                
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                
                return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
            }
            
            // Format timestamp
            function formatTimestamp(timestamp) {
                const date = new Date(timestamp);
                return date.toLocaleString();
            }
            
            // Format metric name
            function formatMetricName(metric) {
                return metric
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, l => l.toUpperCase());
            }
            
            // Initialize page
            document.addEventListener('DOMContentLoaded', function() {
                initCharts();
                connectWebSocket();
                
                // Set up threshold update button
                document.getElementById('updateThreshold').addEventListener('click', function() {
                    const metric = document.getElementById('thresholdMetric').value;
                    const value = parseFloat(document.getElementById('thresholdValue').value);
                    
                    if (!isNaN(value)) {
                        socket.send(JSON.stringify({
                            type: 'set_threshold',
                            metric: metric,
                            threshold: value
                        }));
                    }
                });
            });
        </script>
    </body>
    </html>
    """
