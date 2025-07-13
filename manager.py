"""Manager Agent for TikTok Creator - Corrected imports"""

import json
import time
from typing import Dict, List, Any
from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from config import config
from prompts import MANAGER_AGENT_PROMPT, GAIA_MANAGER_PROMPT
from tools import (
    TrendAnalysisTool,
    ContentCreationTool,
    VideoProductionTool,
    MusicMatchingTool
)
# Import ContentResearchTool from researchtools.py
from researchtools import ContentResearchTool
from logger import PerformanceLogger
import logging


class ManagerAgent:
    """Main manager agent that orchestrates all tools using LangChain"""

    def __init__(self, mode="tiktok"):
        """Initialize manager with LLM and create agent executor"""
        # Neue Logging-Zeilen
        self.mode = mode
        self.logger = logging.getLogger('ManagerAgent')
        self.perf_logger = PerformanceLogger()

        # Bestehende Initialisierung
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
        return [
            TrendAnalysisTool(),
            ContentResearchTool(),  # Now imported from researchtools.py
            ContentCreationTool(),
            VideoProductionTool(),
            MusicMatchingTool()
        ]

    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with ReAct pattern"""
        if self.mode == "gaia":
            print("hallo")
            prompt = PromptTemplate(
                template=GAIA_MANAGER_PROMPT,
                input_variables=["input", "agent_scratchpad"],
                partial_variables={
                    "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                    "tool_names": ", ".join([tool.name for tool in self.tools])
                }
            )
        else:
            prompt = PromptTemplate(
                template=MANAGER_AGENT_PROMPT,
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
        # Neue Logging-Zeilen
        self.logger.info(f"Creating viral video for topic: '{topic}'")
        start_time = time.time()

        print(f"🎬 Manager Agent creating viral video: '{topic}'")

        try:
            # Angepasster Input für flexibleren Workflow
            result = self.agent_executor.invoke({
                "input": f"Create a viral TikTok video about '{topic}'. Analyze trends first, then decide if content research is needed based on the results."
            })

            # Performance-Logging
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
                            "agent_output": output_text,
                            "data": json_data,
                            "performance_metrics": self.perf_logger.get_metrics()
                        }
                except:
                    pass

                return {
                    "status": "success",
                    "topic": topic,
                    "agent_output": output_text,
                    "message": "Video creation completed - check agent output for details",
                    "performance_metrics": self.perf_logger.get_metrics()
                }
            else:
                self.logger.error("No output from agent")
                return {
                    "status": "error",
                    "topic": topic,
                    "error": "No output from agent",
                    "raw_result": result
                }

        except Exception as e:
            # Performance-Logging für Fehler
            duration = time.time() - start_time
            self.perf_logger.log_agent_performance("ManagerAgent", duration, "error", error=str(e))
            self.logger.error(f"Video creation failed: {e}")

            return {
                "status": "error",
                "topic": topic,
                "error": str(e)
            }