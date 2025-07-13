"""Manager Agent for TikTok Creator - FIXED with complete PDF mode support"""

import json
import time
from typing import Dict, List, Any
from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from config import config
from prompts import MANAGER_AGENT_PROMPT, GAIA_MANAGER_PROMPT, PDF_MANAGER_PROMPT
from tools import (
    TrendAnalysisTool,
    ContentCreationTool,
    VideoProductionTool,
    MusicMatchingTool
)
from researchtools import ContentResearchTool, PDFExtractionTool
from logger import PerformanceLogger
import logging


class ManagerAgent:
    """Main manager agent that orchestrates all tools using LangChain"""

    def __init__(self, mode="tiktok"):
        """Initialize manager with LLM and create agent executor"""
        self.mode = mode
        self.logger = logging.getLogger('ManagerAgent')
        self.perf_logger = PerformanceLogger()

        self.llm = OllamaLLM(
            model=config.MANAGER_AGENT_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            timeout=60,
            temperature=0.3
        )
        self.tools = self._initialize_tools()
        self.agent_executor = self._create_agent_executor()

    def _initialize_tools(self) -> List:
        """Initialize all LangChain tools for the agent"""
        tools = [
            TrendAnalysisTool(),
            ContentResearchTool(),
            ContentCreationTool(),
            VideoProductionTool(),
            MusicMatchingTool()
        ]

        # PDF mode doesn't need pdf_extraction tool since we extract in manager
        # All modes use the same tools

        return tools

    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with ReAct pattern"""
        if self.mode == "gaia":
            prompt_template = GAIA_MANAGER_PROMPT
        elif self.mode == "pdf":
            prompt_template = PDF_MANAGER_PROMPT
        else:
            prompt_template = MANAGER_AGENT_PROMPT

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                "tool_names": ", ".join([tool.name for tool in self.tools])
            }
        )

        agent = create_react_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=20,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            early_stopping_method="force"
        )

    def create_viral_video(self, topic: str) -> Dict[str, Any]:
        """Create viral video using the agent workflow"""
        self.logger.info(f"Creating viral video for topic: '{topic}' in mode: {self.mode}")
        start_time = time.time()

        print(f"🎬 Manager Agent creating viral video: '{topic}' (Mode: {self.mode})")

        try:
            # FIXED: Different inputs based on mode
            if self.mode == "pdf":
                # For PDF mode, check if we have PDF content in config
                pdf_path = config.settings.get('pdf_path')
                if pdf_path:
                    # Extract PDF content first
                    pdf_tool = PDFExtractionTool()
                    pdf_content = pdf_tool._extract_pdf_local(pdf_path)

                    if pdf_content.startswith("Error"):
                        raise Exception(f"PDF extraction failed: {pdf_content}")

                    # Create direct input for PDF mode - skip the agent workflow and go straight to content creation
                    agent_input = f"""Create a viral TikTok video that summarizes the PDF document.

SKIP pdf_extraction - we already have the content.

PDF Document: {topic}
PDF Content Summary: {pdf_content[:2000]}

WORKFLOW:
1. SKIP trend_analysis (not needed for PDF summarization)
2. Use content_creation directly with the PDF content provided above
3. Use video_production with the generated script
4. Use music_matching to finalize the video

Focus on creating an engaging summary that transforms the academic/technical content into accessible TikTok format."""
                else:
                    # Fallback if no PDF path
                    agent_input = f"Create a viral TikTok video about '{topic}' focusing on document summarization."
            else:
                # Regular TikTok creation
                agent_input = f"Create a viral TikTok video about '{topic}'. Analyze trends first, then decide if content research is needed based on the results."

            # Execute agent workflow
            result = self.agent_executor.invoke({"input": agent_input})

            # Performance logging
            duration = time.time() - start_time
            self.perf_logger.log_agent_performance("ManagerAgent", duration, "success")

            if "output" in result:
                output_text = result["output"]
                self.logger.info("Video creation completed successfully")

                try:
                    start = output_text.find('{')
                    end = output_text.rfind('}') + 1
                    if start != -1 and end > start:
                        json_data = json.loads(output_text[start:end])
                        return {
                            "status": "success",
                            "topic": topic,
                            "mode": self.mode,
                            "agent_output": output_text,
                            "data": json_data,
                            "performance_metrics": self.perf_logger.get_metrics()
                        }
                except:
                    pass

                return {
                    "status": "success",
                    "topic": topic,
                    "mode": self.mode,
                    "agent_output": output_text,
                    "message": "Video creation completed - check agent output for details",
                    "performance_metrics": self.perf_logger.get_metrics()
                }
            else:
                self.logger.error("No output from agent")
                return {
                    "status": "error",
                    "topic": topic,
                    "mode": self.mode,
                    "error": "No output from agent",
                    "raw_result": result
                }

        except Exception as e:
            # Performance logging for errors
            duration = time.time() - start_time
            self.perf_logger.log_agent_performance("ManagerAgent", duration, "error", error=str(e))
            self.logger.error(f"Video creation failed: {e}")

            return {
                "status": "error",
                "topic": topic,
                "mode": self.mode,
                "error": str(e)
            }