"""LangChain tools for TikTok Creator - Enhanced with tone support and FIXED PDF mode"""

import os
import subprocess
import random
import json
import time
import asyncio
import re
import wave
from typing import Dict, List, Optional, Any
import edge_tts
import vosk
from langchain.tools import BaseTool
from langchain_ollama import OllamaLLM
from duckduckgo_search import DDGS

import prompts
from config import config
from prompts import CONTENT_CREATION_PROMPT, PDF_CONTENT_CREATION_PROMPT
from logger import performance_tracker
import logging

# Erstelle logs Ordner wenn nicht vorhanden
os.makedirs('./logs', exist_ok=True)


class TrendAnalysisTool(BaseTool):
    """LangChain tool for analyzing viral trends and getting trending topics via web search"""
    name: str = "trend_analysis"
    description: str = "Analyze viral trends and get trending topics for a given query using web search"

    @performance_tracker("TrendAnalysis")
    def _run(self, query: str) -> str:
        logger = logging.getLogger('TrendAnalysisTool')
        logger.info(f"Analyzing trends for: {query}")

        try:
            time.sleep(2)
            ddgs = DDGS(timeout=20)
            search_queries = [
                f"{query} trending 2025",
                f"{query} viral content",
                f"popular {query} topics"
            ]

            all_results = []
            for i, search_query in enumerate(search_queries):
                try:
                    if i > 0:
                        time.sleep(3)
                    results = list(ddgs.text(search_query, max_results=5))
                    all_results.extend(results)
                    if len(all_results) >= 10:
                        break
                except Exception as e:
                    logger.warning(f"Search attempt {i + 1} failed: {e}")
                    print(f"Search attempt {i + 1} failed: {e}")
                    continue

            if not all_results:
                logger.error("No search results available")
                return json.dumps({
                    "trending_topics": [],
                    "recommended_keywords": [],
                    "viral_scores": {},
                    "search_results_count": 0,
                    "error": "No search results available"
                })

            trending_topics = []
            keywords = []

            for result in all_results:
                title_words = result["title"].lower().split()
                snippet_words = result["body"][:200].lower().split()
                all_words = title_words + snippet_words
                filtered_words = [w for w in all_words if len(w) > 3 and w.isalpha()]
                keywords.extend(filtered_words)
                if len(result["title"]) < 120:
                    trending_topics.append(result["title"])

            unique_keywords = list(set(keywords))[:20]
            trending_topics = trending_topics[:10]

            result_data = {
                "trending_topics": trending_topics,
                "recommended_keywords": unique_keywords,
                "viral_scores": {topic: random.randint(75, 98) for topic in trending_topics[:5]},
                "search_results_count": len(all_results)
            }

            logger.info(f"Found {len(trending_topics)} trending topics and {len(unique_keywords)} keywords")
            return json.dumps(result_data)

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return json.dumps({
                "trending_topics": [],
                "recommended_keywords": [],
                "viral_scores": {},
                "search_results_count": 0,
                "error": f"Search failed: {str(e)}"
            })


# ContentResearchTool is imported from researchtools.py


