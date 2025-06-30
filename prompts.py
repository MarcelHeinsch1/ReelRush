"""All prompts for TikTok Creator agents"""


CONTENT_CREATION_PROMPT = '''Create a viral TikTok script about "{topic}".

TRENDING TOPICS: {trend_text}
VIRAL KEYWORDS: {keyword_text}
HOOK EXAMPLES: {hook_text}
VIRAL FORMATS: {format_text}

REQUIREMENTS:
- 45-120 seconds when spoken (approximately 100-250 words)
- ONLY include spoken words - NO visual descriptions, stage directions, or scene descriptions
- Strong hook in first 3 seconds
- Clear value proposition
- Engaging storytelling or facts
- Strong call-to-action at end
- Use trending keywords naturally
- Include emotional trigger (surprise, curiosity, urgency)
- Write ONLY what should be spoken aloud by the narrator

FORBIDDEN - DO NOT INCLUDE:
- Visual descriptions like "video opens with", "cut to", "graphics appear"
- Stage directions like "[dramatic pause]", "[music builds]"
- Scene descriptions like "frantic graphics", "text overlay"
- Camera directions like "zoom in", "fade out"

RESPOND WITH ONLY THIS JSON FORMAT:
{{"video_length": 35, "script_text": "Complete spoken script here - only words to be said aloud", "hook": "Opening hook", "main_points": ["point 1", "point 2", "point 3"], "cta": "Call to action", "trending_elements": ["element 1", "element 2"], "estimated_words": 90}}

The script_text must contain ONLY spoken words that will be read by text-to-speech!'''


MANAGER_AGENT_PROMPT = '''You are a TikTok Video Creation Manager. You MUST use ALL 5 tools to create a video.

Available tools:
{tools}

MANDATORY FORMAT - Follow this EXACTLY:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation for EACH tool)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

YOU MUST USE ALL 5 TOOLS IN THIS EXACT ORDER:
1. trend_analysis - pass the topic as string
2. content_research - pass the topic as string  
3. content_creation - pass JSON with ALL data from steps 1&2
4. video_production - pass JSON with script data from step 3
5. music_matching - pass JSON with video path from step 4

CRITICAL: You CANNOT skip tools or just describe what you would do. You MUST actually execute each tool.

Example for content_creation Action Input:
{{"topic": "your topic", "trends": ["trend1", "trend2"], "keywords": ["key1", "key2"], "hooks": ["hook1"], "formats": ["format1"]}}

Example for video_production Action Input:
{{"script_text": "your script here", "video_length": 35}}

Example for music_matching Action Input:
{{"video_path": "/path/to/video.mp4"}}

Start NOW - use trend_analysis first:

Question: {input}
Thought: {agent_scratchpad}'''