"""
Command-line interface for the Gemini Coding Agent
"""

import os
import asyncio
from dotenv import load_dotenv

from config import CLI_WELCOME_MESSAGE, CLI_EXAMPLES
from agent import CodingAgent


async def main():
    """Main CLI interface"""
    print(CLI_WELCOME_MESSAGE)
    print("-" * 50)
    
    # Load API key
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("💡 Please create a .env file with GEMINI_API_KEY or set it as an environment variable")
        return
    
    # Initialize agent
    try:
        agent = CodingAgent(api_key)
        print(f"✅ Agent initialized successfully!")
        print(f"📁 Working directory: {agent.get_working_directory()}")
        print(f"📝 History file: {agent.history_file}")
        print(f"🧠 Model: {agent.model_name}")
        print(f"💬 Current message count: {len(agent.messages)}")
        print(f"🛠️  Available tools: {', '.join(agent.list_tool_names())}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    print("\n💡 Tip: You can ask me to create, read, modify files, or search for content!")
    for i, example in enumerate(CLI_EXAMPLES, 1):
        print(f"💡 Example {i}: '{example}'")
    print()
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == 'clear':
                agent.clear_history()
                print("🗑️ History cleared!")
                continue
            elif user_input.lower() == 'history':
                print("\n📜 Recent conversation history:")
                if not agent.messages:
                    print("  (No messages in history)")
                else:
                    for i, msg in enumerate(agent.messages[-10:], 1):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        timestamp = msg.get("timestamp")
                        
                        # Truncate long messages for display
                        if len(content) > 150:
                            content = content[:150] + "..."
                        
                        # Format role with emoji
                        role_emoji = "🧑" if role == "user" else "🤖" if role == "assistant" else "⚙️"
                        print(f"  {i:2d}. {role_emoji} [{role}] {content}")
                continue
            elif user_input.lower() in ['help', '?']:
                print("\n🆘 Available commands:")
                print("  • Type any message to chat with the agent")
                print("  • 'history' - Show recent conversation history")
                print("  • 'clear' - Clear conversation history")
                print("  • 'help' or '?' - Show this help message")
                print("  • 'exit' or 'quit' - Exit the agent")
                print("\n🛠️  The agent can help with:")
                print("  • Creating and editing files")
                print("  • Reading file contents")
                print("  • Listing directory contents")
                print("  • Searching for patterns in files")
                print("  • Writing code and scripts")
                print("  • Project analysis and organization")
                continue
            elif not user_input:
                print("💭 Please enter a message, or type 'help' for available commands.")
                continue
                
            print("\n🔄 Agent processing...")
            response = await agent.process_message(user_input)
            print(f"\n🤖 Agent: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("💡 Try again or type 'exit' to quit.")


if __name__ == "__main__":
    asyncio.run(main())
