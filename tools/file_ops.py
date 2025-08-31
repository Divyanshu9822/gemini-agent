"""
File operation tools for the Gemini Coding Agent
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .base import BaseTool


class ReadFileTool(BaseTool):
    """Tool for reading file contents"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read the contents of a file"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to read"}
            },
            "required": ["path"]
        }
    
    def _validate_path_security(self, path: str) -> Tuple[bool, Optional[Path]]:
        """Validate that a path is within the working directory for security"""
        try:
            if os.path.isabs(path):
                return False, None
            
            file_path = (self.working_directory / path).resolve()
            
            if not str(file_path).startswith(str(self.working_directory)):
                return False, None
                
            return True, file_path
        except Exception:
            return False, None
    
    async def execute(self, path: str = "", **kwargs) -> Dict[str, Any]:
        """Read a file and return its contents"""
        try:
            is_valid, file_path = self._validate_path_security(path)
            if not is_valid:
                return {"error": "Access denied: path outside working directory or invalid path"}
            
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            if not file_path.is_file():
                return {"error": f"Path is not a file: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True, 
                "content": content, 
                "path": str(file_path.relative_to(self.working_directory)),
                "size": file_path.stat().st_size
            }
        except UnicodeDecodeError:
            return {"error": f"File is not readable as UTF-8 text: {path}"}
        except PermissionError:
            return {"error": f"Permission denied reading file: {path}"}
        except Exception as e:
            return {"error": f"Could not read file: {str(e)}"}


class WriteFileTool(BaseTool):
    """Tool for writing content to files"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Write content to a file"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to write"},
                "content": {"type": "string", "description": "The content to write to the file"}
            },
            "required": ["path", "content"]
        }
    
    def _validate_path_security(self, path: str) -> Tuple[bool, Optional[Path]]:
        """Validate that a path is within the working directory for security"""
        try:
            if os.path.isabs(path):
                return False, None
            
            file_path = (self.working_directory / path).resolve()
            
            if not str(file_path).startswith(str(self.working_directory)):
                return False, None
                
            return True, file_path
        except Exception:
            return False, None
    
    async def execute(self, path: str = "", content: str = "", **kwargs) -> Dict[str, Any]:
        """Write content to a file"""
        try:
            is_valid, file_path = self._validate_path_security(path)
            if not is_valid:
                return {"error": "Access denied: path outside working directory or invalid path"}
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path.relative_to(self.working_directory)),
                "size": len(content.encode('utf-8')),
                "message": f"File written successfully: {path}"
            }
        except PermissionError:
            return {"error": f"Permission denied writing to file: {path}"}
        except OSError as e:
            return {"error": f"OS error writing file: {str(e)}"}
        except Exception as e:
            return {"error": f"Could not write file: {str(e)}"}


class ListFilesTool(BaseTool):
    """Tool for listing files and directories"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
    
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return "List files and directories in a given path"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory path to list files from"}
            },
            "required": ["path"]
        }
    
    def _validate_path_security(self, path: str) -> Tuple[bool, Optional[Path]]:
        """Validate that a path is within the working directory for security"""
        try:
            if os.path.isabs(path):
                return False, None
            
            file_path = (self.working_directory / path).resolve()
            
            if not str(file_path).startswith(str(self.working_directory)):
                return False, None
                
            return True, file_path
        except Exception:
            return False, None
    
    async def execute(self, path: str = ".", **kwargs) -> Dict[str, Any]:
        """List files and directories in a given path"""
        try:
            is_valid, dir_path = self._validate_path_security(path)
            if not is_valid:
                return {"error": "Access denied: path outside working directory or invalid path"}
            
            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}
            
            if not dir_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}
            
            files = []
            directories = []
            
            for item in dir_path.iterdir():
                relative_path = str(item.relative_to(self.working_directory))
                item_info = {
                    "name": item.name,
                    "path": relative_path,
                    "size": item.stat().st_size if item.is_file() else None
                }
                
                if item.is_file():
                    files.append(item_info)
                elif item.is_dir():
                    directories.append(item_info)
            
            # Sort for consistent output
            files.sort(key=lambda x: x["name"])
            directories.sort(key=lambda x: x["name"])
            
            return {
                "success": True,
                "path": str(dir_path.relative_to(self.working_directory)),
                "directories": directories,
                "files": files,
                "total_items": len(files) + len(directories)
            }
        except PermissionError:
            return {"error": f"Permission denied accessing directory: {path}"}
        except Exception as e:
            return {"error": f"Could not list directory: {str(e)}"}


class SearchFilesTool(BaseTool):
    """Tool for searching text patterns in files"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
    
    @property
    def name(self) -> str:
        return "search_files"
    
    @property
    def description(self) -> str:
        return "Search for text patterns in files within a directory"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory path to search in"},
                "pattern": {"type": "string", "description": "The text pattern to search for"},
                "file_extension": {"type": "string", "description": "Optional file extension filter (e.g., '.py', '.js')"}
            },
            "required": ["path", "pattern"]
        }
    
    def _validate_path_security(self, path: str) -> Tuple[bool, Optional[Path]]:
        """Validate that a path is within the working directory for security"""
        try:
            if os.path.isabs(path):
                return False, None
            
            file_path = (self.working_directory / path).resolve()
            
            if not str(file_path).startswith(str(self.working_directory)):
                return False, None
                
            return True, file_path
        except Exception:
            return False, None
    
    async def execute(self, pattern: str = "", path: str = ".", file_extension: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Search for text patterns in files within a directory"""
        try:
            is_valid, search_path = self._validate_path_security(path)
            if not is_valid:
                return {"error": "Access denied: path outside working directory or invalid path"}
            
            if not search_path.exists():
                return {"error": f"Directory not found: {path}"}
            
            if not search_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}
            
            matches = []
            pattern_regex = re.compile(pattern, re.IGNORECASE)
            
            # Walk through directory recursively
            for file_path in search_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Filter by file extension if specified
                if file_extension and not file_path.name.lower().endswith(file_extension.lower()):
                    continue
                
                try:
                    # Only search text files
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Search for pattern in content
                    pattern_matches = pattern_regex.findall(content)
                    if pattern_matches:
                        relative_path = str(file_path.relative_to(self.working_directory))
                        matches.append({
                            "file": relative_path,
                            "matches": len(pattern_matches),
                            "sample_matches": pattern_matches[:5]  # First 5 matches
                        })
                        
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary files or files we can't read
                    continue
            
            return {
                "success": True,
                "pattern": pattern,
                "search_path": str(search_path.relative_to(self.working_directory)),
                "file_extension": file_extension,
                "matches": matches,
                "total_files_with_matches": len(matches)
            }
        except Exception as e:
            return {"error": f"Could not search files: {str(e)}"}


class FileOperationTools:
    """Container for all file operation tools"""
    
    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
        self._tools = {
            'read_file': ReadFileTool(working_directory),
            'write_file': WriteFileTool(working_directory),
            'list_files': ListFilesTool(working_directory),
            'search_files': SearchFilesTool(working_directory)
        }
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """Get all file operation tools"""
        return self._tools.copy()
    
    def get_tool_names(self) -> list:
        """Get list of tool names"""
        return list(self._tools.keys())
    
    def register_all_tools(self, registry):
        """Register all file operation tools with a registry"""
        for tool in self._tools.values():
            registry.register(tool)
