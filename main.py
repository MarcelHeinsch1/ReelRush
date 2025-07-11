"""Main entry point for Multi-Agent TikTok Creator - Fixed for new Config"""

import os
import subprocess
import time
import warnings
import requests
import re
from typing import Optional
from langchain_ollama import OllamaLLM
from config import Config, ConfigManager
from manager import ManagerAgent

warnings.filterwarnings("ignore")


def initialize_system() -> ManagerAgent:
    """Initialize the multi-agent system and verify all dependencies"""
    print("Initializing Multi-Agent TikTok Creator...")

    # Check required dependencies nd tools
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True)
        print("FFmpeg available")
    except:
        raise Exception("FFmpeg not found - required for video processing")

    try:
        import edge_tts
        print("edge-tts available")
    except ImportError:
        raise Exception("edge-tts not installed - required for narration")

    try:
        from duckduckgo_search import DDGS
        print("duckduckgo-search available")
    except ImportError:
        raise Exception("duckduckgo-search not installed")

    try:
        import vosk
        print("Vosk available")
    except ImportError:
        raise Exception("Vosk not installed - required for subtitles")

    # Initialize and test LLM connection
    try:
        # Use a temporary config for initialization
        temp_config = Config()
        response = requests.get(f"{temp_config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code != 200:
            raise Exception("Ollama not responding")

        llm = OllamaLLM(
            model=temp_config.MANAGER_AGENT_MODEL,
            base_url=temp_config.OLLAMA_BASE_URL,
            timeout=60,
            temperature=0.7
        )

        test_response = llm.invoke("Respond with just 'READY'")

        if not test_response or "READY" not in test_response.upper():
            raise Exception("LLM test failed")

        print(f"✅ LLM connected: {temp_config.MANAGER_AGENT_MODEL}")

    except Exception as e:
        raise Exception(f"LLM initialization failed: {e}")

    manager = ManagerAgent()
    print("✅ Multi-Agent System ready with LangChain tools")
    return manager


def create_video_simple(topic: str) -> Optional[str]:
    """Simple API for video creation - returns path to created video"""
    # Create a unique config for this video based on topic
    video_config = Config(topic=topic)
    ConfigManager.set_config(video_config)

    try:
        manager = initialize_system()
        result = manager.create_viral_video(topic)

        if result["status"] == "success":
            print("📋 Agent Execution Log:")
            print(result.get("agent_output", "No detailed output available"))

            output_text = result.get("agent_output", "")
            if "video_with_music" in output_text:
                matches = re.findall(r'"video_with_music":\s*"([^"]+)"', output_text)
                if matches:
                    video_path = matches[0]
                    if os.path.exists(video_path):
                        size_mb = os.path.getsize(video_path) / (1024 * 1024)
                        print(f"📁 Video: {video_path} ({size_mb:.1f}MB)")
                        return video_path

            output_dir = "./output"
            if os.path.exists(output_dir):
                mp4_files = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
                if mp4_files:
                    latest_file = max(
                        [os.path.join(output_dir, f) for f in mp4_files],
                        key=os.path.getmtime
                    )
                    size_mb = os.path.getsize(latest_file) / (1024 * 1024)
                    print(f"📁 Found video: {latest_file} ({size_mb:.1f}MB)")
                    return latest_file

            print("⚠️ Video creation completed but file not found")
            return None
        else:
            raise Exception(f"Video creation failed: {result.get('error', 'Unknown error')}")
    finally:
        # Clean up thread config
        ConfigManager.clear_config()


def main():
    """Main function to run the TikTok creator"""
    print("🎬 Multi-Agent TikTok Creator with LangChain Tools")
    print("Requires: Ollama+models, Vosk, edge-tts, FFmpeg, duckduckgo-search")
    print("Features: LLM Manager Agent, Web Search für Content Research, Automated Workflow")
    print("=" * 80)

    topic = input("Enter video topic: ").strip()
    if not topic:
        print("Topic is required")
        return

    start_time = time.time()
    try:
        video_path = create_video_simple(topic)
        duration = time.time() - start_time

        if video_path:
            print(f"Success! Video created in {duration:.1f}s")
            print(f"{video_path}")
        else:
            print(f"⚠Process completed in {duration:.1f}s but no video file found")

    except Exception as e:
        duration = time.time() - start_time
        print(f"Failed after {duration:.1f}s: {e}")
        raise


if __name__ == "__main__":
    main()