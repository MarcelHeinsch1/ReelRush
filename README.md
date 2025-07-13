# 🎬 ReelRush - AI-Powered Viral Video Generator

An advanced Multi-Agent system for automatic creation of viral TikTok videos with AI-powered trend analysis, content research, and video production.

## Features

### Multi-Agent Architecture
- **Manager Agent**: Orchestrates the entire workflow
- **Trend Analysis Agent**: Analyzes viral trends and keywords
- **Content Research Agent**: Researches content from multiple sources
- **Content Creation Agent**: Creates optimized TikTok scripts
- **Video Production Agent**: Generates videos with AI narration and subtitles
- **Music Matching Agent**: Adds fitting background music

### Intelligent Content Creation
- **Tone Control**: Adjustable content style (Humorous ↔ Informative)
- **Trend Integration**: Automatic incorporation of current trends
- **Multi-Source Research**: Web Search, ArXiv Papers, Wikipedia, YouTube
- **PDF Summarization**: Automatic summarization of PDF documents

## Installation

### Prerequisites
- **Python 3.8+**
- **Ollama** (local LLM server)
- **FFmpeg** (video/audio processing)
- **Node.js** (optional, for extended features)

### 1. Clone Repository
```bash
git clone https://github.com/
cd reelrush
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Ollama Setup
```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Download recommended models
ollama pull gemma3:12b
ollama pull gemma3:27b
ollama pull qwen3:30b

# Start Ollama server
ollama serve
```

### 4. Vosk Speech Recognition Model
```bash
# Download Vosk model for subtitle generation
mkdir -p vosk-model-small-en-us-0.15
cd vosk-model-small-en-us-0.15
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```
or just download it

### 5. Video Templates and Music
```bash
# Create folder structure
mkdir -p videos/templates
mkdir -p music/viral

# Add video templates (MP4 files)
# Add music files (MP3/WAV)
```

### 6. Install FFmpeg
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download FFmpeg from https://ffmpeg.org
```

## Usage

### Web Interface (Recommended)
```bash
python web_app.py
```
Open http://localhost:5000 in your browser

### Command Line Interface
```bash
python main.py
```

### PDF Summarization
1. Upload PDF via Web Interface
2. Automatic text extraction
3. AI-generated video summary

### GAIA Benchmark Testing
Download the benchmark and
```bash
python gaia_benchmark.py --file ./(path)/metadata.jsonl 
```

## Configuration

### Tone Settings
- **0.0 - 0.2**: Very humorous/meme-like
- **0.2 - 0.4**: Humorous with information
- **0.4 - 0.6**: Balanced
- **0.6 - 0.8**: Informative with entertainment
- **0.8 - 1.0**: Very informative/educational

### Model Configuration
```python
# config.py - Customizable AI models
MANAGER_AGENT_MODEL = "qwen3:30b"
CONTENT_CREATION_MODEL = "gemma3:12b"
TREND_ANALYSIS_MODEL = "qwen3:30b"
CONTENT_RESEARCH_MODEL = "qwen3:30b"
```

### Video Settings
```python
MIN_VIDEO_LENGTH = 30  # seconds
MAX_VIDEO_LENGTH = 90  # seconds
VIDEO_TEMPLATES_DIR = "./videos/templates"
```

## Project Structure

```
tiktok-creator/
├── main.py                 # CLI Entry Point
├── web_app.py             # Web Interface
├── manager.py             # Manager Agent
├── tools.py               # LangChain Tools
├── researchtools.py       # Research Tools
├── config.py              # Configuration
├── prompts.py             # LLM Prompts
├── logger.py              # Logging System
├── gaia_benchmark.py      # GAIA Testing
├── test.py                # Research Agent Tester
├── templates/
│   └── index.html         # Web UI
├── videos/
│   └── templates/         # Video Backgrounds
├── music/
│   └── viral/             # Background Music
├── output/                # Generated Videos
├── scripts/               # SRT Subtitles
├── audio/                 # TTS Audio
├── uploads/               # PDF Uploads
└── logs/                  # System Logs
```

## 🔧 API Endpoints

### Video Creation
```bash
POST /api/create
{
    "topic": "productivity tips",
    "settings": {
        "tone": 0.3,
        "models": {
            "manager": "qwen3:30b",
            "content": "gemma3:12b"
        }
    }
}
```

### PDF Upload
```bash
POST /api/upload-pdf
Content-Type: multipart/form-data
```

### Job Status
```bash
GET /api/status/{job_id}
```

### Download Video
```bash
GET /api/download/{job_id}
```



## Advanced Features

### PDF Processing
- **PyPDF2** or **pdfplumber** for text extraction
- Automatic author recognition
- Intelligent content summarization
- PDF-specific prompts

### Multi-Source Research
- **Web Search**: DuckDuckGo Integration
- **Academic Papers**: ArXiv API with PDF download
- **Wikipedia**: Structured information
- **YouTube**: Transcript analysis

### Video Optimization
- **Adaptive Length**: Based on content type
- **Trend Keywords**: Automatic integration
- **Emotional Hooks**: AI-generated attention triggers
- **Call-to-Action**: Optimized engagement strategies

## Performance Monitoring

### Logging System
```python
from logger import performance_tracker

@performance_tracker("MyAgent")
def my_agent_function():
    # Agent Logic
    return result
```

### Metrics
- Agent performance
- Video generation time
- Success rates
- Error tracking

## Troubleshooting

### Common Issues

**Ollama Connection Error**
```bash
# Check Ollama server status
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

**FFmpeg Error**
```bash
# Check FFmpeg installation
ffmpeg -version

# Check PATH variable
which ffmpeg
```

**PDF Extraction Error**
```bash
# Install PDF libraries
pip install PyPDF2 pdfplumber
```

**Vosk Model Error**
```bash
# Check Vosk model path
ls -la vosk-model-small-en-us-0.15/
```

### Debug Mode
```bash
# Enable verbose logging
export LANGCHAIN_VERBOSE=true
python web_app.py
```


## Acknowledgments

- **LangChain** for the agent framework
- **Ollama** for local LLM inference
- **edge-tts** for natural speech synthesis
- **Vosk** for speech recognition
- **FFmpeg** for video processing


**Created with ❤️ by YurrBS**

*Note: This tool is intended for educational and research purposes.*