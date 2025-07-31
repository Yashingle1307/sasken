import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration manager for the application"""
    
    def __init__(self):
        # Load configuration from config.example or environment variables
        self.config_file = Path("config.example")
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file or environment variables"""
        # Default values
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = "openai/gpt-3.5-turbo"  # Default to gpt-3.5-turbo via OpenRouter
        self.mcp_server_url = "http://localhost:3000"
        self.mcp_server_port = 3000
        self.playwright_headless = True
        self.playwright_timeout = 30000
        self.log_level = "INFO"
        
        # Legacy OpenAI support (for backward compatibility)
        self.openai_api_key = None
        
        # Try to load from config.example file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Convert boolean values
                            if value.lower() in ('true', 'false'):
                                value = value.lower() == 'true'
                            # Convert numeric values
                            elif value.isdigit():
                                value = int(value)
                            
                            # Set the configuration value
                            if key == 'OPENROUTER_API_KEY':
                                self.openrouter_api_key = str(value)
                            elif key == 'OPENROUTER_MODEL':
                                self.openrouter_model = str(value)
                            elif key == 'OPENAI_API_KEY':  # Legacy support
                                self.openai_api_key = str(value)
                            elif key == 'MCP_SERVER_URL':
                                self.mcp_server_url = str(value)
                            elif key == 'MCP_SERVER_PORT':
                                self.mcp_server_port = int(str(value))
                            elif key == 'PLAYWRIGHT_HEADLESS':
                                self.playwright_headless = bool(value) if isinstance(value, bool) else str(value).lower() == 'true'
                            elif key == 'PLAYWRIGHT_TIMEOUT':
                                self.playwright_timeout = int(str(value))
                            elif key == 'LOG_LEVEL':
                                self.log_level = str(value)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_file}: {e}")
        
        # Override with environment variables if they exist
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY', self.openrouter_api_key)
        self.openrouter_model = os.getenv('OPENROUTER_MODEL', self.openrouter_model)
        self.openai_api_key = os.getenv('OPENAI_API_KEY', self.openai_api_key)  # Legacy support
        self.mcp_server_url = os.getenv('MCP_SERVER_URL', self.mcp_server_url)
        self.mcp_server_port = int(os.getenv('MCP_SERVER_PORT', str(self.mcp_server_port)))
        self.playwright_headless = os.getenv('PLAYWRIGHT_HEADLESS', str(self.playwright_headless)).lower() == 'true'
        self.playwright_timeout = int(os.getenv('PLAYWRIGHT_TIMEOUT', str(self.playwright_timeout)))
        self.log_level = os.getenv('LOG_LEVEL', self.log_level)
    
    def validate(self) -> bool:
        """Validate that all required configuration is present"""
        # Check for OpenRouter API key first, fallback to OpenAI for backward compatibility
        if not self.openrouter_api_key and not self.openai_api_key:
            print("❌ OpenRouter API key is required (OPENROUTER_API_KEY)")
            print("   Alternatively, set OPENAI_API_KEY for legacy OpenAI support")
            return False
        
        if not self.mcp_server_url:
            print("❌ MCP server URL is required")
            return False
        
        # Warn if using legacy OpenAI key
        if not self.openrouter_api_key and self.openai_api_key:
            print("⚠️  Using legacy OPENAI_API_KEY. Consider switching to OPENROUTER_API_KEY")
        
        return True
    
    def get_openrouter_api_key(self) -> str:
        """Get OpenRouter API key, fallback to OpenAI key for backward compatibility"""
        return self.openrouter_api_key or self.openai_api_key or ""
    
    def get_openrouter_model(self) -> str:
        """Get OpenRouter model"""
        return self.openrouter_model
    
    def get_openai_api_key(self) -> str:
        """Get legacy OpenAI API key (for backward compatibility)"""
        return self.get_openrouter_api_key()
    
    def get_mcp_server_url(self) -> str:
        """Get MCP server URL"""
        return self.mcp_server_url
    
    def get_mcp_server_port(self) -> int:
        """Get MCP server port"""
        return self.mcp_server_port
    
    def get_playwright_headless(self) -> bool:
        """Get Playwright headless mode"""
        return self.playwright_headless
    
    def get_playwright_timeout(self) -> int:
        """Get Playwright timeout"""
        return self.playwright_timeout
    
    def get_log_level(self) -> str:
        """Get log level"""
        return self.log_level
    
    def is_using_openrouter(self) -> bool:
        """Check if using OpenRouter (vs legacy OpenAI)"""
        return bool(self.openrouter_api_key)

# Create a global config instance
config = Config()