"""Configuration file for TikTok Creator - With dynamic unique paths and integrated ConfigManager"""

from dataclasses import dataclass
import threading
import time
import os
import re
from typing import Optional


@dataclass
class Config:
    """Configuration class containing all system paths and settings"""

    def __init__(self, topic: str = None, job_id: str = None):
        # Create safe filename from topic
        if topic:
            # Remove special characters and limit length
            safe_topic = re.sub(r'[^\w\s-]', '', topic).strip()
            safe_topic = re.sub(r'[-\s]+', '_', safe_topic)[:30]
            # Add timestamp for uniqueness
            timestamp = str(int(time.time()))
            self._session_id = f"{safe_topic}_{timestamp}"
        elif job_id:
            # Fallback to job_id if no topic
            self._session_id = job_id[:8]
        else:
            # Default fallback
            self._session_id = str(int(time.time()))

    # Paths
    VIDEO_TEMPLATES_DIR: str = "./videos/templates"

    def get_script_output_path(self) -> str:
        os.makedirs("./scripts", exist_ok=True)
        return f"./scripts/{self._session_id}_script.srt"

    def get_audio_output_path(self) -> str:
        os.makedirs("./audio", exist_ok=True)
        return f"./audio/{self._session_id}_narration.wav"

    def get_final_output_path(self) -> str:
        os.makedirs("./output", exist_ok=True)
        return f"./output/{self._session_id}_tiktok.mp4"

    # For backwards compatibility, keep the property names
    @property
    def SCRIPT_OUTPUT_PATH(self) -> str:
        return self.get_script_output_path()

    @property
    def AUDIO_OUTPUT_PATH(self) -> str:
        return self.get_audio_output_path()

    @property
    def FINAL_OUTPUT_PATH(self) -> str:
        return self.get_final_output_path()

    # Video settings
    MIN_VIDEO_LENGTH: int = 30
    MAX_VIDEO_LENGTH: int = 90

    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Individual LLM models
    agent = "gemma3:12b"
    MANAGER_AGENT_MODEL: str = agent
    CONTENT_CREATION_MODEL: str = agent
    TREND_ANALYSIS_MODEL: str = "qwen3:30b"
    CONTENT_RESEARCH_MODEL: str = "qwen3:30b"
    VIDEO_PRODUCTION_MODEL: str = "qwen3:30b"
    MUSIC_MATCHING_MODEL: str = "qwen3:30b"


class ConfigManager:
    """Manages configs per thread to ensure unique paths for each job"""

    _thread_configs = {}
    _lock = threading.Lock()

    @classmethod
    def get_config(cls) -> Config:
        """Get config for current thread"""
        thread_id = threading.current_thread().ident

        with cls._lock:
            if thread_id not in cls._thread_configs:
                # Return default config if not in a job thread
                return Config()
            return cls._thread_configs[thread_id]

    @classmethod
    def set_config(cls, config: Config):
        """Set config for current thread"""
        thread_id = threading.current_thread().ident

        with cls._lock:
            cls._thread_configs[thread_id] = config

    @classmethod
    def clear_config(cls):
        """Clear config for current thread"""
        thread_id = threading.current_thread().ident

        with cls._lock:
            if thread_id in cls._thread_configs:
                del cls._thread_configs[thread_id]


# Create a proxy class that delegates to ConfigManager
class ConfigProxy:
    """Proxy that automatically uses thread-local configs"""

    def __getattr__(self, name):
        return getattr(ConfigManager.get_config(), name)

    def __repr__(self):
        return repr(ConfigManager.get_config())


# Default config instance that uses ConfigManager
config = ConfigProxy()