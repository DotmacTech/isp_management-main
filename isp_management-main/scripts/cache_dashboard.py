#!/usr/bin/env python
"""
Cache Monitoring Dashboard

This script creates a simple web dashboard to monitor Redis cache performance
in the ISP Management Platform. It displays real-time metrics on cache hit rates,
memory usage, and performance improvements.

Run with: python cache_dashboard.py
Then access the dashboard at: http://localhost:8050/
"""
import os
import sys
import time
import json
import logging
import argparse
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict, deque

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import redis

from isp_management.backend_core.cache import redis_client
from isp_management.backend_core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cache_dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cache_dashboard")

# Initialize data storage
MAX_HISTORY = 100  # Maximum number of data points to store
cache_stats_history = {
    "timestamp": deque(maxlen=MAX_HISTORY),
    "total_keys": deque(maxlen=MAX_HISTORY),
    "memory_used_bytes": deque(maxlen=MAX_HISTORY),
    "hit_rate": deque(maxlen=MAX_HISTORY),
    "miss_rate": deque(maxlen=MAX_HISTORY),
    "tax_rates_count": deque(maxlen=MAX_HISTORY),
    "active_discounts_count": deque(maxlen=MAX_HISTORY),
    "invoices_count": deque(maxlen=MAX_HISTORY),
    "user_credit_notes_count": deque(maxlen=MAX_HISTORY),
}

# Cache key patterns
CACHE_PATTERNS = {
    "tax_rates": "tax_rate:*",
    "active_discounts": "active_discounts",
    "invoices": "invoice:*",
    "user_credit_notes": "user_credit_notes:*",
}

def get_redis_info():
    """Get Redis server information."""
    try:
        info = redis_client.info()
        return info
    except Exception as e:
        logger.error(f"Error getting Redis info: {e}")
        return {}

def get_cache_stats():
    """Get current cache statistics."""
    stats = {
        "timestamp": datetime.now(),
        "total_keys": 0,
        "memory_used_bytes": 0,
        "hit_rate": 0,
        "miss_rate": 0,
        "tax_rates_count": 0,
        "active_discounts_count": 0,
        "invoices_count": 0,
        "user_credit_notes_count": 0,
    }
    
    try:
        # Get Redis info
        info = get_redis_info()
        
        # Get memory usage
        stats["memory_used_bytes"] = info.get("used_memory", 0)
        
        # Get hit/miss rates
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total_ops = hits + misses
        
        if total_ops > 0:
            stats["hit_rate"] = (hits / total_ops) * 100
            stats["miss_rate"] = (misses / total_ops) * 100
        
        # Count keys by pattern
        for cache_type, pattern in CACHE_PATTERNS.items():
            count = len(redis_client.keys(pattern))
            stats[f"{cache_type}_count"] = count
            stats["total_keys"] += count
        
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return stats

def update_stats_history():
    """Update the stats history with current values."""
    stats = get_cache_stats()
    
    for key, value in stats.items():
        if key in cache_stats_history:
            cache_stats_history[key].append(value)

def collect_stats_thread(interval=5):
    """Background thread to collect stats at regular intervals."""
    while True:
        try:
            update_stats_history()
            time.sleep(interval)
        except Exception as e:
            logger.error(f"Error in stats collection thread: {e}")
            time.sleep(interval)

# Initialize Dash app
app = dash.Dash(__name__, title="ISP Management - Cache Dashboard")

