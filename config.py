"""Configuration file for TikTok Creator"""

from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class containing all system paths and settings"""
    # Paths
    VIDEO_TEMPLATES_DIR: str = "./videos/templates"
    SCRIPT_OUTPUT_PATH: str = "./scripts/output.srt"
    AUDIO_OUTPUT_PATH: str = "./audio/narration.wav"
    FINAL_OUTPUT_PATH: str = "./output/final_video.mp4"

    # Video settings
    MIN_VIDEO_LENGTH: int = 30
    MAX_VIDEO_LENGTH: int = 90

    # LLM Configuration - separate models for each agent
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Individual LLM models for each agent
    TREND_ANALYSIS_MODEL: str = "qwen3:30b"
    CONTENT_RESEARCH_MODEL: str = "qwen3:30b"
    CONTENT_CREATION_MODEL: str = "qwen3:30b"
    VIDEO_PRODUCTION_MODEL: str = "qwen3:30b"
    MUSIC_MATCHING_MODEL: str = "qwen3:30b"
    MANAGER_AGENT_MODEL: str = "qwen3:30b"


config = Config()