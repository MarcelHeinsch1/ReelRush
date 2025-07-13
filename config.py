"""Configuration file for TikTok Creator - Enhanced with tone settings support"""

from dataclasses import dataclass
import threading
import time
import os
import re
from typing import Dict, Any


@dataclass
class Config:
    """Configuration class containing all system paths and settings"""

    def __init__(self, topic: str = None, job_id: str = None, settings: Dict[str, Any] = None):
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

        # Store enhanced settings
        self.settings = settings or {}

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

    # Enhanced settings accessors
    @property
    def TONE_VALUE(self) -> float:
        """Get tone value (0.0 = humorous, 1.0 = informative)"""
        return self.settings.get('tone', 0.5)

    @property
    def TONE_DESCRIPTION(self) -> str:
        """Get human-readable tone description"""
        tone = self.TONE_VALUE
        if tone < 0.2:
            return "Very Humorous/Memey"
        elif tone < 0.4:
            return "Humorous with Some Info"
        elif tone < 0.6:
            return "Balanced"
        elif tone < 0.8:
            return "Informative with Some Fun"
        else:
            return "Very Informative/Educational"

    @property
    def TONE_MODIFIER(self) -> str:
        """Get detailed tone modifier for prompts"""
        tone = self.TONE_VALUE

        if tone < 0.2:
            return """
TONE: VERY HUMOROUS/MEMEY (Focus: Entertainment & Virality)
- Use internet slang, memes, and trending phrases heavily
- Include lots of emojis and expressive language  
- Focus on entertainment over education
- Use humor, jokes, and funny comparisons
- Reference popular culture and viral trends extensively
- Make it highly shareable and relatable
- Use casual, Gen-Z friendly language
- Priority: 90% fun/engagement, 10% information
"""
        elif tone < 0.4:
            return """
TONE: HUMOROUS (Focus: Fun with Some Useful Info)
- Balance entertainment with some useful information
- Use casual, friendly language with regular humor
- Include memes and trending references
- Make facts entertaining and easy to digest
- Use engaging storytelling with funny elements
- Keep it light-hearted but somewhat informative
- Priority: 70% entertainment, 30% information
"""
        elif tone < 0.6:
            return """
TONE: BALANCED (Focus: Equal Entertainment & Information)
- Mix entertainment and information equally
- Use conversational but informative tone
- Include both fun facts and useful information
- Make content engaging but educational
- Use relatable examples with moderate humor
- Appeal to broad audience
- Priority: 50% entertainment, 50% information
"""
        elif tone < 0.8:
            return """
TONE: INFORMATIVE (Focus: Educational with Engagement)
- Focus on providing valuable, actionable information
- Use clear, educational language that's still engaging
- Include facts, tips, and useful insights
- Make content authoritative but accessible
- Use professional but friendly tone
- Add some engaging elements to maintain interest
- Priority: 70% information, 30% entertainment
"""
        else:
            return """
TONE: VERY INFORMATIVE/EDUCATIONAL (Focus: Deep Knowledge)
- Focus entirely on educational, valuable content
- Use professional, authoritative language
- Include detailed facts, statistics, and expert insights
- Prioritize accuracy and depth of information
- Use academic or expert-level explanations when appropriate
- Minimize entertainment elements
- Make it comprehensive and trustworthy
- Priority: 90% information, 10% engagement
"""

    # Model configuration accessors
    def get_model(self, agent_type: str) -> str:
        """Get model for specific agent type"""
        models = self.settings.get('models', {})
        defaults = {
            'manager': 'qwen3:30b',
            'content': 'gemma3:12b',
            'trend': 'qwen3:30b',
            'research': 'qwen3:30b',
            'video': 'qwen3:30b',
            'music': 'qwen3:30b'
        }
        return models.get(agent_type, defaults.get(agent_type, 'gemma3:12b'))

    # Dynamic model properties
    @property
    def MANAGER_AGENT_MODEL(self) -> str:
        return self.get_model('manager')

    @property
    def CONTENT_CREATION_MODEL(self) -> str:
        return self.get_model('content')

    @property
    def TREND_ANALYSIS_MODEL(self) -> str:
        return self.get_model('trend')

    @property
    def CONTENT_RESEARCH_MODEL(self) -> str:
        return self.get_model('research')

    @property
    def VIDEO_PRODUCTION_MODEL(self) -> str:
        return self.get_model('video')

    @property
    def MUSIC_MATCHING_MODEL(self) -> str:
        return self.get_model('music')

    # Video settings
    MIN_VIDEO_LENGTH: int = 30
    MAX_VIDEO_LENGTH: int = 90

    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"


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