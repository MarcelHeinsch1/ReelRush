"""Logging system for TikTok Creator"""

import logging
import time
import json
import os
from functools import wraps
from typing import Dict, Any
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/tiktok_creator.log'),
        logging.StreamHandler()
    ]
)

class PerformanceLogger:
    """Simple performance tracking for agents"""

    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger('PerformanceLogger')

    def log_agent_performance(self, agent_name: str, duration: float, status: str, **kwargs):
        """Log agent performance metrics"""
        metric = {
            'agent': agent_name,
            'duration': round(duration, 2),
            'status': status,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }

        if agent_name not in self.metrics:
            self.metrics[agent_name] = []
        self.metrics[agent_name].append(metric)

        self.logger.info(f"Agent {agent_name}: {duration:.2f}s - {status}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        return self.metrics

def performance_tracker(agent_name: str):
    """Decorator to track agent performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f'Agent.{agent_name}')
            perf_logger = getattr(wrapper, '_perf_logger', PerformanceLogger())

            logger.info(f"Starting {agent_name}")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Try to parse result status
                status = "success"
                if isinstance(result, str):
                    try:
                        result_data = json.loads(result)
                        if "error" in result_data:
                            status = "error"
                    except:
                        pass

                perf_logger.log_agent_performance(agent_name, duration, status)
                logger.info(f"Completed {agent_name} in {duration:.2f}s")
                return result

            except Exception as e:
                duration = time.time() - start_time
                perf_logger.log_agent_performance(agent_name, duration, "error", error=str(e))
                logger.error(f"Failed {agent_name} after {duration:.2f}s: {e}")
                raise

        wrapper._perf_logger = PerformanceLogger()
        return wrapper
    return decorator