class ContentCreationTool(BaseTool):
    """LangChain tool for creating TikTok scripts based on topic, trends, and research data with tone and PDF support"""
    name: str = "content_creation"
    description: str = "Create TikTok script based on topic, trends, research data, or PDF content with tone customization"

    def __init__(self):
        super().__init__()
        self._llm = OllamaLLM(
            model=config.CONTENT_CREATION_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            timeout=60,
            temperature=0.7
        )

    @performance_tracker("ContentCreation")
    def _run(self, input_data: str) -> str:
        logger = logging.getLogger('ContentCreationTool')

        try:
            data = json.loads(input_data)
            topic = data.get("topic", "")

            # FIXED: Check for PDF mode properly
            is_pdf_mode = (
                "PDF Summary:" in topic or
                data.get("pdf_content") or
                data.get("pdf_mode") or
                config.settings.get('pdf_mode', False)
            )

            if is_pdf_mode:
                logger.info("Creating PDF summary TikTok script")
                return self._create_pdf_summary_script(data)
            else:
                logger.info("Creating regular TikTok script")
                return self._create_regular_script(data)

        except Exception as e:
            logger.error(f"Content creation tool failed: {e}")
            return json.dumps({"error": f"Content creation tool failed: {str(e)}"})

    def _create_pdf_summary_script(self, data: Dict) -> str:
        """Create TikTok script specifically for PDF summarization"""
        logger = logging.getLogger('ContentCreationTool')

        topic = data.get("topic", "")
        pdf_content = data.get("pdf_content", "")
        main_insights = data.get("main_insights", [])
        surprising_facts = data.get("surprising_facts", [])

        # Extract author names from PDF content
        author_names = self._extract_author_names(pdf_content)

        # Get tone settings
        tone_modifier = config.TONE_MODIFIER
        tone_description = config.TONE_DESCRIPTION
        tone_value = config.TONE_VALUE

        logger.info(f"Creating PDF summary with tone: {tone_description} (value: {tone_value:.2f})")
        if author_names:
            logger.info(f"Extracted authors: {', '.join(author_names)}")

        # FIXED: Use the correct PDF prompt with proper formatting
        prompt = PDF_CONTENT_CREATION_PROMPT.format(
            topic=topic,
            tone_modifier=tone_modifier,
            tone_description=tone_description,
            pdf_content=pdf_content[:2000],  # Limit content size
            main_insights=str(main_insights),
            surprising_facts=str(surprising_facts)
        )

        return self._generate_script_with_prompt(prompt, tone_description, is_pdf=True)

    def _extract_author_names(self, pdf_content: str) -> List[str]:
        """Extract potential author names from PDF content"""
        import re

        authors = []

        # Common patterns for author names in academic papers
        patterns = [
            # "Author Name1, Author Name2" format
            r'(?:Authors?|By):?\s*([A-Z][a-z]+ [A-Z][a-z]+(?:,\s*[A-Z][a-z]+ [A-Z][a-z]+)*)',
            # Names at beginning of document
            r'^([A-Z][a-z]+ [A-Z][a-z]+(?:,\s*[A-Z][a-z]+ [A-Z][a-z]+)*)',
            # Names followed by affiliation patterns
            r'([A-Z][a-z]+ [A-Z][a-z]+)(?:\s*[,\d]|\s*\n|\s*Department|\s*University|\s*Institute)',
        ]

        # Look in first 1000 characters where authors are typically mentioned
        text_start = pdf_content[:1000]

        for pattern in patterns:
            matches = re.findall(pattern, text_start, re.MULTILINE)
            for match in matches:
                # Split by comma and clean up
                names = [name.strip() for name in match.split(',')]
                for name in names:
                    # Basic validation: name should have 2+ words, reasonable length
                    if (len(name.split()) >= 2 and
                        len(name) < 50 and
                        name not in authors and
                        not any(word.lower() in ['abstract', 'university', 'department', 'institute'] for word in name.split())):
                        authors.append(name)

        # Limit to first 3 authors to keep it concise
        return authors[:3]

    def _create_regular_script(self, data: Dict) -> str:
        """Create regular TikTok script for trending topics"""
        topic = data.get("topic", "")
        trends = data.get("trends", [])
        keywords = data.get("keywords", [])
        hooks = data.get("hooks", [])
        formats = data.get("formats", [])

        # Get tone settings
        tone_modifier = config.TONE_MODIFIER
        tone_description = config.TONE_DESCRIPTION

        trend_text = ", ".join(trends[:6]) if trends else ""
        keyword_text = ", ".join(keywords[:12]) if keywords else ""
        hook_text = " | ".join(hooks[:5]) if hooks else ""
        format_text = " | ".join(formats[:4]) if formats else ""

        prompt = CONTENT_CREATION_PROMPT.format(
            topic=topic,
            tone_modifier=tone_modifier,
            tone_description=tone_description,
            trend_text=trend_text,
            keyword_text=keyword_text,
            hook_text=hook_text,
            format_text=format_text
        )

        return self._generate_script_with_prompt(prompt, tone_description, is_pdf=False)

    def _generate_script_with_prompt(self, prompt: str, tone_description: str, is_pdf: bool = False) -> str:
        """Generate script using the LLM with the given prompt"""
        logger = logging.getLogger('ContentCreationTool')

        for attempt in range(3):
            try:
                response = self._llm.invoke(prompt)
                content = self._extract_json(response)
                if content:
                    validated_content = self._validate_content(content, tone_description, is_pdf)
                    content_type = "PDF summary" if is_pdf else "regular content"
                    logger.info(
                        f"Script generated successfully for {content_type} with tone: {validated_content.get('tone_applied', 'unknown')}")
                    return json.dumps(validated_content)
                else:
                    if attempt == 2:
                        logger.error("Failed to generate valid JSON after 3 attempts")
                        return json.dumps({"error": "Failed to generate valid JSON after 3 attempts"})
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Content generation failed: {e}")
                    return json.dumps({"error": f"Content generation failed: {str(e)}"})

    def _extract_json(self, response: str) -> Optional[Dict]:
        """Extract JSON from LLM response"""
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end])
            except:
                pass

        cleaned = re.sub(r'```json|```|\n', '', response)
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except:
                pass
        return None

    def _validate_content(self, content: Dict, tone_description: str, is_pdf: bool = False) -> Dict[str, Any]:
        """Validate and enhance the generated content"""
        video_length = content.get('video_length', 45 if is_pdf else 35)
        try:
            video_length = max(config.MIN_VIDEO_LENGTH, min(int(video_length), config.MAX_VIDEO_LENGTH))
        except:
            video_length = 45 if is_pdf else 35

        script_text = content.get('script_text', '')
        if not script_text:
            raise Exception("No script text generated")

        # Enhanced validation for PDF content
        if is_pdf:
            # Check if script mentions document/research/findings (PDF-appropriate language)
            pdf_indicators = ['document', 'research', 'study', 'findings', 'reveals', 'shows', 'according to']
            has_pdf_context = any(indicator in script_text.lower() for indicator in pdf_indicators)

            if not has_pdf_context and len(script_text) > 50:
                # Add PDF context if missing
                script_text = f"This document reveals something incredible. {script_text}"

        return {
            "video_length": video_length,
            "script_text": script_text,
            "hook": content.get('hook', ''),
            "main_points": content.get('main_points', []),
            "cta": content.get('cta', ''),
            "trending_elements": content.get('trending_elements', []),
            "estimated_words": content.get('estimated_words', len(script_text.split())),
            "tone_applied": content.get('tone_applied', tone_description),
            "tone_value": config.TONE_VALUE,
            "content_type": content.get('content_type', 'pdf_summary' if is_pdf else 'regular')
        }