app.layout = html.Div([
    html.H1("ISP Management Platform - Redis Cache Dashboard", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginTop': '20px'}),
    
    html.Div([
        html.Div([
            html.H3("Cache Overview", style={'textAlign': 'center'}),
            html.Div(id='overview-stats', className='stats-container')
        ], className='dashboard-card'),
        
        html.Div([
            html.H3("Cache Hit/Miss Rate", style={'textAlign': 'center'}),
            dcc.Graph(id='hit-miss-chart')
        ], className='dashboard-card'),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around'}),
    
    html.Div([
        html.Div([
            html.H3("Memory Usage", style={'textAlign': 'center'}),
            dcc.Graph(id='memory-chart')
        ], className='dashboard-card'),
        
        html.Div([
            html.H3("Cache Keys by Type", style={'textAlign': 'center'}),
            dcc.Graph(id='keys-chart')
        ], className='dashboard-card'),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around'}),
    
    html.Div([
        html.H3("Cache Configuration", style={'textAlign': 'center'}),
        html.Div(id='config-info', className='config-container')
    ], className='dashboard-card'),
    
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # in milliseconds (2 seconds)
        n_intervals=0
    ),
    
    # CSS
    html.Style('''
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
        }
        .dashboard-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 15px;
            margin: 15px;
            flex: 1;
            min-width: 45%;
        }
        .stats-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-around;
        }
        .stat-box {
            text-align: center;
            padding: 15px;
            margin: 10px;
            border-radius: 8px;
            background-color: #f8f9fa;
            min-width: 120px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 14px;
            color: #7f8c8d;
        }
        .config-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-around;
        }
        .config-item {
            padding: 10px;
            margin: 5px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
    ''')
])

@app.callback(
    Output('overview-stats', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_overview_stats(n):
    """Update the overview stats section."""
    if not cache_stats_history["timestamp"]:
        return [html.Div("No data available yet")]
    
    # Get the latest stats
    total_keys = cache_stats_history["total_keys"][-1] if cache_stats_history["total_keys"] else 0
    hit_rate = cache_stats_history["hit_rate"][-1] if cache_stats_history["hit_rate"] else 0
    miss_rate = cache_stats_history["miss_rate"][-1] if cache_stats_history["miss_rate"] else 0
    
    memory_bytes = cache_stats_history["memory_used_bytes"][-1] if cache_stats_history["memory_used_bytes"] else 0
    memory_mb = memory_bytes / (1024 * 1024)
    
    # Create stat boxes
    return [
        html.Div([
            html.Div(f"{total_keys}", className="stat-value"),
            html.Div("Total Cache Keys", className="stat-label")
        ], className="stat-box"),
        
        html.Div([
            html.Div(f"{hit_rate:.1f}%", className="stat-value"),
            html.Div("Cache Hit Rate", className="stat-label")
        ], className="stat-box"),
        
        html.Div([
            html.Div(f"{miss_rate:.1f}%", className="stat-value"),
            html.Div("Cache Miss Rate", className="stat-label")
        ], className="stat-box"),
        
        html.Div([
            html.Div(f"{memory_mb:.2f} MB", className="stat-value"),
            html.Div("Memory Usage", className="stat-label")
        ], className="stat-box"),
    ]

@app.callback(
    Output('hit-miss-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_hit_miss_chart(n):
    """Update the hit/miss rate chart."""
    if len(cache_stats_history["timestamp"]) < 2:
        # Not enough data points yet
        return go.Figure()
    
    # Convert deques to lists for plotting
    timestamps = list(cache_stats_history["timestamp"])
    hit_rates = list(cache_stats_history["hit_rate"])
    miss_rates = list(cache_stats_history["miss_rate"])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=hit_rates,
        name="Hit Rate (%)",
        line=dict(color='#2ecc71', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=miss_rates,
        name="Miss Rate (%)",
        line=dict(color='#e74c3c', width=2)
    ))
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Rate (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig

@app.callback(
    Output('memory-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_memory_chart(n):
    """Update the memory usage chart."""
    if len(cache_stats_history["timestamp"]) < 2:
        # Not enough data points yet
        return go.Figure()
    
    # Convert deques to lists for plotting
    timestamps = list(cache_stats_history["timestamp"])
    memory_bytes = list(cache_stats_history["memory_used_bytes"])
    memory_mb = [b / (1024 * 1024) for b in memory_bytes]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=memory_mb,
        name="Memory Usage (MB)",
        line=dict(color='#3498db', width=2),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Memory (MB)",
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig

@app.callback(
    Output('keys-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_keys_chart(n):
    """Update the cache keys by type chart."""
    if not cache_stats_history["timestamp"]:
        return go.Figure()
    
    # Get the latest counts
    tax_rates = cache_stats_history["tax_rates_count"][-1] if cache_stats_history["tax_rates_count"] else 0
    active_discounts = cache_stats_history["active_discounts_count"][-1] if cache_stats_history["active_discounts_count"] else 0
    invoices = cache_stats_history["invoices_count"][-1] if cache_stats_history["invoices_count"] else 0
    credit_notes = cache_stats_history["user_credit_notes_count"][-1] if cache_stats_history["user_credit_notes_count"] else 0
    
    labels = ['Tax Rates', 'Active Discounts', 'Invoices', 'Credit Notes']
    values = [tax_rates, active_discounts, invoices, credit_notes]
    colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        marker=dict(colors=colors)
    )])
    
    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig

@app.callback(
    Output('config-info', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_config_info(n):
    """Update the configuration information section."""
    try:
        info = get_redis_info()
        
        # Extract relevant configuration
        redis_version = info.get('redis_version', 'Unknown')
        uptime_days = info.get('uptime_in_days', 0)
        max_memory = info.get('maxmemory_human', 'Not set')
        max_memory_policy = info.get('maxmemory_policy', 'Unknown')
        connected_clients = info.get('connected_clients', 0)
        
        # Create config items
        return [
            html.Div([
                html.Strong("Redis Version: "),
                html.Span(redis_version)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Uptime: "),
                html.Span(f"{uptime_days} days")
            ], className="config-item"),
            
            html.Div([
                html.Strong("Max Memory: "),
                html.Span(max_memory)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Memory Policy: "),
                html.Span(max_memory_policy)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Connected Clients: "),
                html.Span(connected_clients)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Host: "),
                html.Span(settings.REDIS_HOST)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Port: "),
                html.Span(settings.REDIS_PORT)
            ], className="config-item"),
            
            html.Div([
                html.Strong("Database: "),
                html.Span(settings.REDIS_DB)
            ], className="config-item"),
        ]
    except Exception as e:
        logger.error(f"Error updating config info: {e}")
        return [html.Div("Error retrieving Redis configuration")]

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Redis Cache Dashboard")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    
    # Start the stats collection thread
    stats_thread = threading.Thread(target=collect_stats_thread, daemon=True)
    stats_thread.start()
    
    # Start the Dash app
    app.run_server(debug=args.debug, port=args.port)

if __name__ == "__main__":
    main()
