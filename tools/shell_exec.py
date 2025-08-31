"""
Shell execution tools for the Gemini Coding Agent
"""

import asyncio
from pathlib import Path
from typing import Dict, Any
from .base import BaseTool


class ShellExecTool(BaseTool):
    """Tool for executing shell commands in the working directory"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
    
    @property
    def name(self) -> str:
        return "shell_exec"
    
    @property
    def description(self) -> str:
        return "Run a shell command in the agent's working directory and return stdout, stderr, and exit code."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run"
                }
            },
            "required": ["command"]
        }
    
    async def execute(self, command: str = "", **kwargs) -> Dict[str, Any]:
        """Execute a shell command in the working directory"""
        if not command.strip():
            return {"error": "Command cannot be empty"}
        
        cwd = str(self.working_directory.resolve())
        
        try:
            # Create subprocess with timeout
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for completion with 10-second timeout
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "exit_code": proc.returncode,
                    "command": command,
                    "working_directory": str(self.working_directory)
                }
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                proc.kill()
                await proc.wait()  # Wait for the process to be killed
                return {
                    "error": "Execution timed out after 10 seconds",
                    "command": command,
                    "working_directory": str(self.working_directory)
                }
                
        except FileNotFoundError as e:
            return {
                "error": f"Command not found: {command}",
                "details": str(e),
                "working_directory": str(self.working_directory)
            }
        except PermissionError as e:
            return {
                "error": f"Permission denied executing command: {command}",
                "details": str(e),
                "working_directory": str(self.working_directory)
            }
        except Exception as e:
            return {
                "error": f"Shell execution failed: {str(e)}",
                "command": command,
                "working_directory": str(self.working_directory)
            }


class ShellOperationTools:
    """Container for all shell operation tools"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
        self._tools = {
            'shell_exec': ShellExecTool(working_directory)
        }
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """Get all shell operation tools"""
        return self._tools.copy()
    
    def get_tool_names(self) -> list:
        """Get list of tool names"""
        return list(self._tools.keys())
    
    def register_all_tools(self, registry):
        """Register all shell operation tools with a registry"""
        for tool in self._tools.values():
            registry.register(tool)
