"""
Main CodingAgent class for the Gemini Coding Agent
Simplified and refactored for modularity
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from google import genai
from google.genai import types
from dotenv import load_dotenv

from config import (
    SYSTEM_PROMPT, 
    MODEL_NAME, 
    MODEL_TEMPERATURE, 
    REACT_SAFETY_LIMIT, 
    RECENT_MESSAGES_LIMIT,
    DEFAULT_HISTORY_FILE
)
from tools.base import ToolRegistry
from tools.file_ops import FileOperationTools
from tools.shell_exec import ShellOperationTools
from tools.web_search import WebSearchTools


class CodingAgent:
    """Main coding agent with modular tool system"""
    
    def __init__(self, api_key: str, working_directory: str = ".", history_file: str = DEFAULT_HISTORY_FILE):
        """
        Initialize the CodingAgent with Gemini client and configuration.
        
        Args:
            api_key: Google Gemini API key
            working_directory: Directory where the agent operates
            history_file: File to store conversation history
        """
        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)
        
        # Set up working directory
        self.working_directory = Path(working_directory).resolve()
        self.working_directory.mkdir(parents=True, exist_ok=True)
        
        # History management
        self.history_file = self.working_directory / history_file
        self.messages: List[Dict] = []
        
        # Configuration
        self.model_name = MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT
        
        # Initialize tool registry and register tools
        self.tool_registry = ToolRegistry()
        self._setup_tools()
        
        # Load existing conversation history
        self.load_history()
    
    def _setup_tools(self):
        """Set up and register all available tools"""
        # Register file operation tools
        file_tools = FileOperationTools(self.working_directory)
        file_tools.register_all_tools(self.tool_registry)
        
        # Register shell operation tools
        shell_tools = ShellOperationTools(self.working_directory)
        shell_tools.register_all_tools(self.tool_registry)
        
        # Register web search tools
        web_tools = WebSearchTools()
        web_tools.register_all_tools(self.tool_registry)
    
    def load_history(self):
        """Load conversation history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = data.get('messages', [])
                    print(f"Loaded {len(self.messages)} messages from history")
            else:
                print("No existing history file found, starting fresh")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading history: {e}")
            self.messages = []
    
    def save_history(self):
        """Save conversation history to file"""
        try:
            history_data = {
                'messages': self.messages,
                'working_directory': str(self.working_directory),
                'model_name': self.model_name
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.messages)} messages to history")
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history"""
        message = {
            'role': role,
            'content': content,
            'timestamp': asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else None
        }
        self.messages.append(message)
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the current conversation history"""
        return self.messages.copy()
    
    def clear_history(self):
        """Clear the conversation history"""
        self.messages = []
        if self.history_file.exists():
            self.history_file.unlink()
        print("Conversation history cleared")
    
    def get_working_directory(self) -> Path:
        """Get the current working directory"""
        return self.working_directory
    
    def change_working_directory(self, new_directory: str):
        """Change the working directory"""
        new_path = Path(new_directory).resolve()
        new_path.mkdir(parents=True, exist_ok=True)
        self.working_directory = new_path
        
        # Update history file location
        self.history_file = self.working_directory / self.history_file.name
        
        # Recreate tools with new working directory
        self.tool_registry = ToolRegistry()
        self._setup_tools()
        
        print(f"Changed working directory to: {self.working_directory}")
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return self.system_prompt
    
    def get_available_tools(self) -> List[types.FunctionDeclaration]:
        """Get the list of available tools/functions"""
        return self.tool_registry.get_function_declarations()
    
    def get_tool_by_name(self, tool_name: str):
        """Get a specific tool by name"""
        return self.tool_registry.get_tool(tool_name)
    
    def list_tool_names(self) -> List[str]:
        """List all available tool names"""
        return self.tool_registry.get_tool_names()
    
    def build_messages_list(self, user_input: str) -> List[types.Content]:
        """Build messages list for Gemini API call"""
        messages = []
        
        # Add system prompt
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=self.system_prompt)]
        ))
        messages.append(types.Content(
            role="model",
            parts=[types.Part(text="I understand. I'm a coding agent ready to help with programming tasks and file operations.")]
        ))
        
        # Add conversation history (recent messages only)
        recent_messages = self.messages[-RECENT_MESSAGES_LIMIT:] if len(self.messages) > RECENT_MESSAGES_LIMIT else self.messages
        
        for message in recent_messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Convert role to Gemini format
            if role == "assistant":
                role = "model"
            elif role == "system":
                continue
            
            messages.append(types.Content(
                role=role,
                parts=[types.Part(text=content)]
            ))
        
        # Add current user input if not already in history
        if not recent_messages or recent_messages[-1].get("content") != user_input:
            messages.append(types.Content(
                role="user", 
                parts=[types.Part(text=user_input)]
            ))
        
        return messages
    
    def _parse_gemini_response(self, response) -> Tuple[List[str], List[Any]]:
        """Parse Gemini response to extract text and function calls"""
        text_responses = []
        function_calls = []
        
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                if hasattr(candidate, 'content') and candidate.content:
                    content = candidate.content
                    
                    if hasattr(content, 'parts'):
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_responses.append(part.text)
                            
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls.append(part.function_call)
        except Exception as e:
            print(f"Warning: Error parsing Gemini response: {e}")
            response_str = str(response)
            if response_str and response_str != str(response.__class__):
                text_responses.append(f"Response parsing error, raw response: {response_str}")
        
        return text_responses, function_calls
    
    async def _call_gemini(self, messages: List[types.Content]) -> Tuple[Any, Optional[str]]:
        """Call Gemini API with messages"""
        try:
            tools = [
                types.Tool(function_declarations=self.tool_registry.get_function_declarations())
            ]
            
            config = types.GenerateContentConfig(
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=MODEL_TEMPERATURE
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=messages,
                config=config
            )
            
            return response, None
        except Exception as e:
            return None, f"Gemini API Error: {str(e)}"
    
    async def _execute_tool_calls(self, function_calls: List[Any]) -> List[Dict]:
        """Execute tool calls using the tool registry"""
        tool_results = []
        
        for func_call in function_calls:
            print(f"🔧 Executing: {func_call.name}")
            
            # Get function arguments
            args = func_call.args if hasattr(func_call, 'args') else {}
            
            # Execute tool through registry
            result = await self.tool_registry.execute_tool(func_call.name, **args)
            
            if "error" not in result:
                print(f"✓ Tool {func_call.name} completed")
            else:
                print(f"✗ Tool {func_call.name} failed: {result['error']}")
            
            tool_results.append({
                "name": func_call.name,
                "response": result
            })
        
        return tool_results
    
    def _format_tool_result_for_gemini(self, tool_name: str, result: Dict) -> types.Content:
        """Format tool execution result for Gemini response"""
        if "error" in result:
            result_text = f"Tool {tool_name} failed: {result['error']}"
        elif "success" in result and result["success"]:
            if tool_name == "read_file":
                result_text = f"File content from {result.get('path', 'unknown')}:\n\n{result.get('content', '')}"
            elif tool_name == "write_file":
                result_text = f"Successfully wrote to {result.get('path', 'unknown')} ({result.get('size', 0)} bytes)"
            elif tool_name == "list_files":
                files = result.get('files', [])
                dirs = result.get('directories', [])
                result_text = f"Directory listing for {result.get('path', 'unknown')}:\n"
                if dirs:
                    result_text += "Directories:\n" + "\n".join([f"  📁 {d['name']}" for d in dirs]) + "\n"
                if files:
                    result_text += "Files:\n" + "\n".join([f"  📄 {f['name']} ({f['size']} bytes)" for f in files])
                result_text += f"\nTotal items: {result.get('total_items', 0)}"
            elif tool_name == "search_files":
                matches = result.get('matches', [])
                result_text = f"Search results for '{result.get('pattern', '')}' in {result.get('search_path', 'unknown')}:\n"
                if matches:
                    for match in matches:
                        result_text += f"  📄 {match['file']}: {match['matches']} matches\n"
                        if match.get('sample_matches'):
                            result_text += f"    Examples: {', '.join(match['sample_matches'][:3])}\n"
                else:
                    result_text += "No matches found."
                result_text += f"\nTotal files with matches: {result.get('total_files_with_matches', 0)}"
            elif tool_name == "shell_exec":
                command = result.get('command', 'unknown')
                exit_code = result.get('exit_code', 0)
                stdout = result.get('stdout', '').strip()
                stderr = result.get('stderr', '').strip()
                result_text = f"Shell command executed: {command}\n"
                result_text += f"Exit code: {exit_code}\n"
                if stdout:
                    result_text += f"Output:\n{stdout}\n"
                if stderr:
                    result_text += f"Error output:\n{stderr}\n"
                result_text += f"Working directory: {result.get('working_directory', 'unknown')}"
            elif tool_name == "web_search":
                query = result.get('query', 'unknown')
                results = result.get('results', [])
                result_text = f"Web search results for '{query}':\n"
                if results:
                    for i, search_result in enumerate(results[:5], 1):  # Show top 5 results
                        title = search_result.get('title', 'No title')
                        description = search_result.get('description', 'No description')
                        url = search_result.get('url', 'No URL')
                        result_text += f"{i}. {title}\n"
                        result_text += f"   {description}\n"
                        result_text += f"   🔗 {url}\n\n"
                else:
                    result_text += "No search results found.\n"
                result_text += f"Total results: {result.get('results_count', 0)}"
            else:
                result_text = f"Tool {tool_name} completed: {result}"
        else:
            result_text = f"Tool {tool_name} result: {result}"
        
        return types.Content(
            role="user",
            parts=[types.Part(text=f"[Tool Result]\n{result_text}")]
        )
    
    def _format_tool_results_for_gemini(self, tool_results: List[Dict]) -> List[types.Content]:
        """Format tool execution results for adding to conversation"""
        formatted_results = []
        
        for tool_result in tool_results:
            tool_name = tool_result.get("name", "unknown")
            result = tool_result.get("response", {})
            
            formatted_content = self._format_tool_result_for_gemini(tool_name, result)
            formatted_results.append(formatted_content)
        
        return formatted_results
    
    async def react_loop(self, user_input: str) -> str:
        """Main ReAct loop for processing user input"""
        self.add_message("user", user_input)
        
        messages = self.build_messages_list(user_input=user_input)
        
        last_complete_response = None
        iterations = 0
        
        print(f"🤖 Starting ReAct loop for: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
        
        while iterations < REACT_SAFETY_LIMIT:
            iterations += 1
            print(f"🔄 ReAct iteration {iterations}")
            
            response, error = await self._call_gemini(messages)
            if error:
                error_msg = f"Error: {error}"
                self.add_message("assistant", error_msg)
                return error_msg
            
            text_responses, function_calls = self._parse_gemini_response(response)
            
            if text_responses:
                last_complete_response = "\n".join(text_responses)
                print(f"💬 Model response: {last_complete_response[:100]}{'...' if len(last_complete_response) > 100 else ''}")
            
            if not function_calls:
                print("✅ No more tool calls needed, finishing ReAct loop")
                break
                
            print(f"🔧 Found {len(function_calls)} tool call(s) to execute")
            
            tool_results = await self._execute_tool_calls(function_calls)
            tool_result_contents = self._format_tool_results_for_gemini(tool_results)
            messages.extend(tool_result_contents)
        
        final_response = last_complete_response or "I couldn't generate a response."
        
        if iterations >= REACT_SAFETY_LIMIT:
            final_response += f"\n\n(Note: I reached my processing limit of {REACT_SAFETY_LIMIT} iterations. You may want to break this down into smaller steps.)"
            print(f"⚠️  Hit safety limit of {REACT_SAFETY_LIMIT} iterations")
        
        self.add_message("assistant", final_response)
        print(f"🎯 ReAct loop completed in {iterations} iteration(s)")
        return final_response
    
    async def process_message(self, user_input: str) -> str:
        """Main entry point for processing user messages"""
        try:
            print(f"📝 Processing message: {user_input}")
            result = await self.react_loop(user_input)
            
            self.save_history()
            
            return result
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"❌ Error processing message: {error_msg}")
            self.add_message("assistant", error_msg)
            
            try:
                self.save_history()
            except:
                pass
                
            return error_msg
