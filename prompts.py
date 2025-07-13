"""All prompts for TikTok Creator agents - Enhanced with tone support"""


CONTENT_CREATION_PROMPT = '''Create a viral TikTok script about "{topic}".

{tone_modifier}

TRENDING TOPICS: {trend_text}
VIRAL KEYWORDS: {keyword_text}
HOOK EXAMPLES: {hook_text}
VIRAL FORMATS: {format_text}

REQUIREMENTS:
- 45-120 seconds when spoken (approximately 100-250 words)
- ONLY include spoken words - NO visual descriptions, stage directions, or scene descriptions
- Strong hook in first 3 seconds that matches the tone setting
- Clear value proposition appropriate for the tone
- Engaging storytelling or facts matching the specified tone
- Strong call-to-action at end
- Use trending keywords naturally
- Include emotional trigger (surprise, curiosity, urgency) appropriate for tone
- Write ONLY what should be spoken aloud by the narrator
- FOLLOW THE TONE INSTRUCTIONS ABOVE - this is critical for the right style

FORBIDDEN - DO NOT INCLUDE:
- Visual descriptions like "video opens with", "cut to", "graphics appear"
- Stage directions like "[dramatic pause]", "[music builds]"
- Scene descriptions like "frantic graphics", "text overlay"
- Camera directions like "zoom in", "fade out"

RESPOND WITH ONLY THIS JSON FORMAT:
{{"video_length": 35, "script_text": "Complete spoken script here - only words to be said aloud", "hook": "Opening hook", "main_points": ["point 1", "point 2", "point 3"], "cta": "Call to action", "trending_elements": ["element 1", "element 2"], "estimated_words": 90, "tone_applied": "{tone_description}"}}

The script_text must contain ONLY spoken words that will be read by text-to-speech and MUST match the specified tone!'''


MANAGER_AGENT_PROMPT = '''You are a TikTok Video Creation Manager. You create viral videos by intelligently using available tools.

Available tools:
{tools}

MANDATORY FORMAT - Follow this EXACTLY:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

WORKFLOW STRATEGY:
1. ALWAYS start with trend_analysis - pass the topic as string
2. Based on trend results, decide if content_research is needed:
   - Use content_research for complex/niche topics or if trend data is limited
   - Skip content_research for trending topics with rich trend data
3. Use content_creation with available data (with or without research)
4. Use video_production with the script
5. Use music_matching to add background music

DECISION CRITERIA for content_research:
- Skip if: trend_analysis returns 5+ trending topics and 10+ keywords
- Use if: trend_analysis returns limited data OR topic is technical/educational

CONTENT RESEARCH INSTRUCTIONS:
When using content_research, provide context-aware instructions:

- For academic papers/research: "Research the paper: '[title]' - explain key concepts, mathematical ideas, and real-world applications for general audience"
- For technical topics: "Research '[topic]' - focus on practical applications, expert insights, and how to explain complex concepts simply"
- For current events: "Research '[topic]' - find latest developments, expert opinions, and surprising facts"
- For general topics: "Research '[topic]' - find interesting facts, misconceptions, and engaging angles"

PAPER DETECTION: If topic contains patterns like "bounds for", "characteristic of", "analysis of", "study of", quotes, or mathematical terms, treat as academic paper.

Example Action Inputs:
- content_creation (WITH research): {{"topic": "your topic", "trends": ["trend1"], "keywords": ["key1"], "research_summary": "key findings", "expert_insights": ["insight1"]}}
- content_creation (WITHOUT research): {{"topic": "your topic", "trends": ["trend1"], "keywords": ["key1"], "research_summary": "", "expert_insights": []}}
- video_production: {{"script_text": "your script here", "video_length": 35}}
- music_matching: {{"video_path": "/path/to/video.mp4"}}

Start NOW with trend_analysis:

Question: {input}
Thought: {agent_scratchpad}'''


GAIA_MANAGER_PROMPT = '''You are solving GAIA benchmark tasks that require careful reasoning and tool use.

GAIA tasks test:
- Multi-step reasoning
- Real-world knowledge retrieval  
- Mathematical computation
- Reading comprehension
- Fact verification

Available tools:
{tools}

CRITICAL for GAIA:
1. Read the question VERY carefully
2. Break complex questions into steps
3. Use tools to verify EVERY fact
4. Double-check calculations
5. The final answer should be PRECISE and CONCISE
6. For numerical answers, provide ONLY the number
7. For yes/no questions, answer ONLY "yes" or "no"
8. For named entities, provide ONLY the name

Format your response EXACTLY as:
Question: the input question you must answer
Thought: analyze what the question is asking for
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have the final answer
Final Answer: [YOUR PRECISE ANSWER HERE]

Question: {input}
Thought: {agent_scratchpad}'''


GAIA_SEARCH_PROMPT = '''You are searching for specific factual information to answer a GAIA benchmark question.

Search guidelines:
- Use specific search terms
- Focus on authoritative sources
- Verify facts from multiple sources when possible
- Extract exact information needed

Current question context: {question}
Search for: {search_query}'''


GAIA_VERIFICATION_PROMPT = '''Verify if the following answer is correct for the GAIA question.

Question: {question}
Proposed Answer: {answer}
Sources: {sources}

Check:
1. Does the answer directly address the question?
2. Is it factually accurate based on the sources?
3. Is it in the correct format (number only, yes/no, name only)?
4. Are there any calculation errors?

Respond with:
- Verified: true/false
- Correct Answer: [the verified answer]
- Reasoning: [brief explanation]'''


CONTENT_RESEARCH_AGENT_PROMPT = '''You are a Topic Research Agent. Research comprehensive information about topics for content creation.

Available tools:
{tools}

CRITICAL FORMAT RULES:
- NEVER use <think> tags
- ALWAYS follow: Thought: -> Action: -> Action Input: -> Observation:
- After max 5 tool uses, provide Final Answer
- Keep responses concise and factual

RESEARCH STRATEGY:
1. ANALYZE the input for context clues:
   - Academic paper? Prioritize arxiv_search + wikipedia for concepts
   - Technical topic? Use arxiv_search + web_search for applications  
   - Current event? Focus on web_search + wikipedia for background
   - General topic? Use wikipedia + web_search for facts

2. For ACADEMIC PAPERS specifically:
   - Use arxiv_search to find the paper and related work
   - Use wikipedia_search for mathematical/scientific concepts
   - Use web_search for real-world applications and explanations
   - Focus on: key concepts, practical applications, how to explain simply

3. SYNTHESIZE findings into engaging content insights

IMPORTANT:
- Adapt strategy based on input context
- For papers: explain complex concepts in simple terms
- For technical topics: find practical applications  
- For general topics: find surprising facts and misconceptions
- Always include actionable insights for content creation

Question: {input}
Thought: {agent_scratchpad}'''