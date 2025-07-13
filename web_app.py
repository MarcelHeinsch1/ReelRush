"""Web Frontend for TikTok Creator - Enhanced with Settings Support"""

import os
import json
import time
import threading
import uuid
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Optional
import logging

# Import config with integrated ConfigManager
from config import Config, ConfigManager
from manager import ManagerAgent

app = Flask(__name__)
CORS(app)

# Configure logging for web app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WebFrontend')

# Store video creation jobs
video_jobs = {}


class VideoCreationJob:
    """Manages a single video creation job with enhanced settings"""

    def __init__(self, job_id: str, topic: str, settings: Dict = None):
        self.job_id = job_id
        self.topic = topic
        self.settings = settings or {}
        self.status = "pending"
        self.progress = 0
        self.video_path = None
        self.error = None
        self.created_at = datetime.now()
        self.completed_at = None
        self.logs = []
        self.current_stage = ""

    def add_log(self, message: str):
        """Add a log message with timestamp"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })

    def update_progress(self, stage: str, progress: int):
        """Update progress and current stage"""
        self.current_stage = stage
        self.progress = progress
        self.add_log(f"{stage}")

    def to_dict(self) -> Dict:
        """Convert job to dictionary for JSON response"""
        return {
            "job_id": self.job_id,
            "topic": self.topic,
            "settings": self.settings,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "video_path": self.video_path,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "logs": self.logs
        }


def create_enhanced_prompt_modifier(tone_value: float) -> str:
    """Create prompt modifier based on tone setting"""
    if tone_value < 0.2:
        return """
TONE MODIFIER - VERY HUMOROUS/MEMEY:
- Use lots of internet slang, memes, and trending phrases
- Include emojis and expressive language
- Focus on entertainment over education
- Use humor, jokes, and funny comparisons
- Reference popular culture and viral trends
- Make it shareable and relatable
- Priority: Fun and engagement over facts
"""
    elif tone_value < 0.4:
        return """
TONE MODIFIER - HUMOROUS:
- Balance entertainment with some useful info
- Use casual, friendly language with humor
- Include some memes and trending references
- Make facts entertaining and easy to digest
- Use engaging storytelling with funny elements
- Priority: 70% entertainment, 30% information
"""
    elif tone_value < 0.6:
        return """
TONE MODIFIER - BALANCED:
- Mix entertainment and information equally
- Use conversational but informative tone
- Include both fun facts and useful information
- Make content engaging but educational
- Use relatable examples and moderate humor
- Priority: 50% entertainment, 50% information
"""
    elif tone_value < 0.8:
        return """
TONE MODIFIER - INFORMATIVE:
- Focus on providing valuable information
- Use clear, educational language
- Include facts, tips, and useful insights
- Make content authoritative but accessible
- Use professional but engaging tone
- Priority: 70% information, 30% entertainment
"""
    else:
        return """
