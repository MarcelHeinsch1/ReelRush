"""Manager Agent for TikTok Creator"""

import json
from typing import Dict, List, Any
from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from config import config
from prompts import MANAGER_AGENT_PROMPT
from tools import (
    TrendAnalysisTool,
    ContentResearchTool,
    ContentCreationTool,
    VideoProductionTool,
    MusicMatchingTool
)


class ManagerAgent:
    """Main manager agent that orchestrates all tools using LangChain"""

    def __init__(self):
        """Initialize manager with LLM and create agent executor"""
        self.llm = OllamaLLM(
            model=config.MANAGER_AGENT_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            timeout=60,
            temperature=0.7
        )
        self.tools = self._initialize_tools()
        self.agent_executor = self._create_agent_executor()

    def _initialize_tools(self) -> List:
        """Initialize all LangChain tools for the agent"""
        return [
            TrendAnalysisTool(),
            ContentResearchTool(),
            ContentCreationTool(),
            VideoProductionTool(),
            MusicMatchingTool()
        ]

    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with ReAct pattern"""
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
        print(f"🎬 Manager Agent creating viral video: '{topic}'")

        try:
            result = self.agent_executor.invoke({
                "input": f"Create a viral TikTok video about '{topic}'. Follow the complete workflow to analyze trends, research content, create script, produce video, and add music."
            })

            if "output" in result:
                output_text = result["output"]

                try:
                    start = output_text.find('{')
                    end = output_text.rfind('}') + 1
                    if start != -1 and end > start:
                        json_data = json.loads(output_text[start:end])
                        return {
                            "status": "success",
                            "topic": topic,
                            "agent_output": output_text,
                            "data": json_data
                        }
                except:
                    pass

                return {
                    "status": "success",
                    "topic": topic,
                    "agent_output": output_text,
                    "message": "Video creation completed - check agent output for details"
                }
            else:
                return {
                    "status": "error",
                    "topic": topic,
                    "error": "No output from agent",
                    "raw_result": result
                }

        except Exception as e:
            return {
                "status": "error",
                "topic": topic,
                "error": str(e)
            }