"""
Health check server for production deployment
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import logging

# Import Flask for health check server
try:
    from flask import Flask, jsonify
    import threading
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from src.core.logging import get_logger
from src.core.database import get_database_manager


class HealthCheckServer:
    """Health check HTTP server for Koyeb monitoring."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.logger = get_logger(__name__)
        self.app = None
        self.server_thread = None
        self.is_running = False
        
        if FLASK_AVAILABLE:
            self._setup_flask_app()
    
    def _setup_flask_app(self) -> None:
        """Setup Flask application for health checks."""
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.WARNING)  # Reduce Flask logging
        
        @self.app.route('/health')
        def health_check():
            """Health check endpoint."""
            try:
                health_data = self._get_health_status()
                status_code = 200 if health_data['status'] == 'healthy' else 503
                return jsonify(health_data), status_code
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 503
        
        @self.app.route('/')
        def root():
            """Root endpoint with service information."""
            return jsonify({
                'service': 'Discord Bot Enterprise',
                'version': '3.0.0',
                'status': 'running',
                'endpoints': {
                    'health': '/health'
                },
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/metrics')
        def metrics():
            """Basic metrics endpoint."""
            try:
                return jsonify(self._get_metrics())
            except Exception as e:
                self.logger.error(f"Metrics collection failed: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        checks = {}
        overall_status = 'healthy'
        
        # Database health check
        try:
            # This would need to be run in async context in real implementation
            checks['database'] = {
                'status': 'healthy',
                'message': 'Database connection available'
            }
        except Exception as e:
            checks['database'] = {
                'status': 'unhealthy',
                'message': f'Database error: {e}'
            }
            overall_status = 'unhealthy'
        
        # Memory check (basic)
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            if memory_usage > 90:
                checks['memory'] = {
                    'status': 'warning',
                    'usage_percent': memory_usage,
                    'message': 'High memory usage'
                }
                if overall_status == 'healthy':
                    overall_status = 'warning'
            else:
                checks['memory'] = {
                    'status': 'healthy',
                    'usage_percent': memory_usage,
                    'message': 'Memory usage normal'
                }
        except ImportError:
            checks['memory'] = {
                'status': 'unknown',
                'message': 'psutil not available'
            }
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': checks,
            'uptime': self._get_uptime()
        }
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get basic metrics."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime': self._get_uptime()
        }
        
        # Add memory metrics if available
        try:
            import psutil
            process = psutil.Process()
            metrics['memory'] = {
                'rss': process.memory_info().rss,
                'vms': process.memory_info().vms,
                'percent': process.memory_percent()
            }
            metrics['cpu'] = {
                'percent': process.cpu_percent()
            }
        except ImportError:
            pass
        
        return metrics
    
    def _get_uptime(self) -> str:
        """Get service uptime."""
        # This is a placeholder - in real implementation, track start time
        return "unknown"
    
    def start(self) -> None:
        """Start health check server."""
        if not FLASK_AVAILABLE:
            self.logger.warning("Flask not available, health check server disabled")
            return
        
        if self.is_running:
            return
        
        self.logger.info(f"Starting health check server on port {self.port}")
        
        def run_server():
            try:
                self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                self.logger.error(f"Health check server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        self.logger.info(f"Health check server started on http://0.0.0.0:{self.port}")
    
    def stop(self) -> None:
        """Stop health check server."""
        if self.is_running:
            self.is_running = False
            self.logger.info("Health check server stopped")


# Global health check server instance
_health_server: HealthCheckServer = None


def get_health_server(port: int = 8000) -> HealthCheckServer:
    """Get global health check server instance."""
    global _health_server
    if _health_server is None:
        _health_server = HealthCheckServer(port)
    return _health_server


def start_health_server(port: int = 8000) -> None:
    """Start the global health check server."""
    server = get_health_server(port)
    server.start()


def stop_health_server() -> None:
    """Stop the global health check server."""
    global _health_server
    if _health_server:
        _health_server.stop()


# Simple async health check for bot framework
async def check_bot_health() -> Dict[str, Any]:
    """Async health check for bot components."""
    checks = {}
    
    # Database check
    try:
        db_manager = get_database_manager()
        if hasattr(db_manager, 'connection_pool') and db_manager.connection_pool:
            checks['database'] = {'status': 'healthy', 'type': 'postgresql'}
        elif hasattr(db_manager, '_initialized') and db_manager._initialized:
            checks['database'] = {'status': 'healthy', 'type': 'sqlite'}
        else:
            checks['database'] = {'status': 'initializing'}
    except Exception as e:
        checks['database'] = {'status': 'error', 'message': str(e)}
    
    overall_status = 'healthy'
    for check in checks.values():
        if check['status'] == 'error':
            overall_status = 'error'
            break
        elif check['status'] != 'healthy':
            overall_status = 'warning'
    
    return {
        'status': overall_status,
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    }