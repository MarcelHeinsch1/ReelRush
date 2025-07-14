"""Simplified Research Tools for Content Research Agent - Fixed circular import"""

import json
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
import os
import requests
import tempfile
from typing import Dict, List, Any, Optional
from langchain_ollama import OllamaLLM
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from duckduckgo_search import DDGS
from config import config
from prompts import CONTENT_RESEARCH_AGENT_PROMPT
from logger import performance_tracker
import logging

# PDF libraries
try:
    import PyPDF2
    PDF_LIB = "PyPDF2"
except ImportError:
    try:
        import pdfplumber
        PDF_LIB = "pdfplumber"
    except ImportError:
        PDF_LIB = None


class PDFExtractionTool(BaseTool):
    """Tool for downloading and extracting text from PDF files"""
    name: str = "pdf_extraction"
    description: str = "Download and extract text from PDF files. Input: PDF URL"

    @performance_tracker("PDFExtraction")
    def _run(self, pdf_url: str) -> str:
        logger = logging.getLogger('PDFExtractionTool')
        logger.info(f"Extracting text from PDF: {pdf_url}")

        if PDF_LIB is None:
            return "Error: No PDF library available. Install PyPDF2 or pdfplumber."

        temp_pdf_path = None
        try:
            # Download PDF to temporary file
            temp_pdf_path = self._download_pdf(pdf_url)

            # Extract text
            if PDF_LIB == "PyPDF2":
                text = self._extract_with_pypdf2(temp_pdf_path)
            else:  # pdfplumber
                text = self._extract_with_pdfplumber(temp_pdf_path)

            logger.info(f"Successfully extracted {len(text)} characters from PDF")

            # Limit text length for LLM processing
            if len(text) > 15000:
                text = text[:15000] + "\n\n[Text truncated - showing first 15000 characters]"

            return text

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"Error extracting PDF: {str(e)}"

        finally:
            # Clean up temporary file
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                try:
                    os.unlink(temp_pdf_path)
                    logger.info("Temporary PDF file deleted")
                except Exception as e:
                    logger.warning(f"Could not delete temporary file: {e}")

    def _download_pdf(self, url: str) -> str:
        """Download PDF to temporary file"""
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')

        try:
            # Download PDF
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Write to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

            return temp_path

        except Exception as e:
            # Clean up on error
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except:
                pass
            raise Exception(f"Failed to download PDF: {str(e)}")

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        text = ""

        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    text += f"\n--- Page {page_num + 1} (extraction error) ---\n"

        return text.strip()

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber"""
        text = ""

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    text += f"\n--- Page {page_num + 1} (extraction error) ---\n"

        return text.strip()

    def _extract_pdf_local(self, pdf_path: str) -> str:
        """Extract text from local PDF file"""
        logger = logging.getLogger('PDFExtractionTool')
        logger.info(f"Extracting text from local PDF: {pdf_path}")

        if PDF_LIB is None:
            return "Error: No PDF library available. Install PyPDF2 or pdfplumber."

        try:
            if not os.path.exists(pdf_path):
                return f"Error: PDF file not found: {pdf_path}"

            # Extract text using available library
            if PDF_LIB == "PyPDF2":
                text = self._extract_with_pypdf2(pdf_path)
            else:  # pdfplumber
                text = self._extract_with_pdfplumber(pdf_path)

            logger.info(f"Successfully extracted {len(text)} characters from local PDF")

            # Limit text length for LLM processing
            if len(text) > 15000:
                text = text[:15000] + "\n\n[Text truncated - showing first 15000 characters]"

            return text

        except Exception as e:
            logger.error(f"Local PDF extraction failed: {e}")
            return f"Error extracting PDF: {str(e)}"

class ArxivFullTextTool(BaseTool):
    """Search ArXiv and get full text of papers by downloading PDFs"""
    name: str = "arxiv_fulltext"
    description: str = "Search ArXiv for papers and get full text content by downloading PDFs. Input: search query or ArXiv ID"

    @performance_tracker("ArxivFullText")
    def _run(self, query: str) -> str:
        logger = logging.getLogger('ArxivFullTextTool')
        logger.info(f"ArXiv full text search for: {query}")

        try:
            # Check if input is an ArXiv ID (e.g., "2301.12345" or "arxiv:2301.12345")
            arxiv_id = self._extract_arxiv_id(query)

            if arxiv_id:
                # Direct PDF download for specific ArXiv ID
                return self._get_paper_fulltext(arxiv_id)
            else:
                # Search ArXiv and get full text of best match
                return self._search_and_get_fulltext(query)

        except Exception as e:
            logger.error(f"ArXiv full text search failed: {e}")
            return json.dumps({
                "error": f"ArXiv full text search failed: {str(e)}",
                "papers": []
            })

    def _extract_arxiv_id(self, query: str) -> str:
        """Extract ArXiv ID from query if present"""
        # Remove 'arxiv:' prefix if present
        query_clean = query.lower().replace('arxiv:', '').strip()

        # Match ArXiv ID patterns (e.g., 2301.12345, 1234.5678v2)
        arxiv_pattern = r'\b\d{4}\.\d{4,5}(v\d+)?\b'
        match = re.search(arxiv_pattern, query_clean)

        return match.group(0) if match else None

    def _get_paper_fulltext(self, arxiv_id: str) -> str:
        """Get full text for specific ArXiv ID"""
        logger = logging.getLogger('ArxivFullTextTool')

        try:
            # First get metadata from ArXiv API
            metadata = self._get_paper_metadata(arxiv_id)

            # Download and extract PDF
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            logger.info(f"Downloading PDF: {pdf_url}")

            full_text = self._extract_pdf_text(pdf_url)

            if full_text.startswith("Error"):
                return json.dumps({
                    "error": full_text,
                    "arxiv_id": arxiv_id,
                    "pdf_url": pdf_url
                })

            return json.dumps({
                "arxiv_id": arxiv_id,
                "title": metadata.get("title", "Unknown"),
                "authors": metadata.get("authors", []),
                "abstract": metadata.get("abstract", ""),
                "full_text": full_text,
                "pdf_url": pdf_url,
                "word_count": len(full_text.split()),
                "source": "ArXiv Full Text"
            })

        except Exception as e:
            logger.error(f"Failed to get full text for {arxiv_id}: {e}")
            return json.dumps({
                "error": f"Failed to get full text: {str(e)}",
                "arxiv_id": arxiv_id
            })

    def _search_and_get_fulltext(self, query: str) -> str:
        """Search ArXiv and get full text of best match"""
        logger = logging.getLogger('ArxivFullTextTool')

        try:
            # Search ArXiv API
            encoded_query = urllib.parse.quote(query)
            search_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=3"

            response = requests.get(search_url, timeout=15)
            if response.status_code != 200:
                return json.dumps({"error": "ArXiv API unavailable", "papers": []})

            # Parse search results
            papers = self._parse_search_results(response.text)

            if not papers:
                return json.dumps({"error": "No papers found", "papers": []})

            # Get full text of the first (most relevant) paper
            best_paper = papers[0]
            arxiv_id = best_paper.get("arxiv_id")

            if not arxiv_id:
                return json.dumps({
                    "error": "Could not extract ArXiv ID from search results",
                    "papers": papers
                })

            logger.info(f"Getting full text for best match: {arxiv_id}")
            return self._get_paper_fulltext(arxiv_id)

        except Exception as e:
            logger.error(f"Search and full text extraction failed: {e}")
            return json.dumps({
                "error": f"Search failed: {str(e)}",
                "papers": []
            })

    def _get_paper_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        """Get paper metadata from ArXiv API"""
        try:
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return self._parse_single_paper(response.text)
            else:
                return {}

        except Exception:
            return {}

    def _parse_search_results(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse ArXiv API search results"""
        papers = []

        try:
            root = ET.fromstring(xml_content)
            namespace = ""
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'

            entries = root.findall(f"{namespace}entry")

            for entry in entries:
                paper = self._parse_paper_entry(entry, namespace)
                if paper:
                    papers.append(paper)

        except Exception as e:
            # Fallback to regex if XML parsing fails
            papers = self._parse_with_regex(xml_content)

        return papers

    def _extract_pdf_text(self, pdf_url: str) -> str:
        """Extract text from PDF URL using built-in extraction"""
        logger = logging.getLogger('ArxivFullTextTool')

        if PDF_LIB is None:
            return "Error: No PDF library available. Install PyPDF2 or pdfplumber."

        temp_pdf_path = None
        try:
            # Download PDF to temporary file
            temp_pdf_path = self._download_pdf(pdf_url)

            # Extract text
            if PDF_LIB == "PyPDF2":
                text = self._extract_with_pypdf2(temp_pdf_path)
            else:  # pdfplumber
                text = self._extract_with_pdfplumber(temp_pdf_path)

            logger.info(f"Successfully extracted {len(text)} characters from PDF")

            # Limit text length for LLM processing
            if len(text) > 15000:
                text = text[:15000] + "\n\n[Text truncated - showing first 15000 characters]"

            return text

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"Error extracting PDF: {str(e)}"

        finally:
            # Clean up temporary file
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                try:
                    os.unlink(temp_pdf_path)
                    logger.info("Temporary PDF file deleted")
                except Exception as e:
                    logger.warning(f"Could not delete temporary file: {e}")

    def _download_pdf(self, url: str) -> str:
        """Download PDF to temporary file"""
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')

        try:
            # Download PDF
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Write to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

            return temp_path

        except Exception as e:
            # Clean up on error
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except:
                pass
            raise Exception(f"Failed to download PDF: {str(e)}")

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        text = ""

        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    text += f"\n--- Page {page_num + 1} (extraction error) ---\n"

        return text.strip()

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber"""
        text = ""

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    text += f"\n--- Page {page_num + 1} (extraction error) ---\n"

        return text.strip()

    def _parse_single_paper(self, xml_content: str) -> Dict[str, Any]:
        """Parse single paper metadata"""
        try:
            root = ET.fromstring(xml_content)
            namespace = ""
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'

            entry = root.find(f"{namespace}entry")
            if entry is not None:
                return self._parse_paper_entry(entry, namespace)

        except Exception:
            pass

        return {}

    def _parse_paper_entry(self, entry, namespace: str) -> Dict[str, Any]:
        """Parse individual paper entry from XML"""
        try:
            title_elem = entry.find(f"{namespace}title")
            summary_elem = entry.find(f"{namespace}summary")
            id_elem = entry.find(f"{namespace}id")

            # Extract ArXiv ID from URL
            arxiv_id = ""
            if id_elem is not None:
                id_url = id_elem.text
                if "arxiv.org/abs/" in id_url:
                    arxiv_id = id_url.split("/abs/")[-1]

            # Extract authors
            authors = []
            for author_elem in entry.findall(f"{namespace}author"):
                name_elem = author_elem.find(f"{namespace}name")
                if name_elem is not None:
                    authors.append(name_elem.text)

            return {
                "arxiv_id": arxiv_id,
                "title": title_elem.text.strip() if title_elem is not None else "",
                "abstract": summary_elem.text.strip() if summary_elem is not None else "",
                "authors": authors
            }

        except Exception:
            return {}

    def _parse_with_regex(self, xml_content: str) -> List[Dict[str, Any]]:
        """Fallback regex parsing for ArXiv XML"""
        papers = []

        try:
            # Extract IDs (ArXiv IDs from URLs)
            id_matches = re.findall(r'arxiv\.org/abs/([^<]+)', xml_content)
            titles = re.findall(r'<title>(.*?)</title>', xml_content, re.DOTALL)
            summaries = re.findall(r'<summary>(.*?)</summary>', xml_content, re.DOTALL)

            # Skip feed title
            paper_titles = titles[1:] if len(titles) > 1 else []

            for i, (arxiv_id, title, summary) in enumerate(zip(id_matches, paper_titles, summaries)):
                if i >= 3:  # Limit results
                    break

                papers.append({
                    "arxiv_id": arxiv_id.strip(),
                    "title": title.strip(),
                    "abstract": summary.strip(),
                    "authors": []
                })

        except Exception:
            pass

        return papers


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
            ArxivFullTextTool(),  # NEW: Added full text tool
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
            max_iterations=15,  # Reduced to prevent loops
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