class VideoProductionTool(BaseTool):
    """LangChain tool for creating videos with narration and subtitles from scripts"""
    name: str = "video_production"
    description: str = "Create video with narration and subtitles from script"

    @performance_tracker("VideoProduction")
    def _run(self, input_data: str) -> str:
        logger = logging.getLogger('VideoProductionTool')
        logger.info("Starting video production")

        try:
            data = json.loads(input_data)
            script_text = data.get("script_text", "")
            video_length = data.get("video_length", 35)

            if not script_text:
                logger.error("No script text provided")
                return json.dumps({"error": "No script text provided"})

            logger.info("Creating narration")
            narration_path = self._create_narration(script_text)

            logger.info("Selecting video template")
            template_path = self._select_template()

            logger.info("Creating video with subtitles")
            final_video = self._create_video_with_subtitles(
                template_path, script_text, narration_path, video_length
            )

            result = {
                "video_path": final_video,
                "duration": video_length,
                "has_subtitles": True,
                "narration_path": narration_path
            }

            logger.info(f"Video production completed: {final_video}")
            return json.dumps(result)

        except Exception as e:
            logger.error(f"Video production failed: {e}")
            return json.dumps({"error": f"Video production failed: {str(e)}"})

    def _create_narration(self, script_text: str) -> str:
        text = re.sub(r'[🔥😱🤯🚀💥⚡🌟✨💯🎯⏳✊🌱➡️📚#🌍🤫]', '', script_text)
        text = re.sub(r'[^\w\s.,!?-]', '', text).strip()

        if not text:
            raise Exception("No valid text for TTS after cleaning")

        os.makedirs(os.path.dirname(config.AUDIO_OUTPUT_PATH), exist_ok=True)
        voice = random.choice(["en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural"])

        async def create_audio():
            communicate = edge_tts.Communicate(text, voice, rate="+15%")
            await communicate.save(config.AUDIO_OUTPUT_PATH)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(create_audio())
        loop.close()

        if not os.path.exists(config.AUDIO_OUTPUT_PATH) or os.path.getsize(config.AUDIO_OUTPUT_PATH) <= 1000:
            raise Exception("TTS failed to generate valid audio file")

        return config.AUDIO_OUTPUT_PATH

    def _select_template(self) -> str:
        if not os.path.exists(config.VIDEO_TEMPLATES_DIR):
            raise Exception(f"Video templates directory does not exist: {config.VIDEO_TEMPLATES_DIR}")

        video_files = [f for f in os.listdir(config.VIDEO_TEMPLATES_DIR)
                       if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

        if not video_files:
            raise Exception(f"No video template files found in {config.VIDEO_TEMPLATES_DIR}")

        return os.path.join(config.VIDEO_TEMPLATES_DIR, random.choice(video_files))

    def _create_video_with_subtitles(self, video_path: str, script_text: str,
                                     narration_path: str, target_duration: int) -> str:
        os.makedirs(os.path.dirname(config.FINAL_OUTPUT_PATH), exist_ok=True)
        subtitles = self._generate_vosk_subtitles(narration_path, script_text)

        os.makedirs(os.path.dirname(config.SCRIPT_OUTPUT_PATH), exist_ok=True)
        with open(config.SCRIPT_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(subtitles)

        safe_dir = "./temp_srt"
        safe_path = "./temp_srt/subs.srt"
        os.makedirs(safe_dir, exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(subtitles)

        abs_video = os.path.abspath(video_path)
        abs_output = os.path.abspath(config.FINAL_OUTPUT_PATH)
        abs_audio = os.path.abspath(narration_path)

        cmd = [
            "ffmpeg", "-y", "-i", abs_video, "-i", abs_audio, "-vf",
            "subtitles='temp_srt/subs.srt':force_style='Fontsize=24,Bold=0,Outline=3,Shadow=2,Alignment=2,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,MarginV=80'",
            "-c:v", "libx264", "-map", "0:v", "-map", "1:a", "-preset", "fast", "-shortest", abs_output
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=180)

        try:
            os.remove(safe_path)
            os.rmdir(safe_dir)
        except:
            pass

        if result.returncode != 0 or not os.path.exists(abs_output):
            error_msg = result.stderr.decode('utf-8', errors='ignore')[
                        :200] if result.stderr else "Unknown FFmpeg error"
            raise Exception(f"FFmpeg failed to create video: {error_msg}")

        return abs_output

    def _generate_vosk_subtitles(self, narration_path: str, script_text: str) -> str:
        temp_wav = "./output/temp_vosk.wav"
        os.makedirs(os.path.dirname(temp_wav), exist_ok=True)

        result = subprocess.run([
            "ffmpeg", "-y", "-i", narration_path,
            "-ar", "16000", "-ac", "1", "-f", "wav", temp_wav
        ], capture_output=True)

        if result.returncode != 0:
            raise Exception("Failed to convert audio for Vosk processing")

        model_paths = [
            "./vosk-model-small-en-us-0.15",
            "./models/vosk-model-small-en-us-0.15",
            "./vosk-model-en-us-0.22"
        ]

        model = None
        for path in model_paths:
            if os.path.exists(path):
                model = vosk.Model(path)
                break

        if not model:
            raise Exception("No Vosk model found. Download from https://alphacephei.com/vosk/models")

        rec = vosk.KaldiRecognizer(model, 16000)
        rec.SetWords(True)
        wf = wave.open(temp_wav, 'rb')
        words_with_time = []

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if "result" in result:
                    words_with_time.extend([
                        {"word": w["word"], "start": w["start"], "end": w["end"]}
                        for w in result["result"]
                    ])

        final = json.loads(rec.FinalResult())
        if "result" in final:
            words_with_time.extend([
                {"word": w["word"], "start": w["start"], "end": w["end"]}
                for w in final["result"]
            ])

        wf.close()
        os.remove(temp_wav)

        if not words_with_time:
            raise Exception("Vosk detected no words with timestamps")

        word_chunks = self._create_vosk_chunks(words_with_time)

        srt = ""
        for i, chunk in enumerate(word_chunks, 1):
            srt += f"{i}\n{self._format_time(chunk['start'])} --> {self._format_time(chunk['end'])}\n<font color='#FFFF00'>{chunk['text']}</font>\n\n"

        return srt.strip()

    def _create_vosk_chunks(self, words_with_time: List[Dict]) -> List[Dict]:
        chunks = []
        i = 0

        while i < len(words_with_time):
            current = words_with_time[i]
            current_word = current["word"]
            current_length = len(current_word)

            if current_word.endswith(('.', '!', '?', ',', ';', ':')) or current_length > 7:
                chunks.append({"text": current_word, "start": current["start"], "end": current["end"]})
                i += 1
                continue

            next_word = words_with_time[i + 1] if i + 1 < len(words_with_time) else None
            if next_word:
                next_word_text = next_word["word"]
                if current_length <= 5 and len(next_word_text) <= 5:
                    chunks.append({
                        "text": f"{current_word} {next_word_text}",
                        "start": current["start"],
                        "end": next_word["end"]
                    })
                    i += 2
                else:
                    chunks.append({"text": current_word, "start": current["start"], "end": current["end"]})
                    i += 1
            else:
                chunks.append({"text": current_word, "start": current["start"], "end": current["end"]})
                i += 1

        return chunks

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class MusicMatchingTool(BaseTool):
    """LangChain tool for adding background music to videos"""
    name: str = "music_matching"
    description: str = "Add background music to video"

    @performance_tracker("MusicMatching")
    def _run(self, input_data: str) -> str:
        logger = logging.getLogger('MusicMatchingTool')
        logger.info("Adding background music")

        try:
            data = json.loads(input_data)
            video_path = data.get("video_path", "")

            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return json.dumps({"error": "Video file not found"})

            logger.info("Selecting music")
            music_path = self._select_music()

            logger.info(f"Adding music to video: {music_path}")
            final_video = self._add_music_to_video(video_path, music_path)

            result = {
                "video_with_music": final_video,
                "music_used": music_path,
                "original_video": video_path
            }

            logger.info(f"Music added successfully: {final_video}")
            return json.dumps(result)

        except Exception as e:
            logger.error(f"Music matching failed: {e}")
            return json.dumps({"error": f"Music matching failed: {str(e)}"})

    def _select_music(self) -> str:
        music_dir = "./music/viral"

        if not os.path.exists(music_dir):
            raise Exception(f"Music directory {music_dir} does not exist")

        music_files = [f for f in os.listdir(music_dir)
                       if f.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg'))]

        if not music_files:
            raise Exception(f"No music files found in {music_dir}")

        return os.path.join(music_dir, random.choice(music_files))

    def _add_music_to_video(self, video_path: str, music_path: str) -> str:
        """Add music to video with unique output filename"""
        # Extract base name without extension from the input video
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(os.path.dirname(video_path), f"{base_name}_with_music.mp4")

        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", music_path,
            "-filter_complex", "[1:a]volume=0.2[music];[0:a][music]amix=inputs=2:duration=shortest[out]",
            "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac",
            "-shortest", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=180)

        if result.returncode != 0 or not os.path.exists(output_path):
            error_msg = result.stderr.decode('utf-8', errors='ignore')[
                        :200] if result.stderr else "Unknown FFmpeg error"
            raise Exception(f"Failed to add music: {error_msg}")

        return output_path