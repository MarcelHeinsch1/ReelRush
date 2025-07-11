"""Web Frontend for TikTok Creator - Optional Flask Application"""

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
    """Manages a single video creation job"""

    def __init__(self, job_id: str, topic: str):
        self.job_id = job_id
        self.topic = topic
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
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "video_path": self.video_path,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "logs": self.logs
        }


def create_video_with_progress(job: VideoCreationJob):
    """Create video with manual progress tracking"""
    try:
        job.status = "initializing"
        job.update_progress("Initializing TikTok Creator", 5)

        # Create a unique config for this job using the topic
        job_config = Config(topic=job.topic, job_id=job.job_id)

        # Set config for this thread
        ConfigManager.set_config(job_config)

        # Initialize manager with unique config
        manager = ManagerAgent()
        job.update_progress("System initialized", 10)

        job.status = "processing"
        creation_timestamp = datetime.now()

        # Simulate progress based on expected timing
        # Start background progress simulation
        def simulate_progress():
            stages = [
                (15, "Starting multi-agent workflow"),
                (25, "Analyzing viral trends"),
                (35, "Searching for trending topics"),
                (45, "Researching content ideas"),
                (55, "Creating viral script"),
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

        # Actually create the video
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
    """Start video creation job"""
    data = request.json
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Create new job
    job_id = str(uuid.uuid4())
    job = VideoCreationJob(job_id, topic)
    video_jobs[job_id] = job

    # Start video creation in background
    thread = threading.Thread(target=create_video_with_progress, args=(job,))
    thread.start()

    return jsonify({
        "job_id": job_id,
        "message": "Video creation started",
        "topic": topic
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

    # Generate filename based on topic and job ID
    safe_topic = "".join(c for c in job.topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_topic = safe_topic[:50]  # Limit length
    timestamp = job.created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"tiktok_{safe_topic}_{timestamp}.mp4"

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

    print("🌐 TikTok Creator Web Frontend")
    print("=" * 50)
    print("Access the web interface at: http://localhost:5000")
    print("The original CLI tool (main.py) can still be used independently")
    print("=" * 50)

    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)