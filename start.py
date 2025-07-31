import os
import sys
import subprocess
import time
import threading
from pathlib import Path
from config import config

def print_banner():
    """Print the startup banner"""
    print("\n" + "="*80)
    print("🎭 Playwright Automation with MCP & OpenAI - Quick Start")
    print("This script will help you set up and run the automation system.\n")

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. You have:", sys.version)
        return False
    else:
        print("✅ Python version:", sys.version.split()[0])
    
    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Node.js version:", result.stdout.strip())
        else:
            print("❌ Node.js not found. Please install Node.js 16+")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js 16+")
        return False
    
    # Check OpenAI API key
    api_key = config.get_openrouter_api_key()
    if not api_key or api_key == "":
        print("⚠️  OpenAI API key not found in configuration")
        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ OpenAI API key is required")
            return False
        print("💡 Please update your config.py file with your API key")
    print("✅ OpenAI API key is configured")
    
    return True

def install_dependencies():
    """Install Python and Node.js dependencies"""
    print("\n📦 Installing dependencies...")
    
    # Install Python dependencies
    print("Installing Python packages...")
    req_file = 'requirements_simple.txt' if Path('requirements_simple.txt').exists() else 'requirements.txt'
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_file])
    if result.returncode != 0:
        print("❌ Failed to install Python dependencies")
        return False
    
    # Install Node.js dependencies
    print("Installing Node.js packages...")
    result = subprocess.run(['npm', 'install'])
    if result.returncode != 0:
        print("❌ Failed to install Node.js dependencies")
        return False
    
    # Install Playwright browsers
    print("Installing Playwright browsers...")
    result = subprocess.run(['npx', 'playwright', 'install'])
    if result.returncode != 0:
        print("❌ Failed to install Playwright browsers")
        return False
    
    print("✅ All dependencies installed successfully!")
    print()
    print("Next steps:")
    print("1. Set your OpenAI API key in config.py file")
    print("2. Start the MCP server: python main.py start-server")
    print("3. Run automation: python main.py run --interactive")
    print()
    print("Note: Updated to use simplified configuration with config.py")
    return True

def start_mcp_server():
    """Start the MCP server in a separate thread"""
    def run_server():
        try:
            subprocess.run([sys.executable, "main.py", "start-server"], check=True)
        except subprocess.CalledProcessError:
            print("❌ MCP server failed to start")
        except KeyboardInterrupt:
            print("\n🛑 MCP server stopped")
    
    print("\n🚀 Starting MCP server...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(3)
    
    # Check if server is running
    try:
        import requests
        response = requests.get('http://localhost:3000/health', timeout=2)
        if response.status_code == 200:
            print("✅ MCP server is running at http://localhost:3000")
            return True
    except:
        pass
    
    print("⚠️  MCP server might not be ready yet. Continuing anyway...")
    return True

def run_interactive_mode():
    """Run the interactive automation mode"""
    print("\n🎭 Starting interactive mode...")
    print("You can now enter natural language prompts to automate browser actions!")
    print("Type 'help' for available commands, 'quit' to exit.\n")
    
    try:
        subprocess.run([sys.executable, "main.py", "run", "--interactive"])
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def main():
    """Main startup function"""
    print_banner()
    
    if not Path('requirements.txt').exists():
        print("❌ This doesn't appear to be a Playwright automation project directory")
        print("Please run this script from the project root directory")
        return
    
    if not check_requirements():
        print("\n❌ Requirements check failed. Please fix the issues above.")
        return
    
    print("\n🎯 What would you like to do?")
    print("1. Full setup (install dependencies + start system)")
    print("2. Just start the system (skip dependency installation)")
    print("3. Install dependencies only")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            break
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return
    
    if choice == '1':
        if not install_dependencies():
            return
        if not start_mcp_server():
            return
        run_interactive_mode()
    elif choice == '2':
        if not start_mcp_server():
            return
        run_interactive_mode()
    elif choice == '3':
        install_dependencies()
    elif choice == '4':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice. Please run the script again.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the logs and try again.")
