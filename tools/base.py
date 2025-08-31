"""
Base tool interface and registry for the Gemini Coding Agent
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from google.genai import types
import asyncio
import os
from pathlib import Path


class BaseTool(ABC):
    """Abstract base class for all agent tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the AI model"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    def get_function_declaration(self) -> types.FunctionDeclaration:
        """Convert tool to Gemini FunctionDeclaration"""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a new tool"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools"""
        return self._tools.copy()
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self._tools.keys())
    
    def get_function_declarations(self) -> List[types.FunctionDeclaration]:
        """Get Gemini function declarations for all tools"""
        return [tool.get_function_declaration() for tool in self._tools.values()]
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}


# Global tool registry instance
tool_registry = ToolRegistry()