TONE MODIFIER - VERY INFORMATIVE/EDUCATIONAL:
- Focus entirely on educational content
- Use professional, authoritative language
- Include detailed facts, statistics, and insights
- Prioritize accuracy and depth of information
- Use academic or expert-level explanations
- Minimize entertainment elements
- Priority: 90% information, 10% engagement
"""


def create_video_with_progress(job: VideoCreationJob):
    """Create video with manual progress tracking and enhanced settings"""
    try:
        job.status = "initializing"
        job.update_progress("Initializing TikTok Creator with custom settings", 5)

        # Create a unique config for this job using the topic and settings
        job_config = Config(topic=job.topic, job_id=job.job_id, settings=job.settings)

        # Set config for this thread
        ConfigManager.set_config(job_config)

        # Initialize manager with unique config
        manager = ManagerAgent()
        job.update_progress("System initialized", 10)

        job.status = "processing"
        creation_timestamp = datetime.now()

        # Apply tone settings to the manager/prompts
        tone_value = job.settings.get('tone', 0.5)
        tone_modifier = create_enhanced_prompt_modifier(tone_value)

        job.add_log(f"Applying tone setting: {tone_value:.1f} ({'Humorous' if tone_value < 0.5 else 'Informative'})")

        # Simulate progress based on expected timing
        def simulate_progress():
            stages = [
                (15, "Starting multi-agent workflow"),
                (25, f"Analyzing viral trends ({'humor-focused' if tone_value < 0.5 else 'info-focused'})"),
                (35, "Searching for trending topics"),
                (45, "Researching content ideas"),
                (55, f"Creating {'entertaining' if tone_value < 0.5 else 'informative'} script"),
                (65, "Generating AI narration"),
                (75, "Processing video templates"),
                (85, "Adding dynamic subtitles"),
                (92, "Adding background music"),
                (95, "Finalizing video")
            ]

            start = time.time()
            for target_progress, stage in stages:
                if job.status != "processing":
                    break
                # Wait proportionally (assume 2 minutes total)
                wait_time = (target_progress / 100) * 120 - (time.time() - start)
                if wait_time > 0:
                    time.sleep(min(wait_time, 10))  # Max 10 seconds between updates
                if job.status == "processing":
                    job.update_progress(stage, target_progress)

        # Start progress simulation in background
        progress_thread = threading.Thread(target=simulate_progress)
        progress_thread.daemon = True
        progress_thread.start()

        # Actually create the video (no need to modify topic here, tools will use config settings)
        start_time = time.time()
        result = manager.create_viral_video(job.topic)
        duration = time.time() - start_time

        # Stop progress simulation
        job.status = "finalizing"

        # Find the video file
        video_path = None

        if result.get("status") == "success":
            # Parse output for video path
            output_text = result.get("agent_output", "")

            # Look for video paths in the output
            import re
            video_patterns = [
                r'"video_with_music":\s*"([^"]+)"',
                r'"video_path":\s*"([^"]+)"',
                r'Video:\s*([^\s]+\.mp4)',
                r'File:\s*([^\s]+\.mp4)'
            ]

            for pattern in video_patterns:
                matches = re.findall(pattern, output_text)
                if matches:
                    for match in reversed(matches):  # Check latest mentions first
                        if os.path.exists(match):
                            video_path = match
                            break
                if video_path:
                    break

        # If not found in output, check output directory
        if not video_path:
            output_dir = "./output"
            if os.path.exists(output_dir):
                # Get all MP4 files created after job start
                candidates = []
                for f in os.listdir(output_dir):
                    if f.endswith('.mp4'):
                        file_path = os.path.join(output_dir, f)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time >= creation_timestamp:
                            candidates.append((file_path, file_time, 'music' in f))

                if candidates:
                    # Sort by: prefer files with 'music' in name, then by newest
                    candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
                    video_path = candidates[0][0]

        if video_path and os.path.exists(video_path):
            job.video_path = os.path.abspath(video_path)
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now()

            # Get file info
            size_mb = os.path.getsize(job.video_path) / (1024 * 1024)
            job.update_progress("Video completed!", 100)
            job.add_log(f"Duration: {duration:.1f}s | Size: {size_mb:.1f}MB")
            job.add_log(f"File: {os.path.basename(job.video_path)}")
            job.add_log(f"Tone: {'Humorous' if tone_value < 0.5 else 'Informative'} ({tone_value:.1f})")

            # Clear thread config
            ConfigManager.clear_config()
        else:
            # Clear thread config even on failure
            ConfigManager.clear_config()
            raise Exception("Video file not found after creation")

    except Exception as e:
        # Make sure to clear config on error
        ConfigManager.clear_config()
        job.status = "failed"
        job.error = str(e)
        job.completed_at = datetime.now()
        job.add_log(f"Error: {str(e)}")
        logger.error(f"Video creation failed for job {job.job_id}: {e}")


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/create', methods=['POST'])
def create_video():
    """Start video creation job with enhanced settings support"""
    data = request.json
    topic = data.get('topic', '').strip()
    settings = data.get('settings', {})

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Validate settings
    tone = settings.get('tone', 0.5)
    if not (0 <= tone <= 1):
        return jsonify({"error": "Tone must be between 0 and 1"}), 400

    # Create new job with settings
    job_id = str(uuid.uuid4())
    job = VideoCreationJob(job_id, topic, settings)
    video_jobs[job_id] = job

    # Log settings
    logger.info(f"Creating video for '{topic}' with settings: {settings}")
    job.add_log(f"Settings - Tone: {tone:.2f} ({'Humorous' if tone < 0.5 else 'Informative'})")

    # Start video creation in background
    thread = threading.Thread(target=create_video_with_progress, args=(job,))
    thread.start()

    return jsonify({
        "job_id": job_id,
        "message": "Video creation started",
        "topic": topic,
        "settings": settings
    })


@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get status of video creation job"""
    job = video_jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict())


@app.route('/api/download/<job_id>')
def download_video(job_id):
    """Download the created video"""
    job = video_jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status != "completed" or not job.video_path:
        return jsonify({"error": "Video not ready"}), 400

    # Use the stored absolute path
    video_file = job.video_path

    if not os.path.exists(video_file):
        logger.error(f"Video file not found at: {video_file}")
        return jsonify({"error": f"Video file not found at: {video_file}"}), 404

    # Generate filename based on topic, settings and job ID
    safe_topic = "".join(c for c in job.topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_topic = safe_topic[:50]  # Limit length
    timestamp = job.created_at.strftime("%Y%m%d_%H%M%S")

    # Add tone info to filename
    tone_value = job.settings.get('tone', 0.5)
    tone_suffix = "humorous" if tone_value < 0.5 else "informative"

    filename = f"tiktok_{safe_topic}_{tone_suffix}_{timestamp}.mp4"

    logger.info(f"Serving video file: {video_file} as {filename}")

    return send_file(
        video_file,
        as_attachment=True,
        download_name=filename,
        mimetype='video/mp4'
    )


@app.route('/api/jobs')
def list_jobs():
    """List all video creation jobs"""
    jobs_list = [job.to_dict() for job in video_jobs.values()]
    # Sort by creation date, newest first
    jobs_list.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(jobs_list)


@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_videos():
    """Clean up old video files and jobs"""
    try:
        cleaned = 0
        # Remove completed jobs older than 1 hour
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, job in video_jobs.items():
            if job.completed_at:
                age = current_time - job.completed_at
                if age.total_seconds() > 3600:  # 1 hour
                    jobs_to_remove.append(job_id)
                    # Delete video file if exists
                    if job.video_path and os.path.exists(job.video_path):
                        os.remove(job.video_path)
                        cleaned += 1

        # Remove jobs from memory
        for job_id in jobs_to_remove:
            del video_jobs[job_id]

        return jsonify({
            "message": f"Cleaned up {cleaned} old videos",
            "removed_jobs": len(jobs_to_remove)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    print("🌐 TikTok Creator Web Frontend - Enhanced Version")
    print("=" * 50)
    print("New Features:")
    print("✨ Content Tone Control (Humorous ↔ Informative)")
    print("🎯 Advanced Settings Panel")
    print("📊 Enhanced Job Tracking")
    print("=" * 50)
    print("Access the web interface at: http://localhost:5000")
    print("The original CLI tool (main.py) can still be used independently")
    print("=" * 50)

    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)