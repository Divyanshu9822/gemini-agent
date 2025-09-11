"""
Web search tools using Brave Search API for the Gemini Coding Agent
"""

import os
import requests
from typing import Dict, Any, Optional
from .base import BaseTool


class WebSearchTool(BaseTool):
    """Tool for web searching using Brave Search API"""
    
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information using Brave Search API. Returns web search results with titles, descriptions, and URLs."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "The search query to look up on the web"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of search results to return (default: 10, max: 20)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str = "", count: int = 10, **kwargs) -> Dict[str, Any]:
        """Execute web search using Brave Search API"""
        
        if not query.strip():
            return {"error": "Search query cannot be empty"}
        
        if not self.api_key:
            return {
                "error": "Brave Search API key not found. Please set BRAVE_API_KEY environment variable."
            }
        
        # Validate count parameter
        if count < 1:
            count = 1
        elif count > 20:
            count = 20
        
        try:
            # Prepare headers
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            # Prepare parameters
            params = {
                "q": query,
                "count": count
            }
            
            # Make the API request
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            # Check if request was successful
            if response.status_code != 200:
                return {
                    "error": f"Brave Search API returned status code {response.status_code}: {response.text}"
                }
            
            # Parse JSON response
            data = response.json()
            
            # Extract search results
            results = []
            web_results = data.get("web", {}).get("results", [])
            
            for result in web_results:
                search_result = {
                    "title": result.get("title", ""),
                    "description": result.get("description", ""),
                    "url": result.get("url", ""),
                    "published": result.get("published", ""),
                    "type": result.get("type", "search_result")
                }
                results.append(search_result)
            
            # Get additional info
            query_info = data.get("query", {})
            
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "original_query": query_info.get("original", query),
                "results": results,
                "api_response_time": response.elapsed.total_seconds() if response.elapsed else None
            }
            
        except requests.exceptions.Timeout:
            return {"error": "Search request timed out after 10 seconds"}
        
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Brave Search API. Check your internet connection."}
        
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        
        except ValueError as e:
            return {"error": f"Failed to parse JSON response: {str(e)}"}
        
        except Exception as e:
            return {"error": f"Unexpected error during web search: {str(e)}"}


class WebSearchTools:
    """Container for all web search tools"""
    
    def __init__(self):
        self._tools = {
            'web_search': WebSearchTool()
        }
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """Get all web search tools"""
        return self._tools.copy()
    
    def get_tool_names(self) -> list:
        """Get list of tool names"""
        return list(self._tools.keys())
    
    def register_all_tools(self, registry):
        """Register all web search tools with a registry"""
        for tool in self._tools.values():
            registry.register(tool)
