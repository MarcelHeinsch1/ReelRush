"""Simplified Research Tools for Content Research Agent"""

import json
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from duckduckgo_search import DDGS
from config import config
from prompts import CONTENT_RESEARCH_AGENT_PROMPT
from logger import performance_tracker
import logging
import requests


class WebSearchTool(BaseTool):
    """Simple web search - agent decides the search query"""
    name: str = "web_search"
    description: str = "Search the web for any information. You control the search query."

    @performance_tracker("WebSearch")
    def _run(self, query: str) -> str:
        try:
            time.sleep(1)
            ddgs = DDGS(timeout=15)
            results = list(ddgs.text(query, max_results=8))

            if not results:
                return json.dumps({"error": "No results found", "results": []})

            cleaned_results = []
            for result in results:
                cleaned_results.append({
                    "title": result.get("title", "")[:150],
                    "content": result.get("body", "")[:400],
                    "url": result.get("href", "")
                })

            return json.dumps({"results": cleaned_results, "total": len(cleaned_results)})

        except Exception as e:
            return json.dumps({"error": f"Search failed: {str(e)}", "results": []})


class ArxivSearchTool(BaseTool):
    """Search ArXiv for academic papers and research"""
    name: str = "arxiv_search"
    description: str = "Search ArXiv for academic papers, research studies, and scientific information"

    @performance_tracker("ArxivSearch")
    def _run(self, query: str) -> str:
        logger = logging.getLogger('ArxivSearchTool')
        logger.info(f"ArXiv searching for: {query}")

        try:
            # ArXiv API search with URL encoding
            encoded_query = urllib.parse.quote(query)
            url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=5"

            logger.info(f"ArXiv URL: {url}")

            response = requests.get(url, timeout=15)
            logger.info(f"ArXiv response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"ArXiv API returned status {response.status_code}")
                return json.dumps({"error": "ArXiv API unavailable", "papers": []})

            content = response.text
            logger.info(f"ArXiv content length: {len(content)}")
            papers = []

            # Use proper XML parsing instead of regex
            try:
                root = ET.fromstring(content)

                # Handle namespace
                namespace = ""
                if root.tag.startswith('{'):
                    namespace = root.tag.split('}')[0] + '}'

                logger.info(f"ArXiv XML namespace: {namespace}")

                # Find all entry elements
                entries = root.findall(f"{namespace}entry")
                logger.info(f"ArXiv found {len(entries)} entries")

                for i, entry in enumerate(entries):
                    title_elem = entry.find(f"{namespace}title")
                    summary_elem = entry.find(f"{namespace}summary")

                    if title_elem is not None and summary_elem is not None:
                        title = title_elem.text.strip() if title_elem.text else ""
                        summary = summary_elem.text.strip() if summary_elem.text else ""

                        logger.info(f"ArXiv paper {i+1}: {title[:50]}...")

                        papers.append({
                            "title": title[:200],
                            "summary": summary[:400],
                            "source": "ArXiv"
                        })

                        if len(papers) >= 5:  # Limit results
                            break

                logger.info(f"ArXiv XML parsing successful: {len(papers)} papers")

            except Exception as xml_error:
                logger.error(f"ArXiv XML parsing failed: {xml_error}")
                # Fallback to regex if XML parsing fails
                titles = re.findall(r'<title>(.*?)</title>', content, re.DOTALL)
                summaries = re.findall(r'<summary>(.*?)</summary>', content, re.DOTALL)

                logger.info(f"ArXiv regex fallback: {len(titles)} titles, {len(summaries)} summaries")

                # Skip feed title (first title) and properly pair with summaries
                paper_titles = titles[1:] if len(titles) > 1 else []

                for i, (title, summary) in enumerate(zip(paper_titles, summaries)):
                    if i >= 5:  # Limit results
                        break
                    papers.append({
                        "title": title.strip()[:200],
                        "summary": summary.strip()[:400],
                        "source": "ArXiv"
                    })

                logger.info(f"ArXiv regex parsing result: {len(papers)} papers")

            result = {"papers": papers, "total": len(papers)}
            logger.info(f"ArXiv final result: {len(papers)} papers")
            return json.dumps(result)

        except Exception as e:
            logger.error(f"ArXiv search failed completely: {e}")
            return json.dumps({"error": f"ArXiv search failed: {str(e)}", "papers": []})


class YouTubeTranscriptTool(BaseTool):
    """Get transcripts/subtitles from YouTube videos"""
    name: str = "youtube_transcript"
    description: str = "Get transcript/subtitles from YouTube videos by searching for videos first"

    @performance_tracker("YouTubeTranscript")
    def _run(self, query: str) -> str:
        try:
            # Search for YouTube videos first
            ddgs = DDGS(timeout=10)
            search_query = f"site:youtube.com {query}"
            results = list(ddgs.text(search_query, max_results=3))

            transcripts = []
            for result in results:
                if "youtube.com/watch" in result.get("href", ""):
                    # Extract video ID
                    url = result.get("href", "")
                    video_id_match = re.search(r'v=([^&]+)', url)

                    if video_id_match:
                        video_id = video_id_match.group(1)

                        # Try to get transcript via YouTube's API or description
                        transcript_text = self._get_video_info(video_id, result)

                        transcripts.append({
                            "title": result.get("title", "")[:150],
                            "video_id": video_id,
                            "content": transcript_text[:500],
                            "url": url
                        })

            return json.dumps({"transcripts": transcripts, "total": len(transcripts)})

        except Exception as e:
            return json.dumps({"error": f"YouTube transcript failed: {str(e)}", "transcripts": []})

    def _get_video_info(self, video_id: str, result: dict) -> str:
        """Get available video information (description, etc.)"""
        try:
            # Use video description from search results as proxy for content
            description = result.get("body", "")
            return description[:500] if description else "No transcript available"
        except:
            return "No transcript available"


class WikipediaSearchTool(BaseTool):
    """Search Wikipedia for comprehensive topic information"""
    name: str = "wikipedia_search"
    description: str = "Search Wikipedia for comprehensive, factual information about topics"

    @performance_tracker("WikipediaSearch")
    def _run(self, query: str) -> str:
        try:
            # Wikipedia API search
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
            response = requests.get(search_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return json.dumps({
                    "title": data.get("title", ""),
                    "summary": data.get("extract", "")[:800],
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "source": "Wikipedia"
                })
            else:
                # Fallback to search
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=3"
                response = requests.get(search_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("query", {}).get("search", [])

                    if results:
                        first_result = results[0]
                        return json.dumps({
                            "title": first_result.get("title", ""),
                            "summary": first_result.get("snippet", "")[:400],
                            "source": "Wikipedia"
                        })

            return json.dumps({"error": "No Wikipedia results found"})

        except Exception as e:
            return json.dumps({"error": f"Wikipedia search failed: {str(e)}"})


class ContentResearchAgent:
    """Simplified autonomous research agent"""

    def __init__(self):
        self.llm = OllamaLLM(
            model=config.CONTENT_RESEARCH_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            timeout=60,
            temperature=0.3
        )
        self.tools = [
            WebSearchTool(),
            ArxivSearchTool(),
            YouTubeTranscriptTool(),
            WikipediaSearchTool()
        ]
        self.agent_executor = self._create_agent_executor()

    def _create_agent_executor(self) -> AgentExecutor:
        prompt = PromptTemplate(
            template=CONTENT_RESEARCH_AGENT_PROMPT,
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
            max_iterations=5,  # Reduced to prevent loops
            handle_parsing_errors=True,
            early_stopping_method="force"
        )

    @performance_tracker("ContentResearchAgent")
    def research_content(self, topic: str) -> Dict[str, Any]:
        try:
            result = self.agent_executor.invoke({
                "input": f"Research comprehensive information about '{topic}' for content creation. Use multiple sources including academic papers, videos, and encyclopedic information."
            })

            output_text = result.get("output", "")

            # Extract JSON if present
            try:
                start = output_text.find('{')
                end = output_text.rfind('}') + 1
                if start != -1 and end > start:
                    structured_data = json.loads(output_text[start:end])
                    return {
                        "status": "success",
                        "topic": topic,
                        "structured_data": structured_data,
                        "research_output": output_text
                    }
            except:
                pass

            return {
                "status": "success",
                "topic": topic,
                "research_output": output_text
            }

        except Exception as e:
            return {
                "status": "error",
                "topic": topic,
                "error": str(e)
            }


class ContentResearchTool(BaseTool):
    """Main research tool for integration"""
    name: str = "content_research"
    description: str = "Research comprehensive information about topics using multiple specialized sources"

    @performance_tracker("ContentResearch")
    def _run(self, query: str) -> str:
        try:
            # Create agent instance locally to avoid Pydantic issues
            research_agent = ContentResearchAgent()
            result = research_agent.research_content(query)

            if result["status"] == "success":
                if "structured_data" in result:
                    return json.dumps(result["structured_data"])
                else:
                    # Extract key information from output
                    output = result.get("research_output", "")
                    return json.dumps({
                        "research_summary": output[:800],
                        "key_findings": self._extract_findings(output),
                        "sources_used": ["web", "academic", "video", "encyclopedia"],
                        "agent_research": True
                    })
            else:
                return json.dumps({
                    "error": result.get("error", "Research failed"),
                    "research_summary": "",
                    "key_findings": []
                })

        except Exception as e:
            return json.dumps({
                "error": f"Research failed: {str(e)}",
                "research_summary": "",
                "key_findings": []
            })

    def _extract_findings(self, text: str) -> List[str]:
        """Extract key findings from research output"""
        findings = []

        # Look for facts, insights, and key points
        patterns = [
            r'["\']([^"\']*(?:fact|research|study|shows|indicates)[^"\']*)["\']',
            r'["\']([^"\']*\d+%[^"\']*)["\']',
            r'["\']([^"\']*(?:expert|professor|scientist)[^"\']*)["\']'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            findings.extend(matches[:3])

        return list(set(findings))[:8]