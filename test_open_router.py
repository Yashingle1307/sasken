import os
import sys
from pathlib import Path
from config import config
from client import OpenRouterPlaywrightAssistant

def test_openrouter_connection():
    """Test OpenRouter API connection"""
    print("🧪 Testing OpenRouter API Connection")
    print("=" * 50)
    
    # Check configuration
    api_key = config.get_openrouter_api_key()
    model = config.get_openrouter_model()
    
    if not api_key:
        print("❌ No OpenRouter API key found!")
        print("Please set OPENROUTER_API_KEY in your config.py or environment variables")
        return False
    
    print(f"✅ API Key: {'*' * (len(api_key) - 8) + api_key[-8:] if len(api_key) > 8 else '*' * len(api_key)}")
    print(f"✅ Model: {model}")
    print(f"✅ Using: {'OpenRouter' if config.is_using_openrouter() else 'Legacy OpenAI key'}")
    print()
    
    # Test API call
    print("🔄 Testing API call...")
    try:
        assistant = OpenRouterPlaywrightAssistant(api_key, model)
        
        test_prompt = "Navigate to google.com and search for 'test'"
        print(f"Test prompt: {test_prompt}")
        print()
        
        result = assistant.interpret_prompt(test_prompt)
        
        if "error" in result:
            print(f"❌ API call failed: {result['error']}")
            if "raw_response" in result:
                print(f"Raw response: {result['raw_response']}")
            return False
        
        print("✅ API call successful!")
        print(f"Explanation: {result.get('explanation', 'No explanation')}")
        print(f"Actions count: {len(result.get('actions', []))}")
        
        # Show first action as example
        actions = result.get('actions', [])
        if actions:
            first_action = actions[0]
            print(f"First action: {first_action.get('action')} - {first_action.get('description')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\n🔧 Testing Configuration")
    print("=" * 50)
    
    try:
        # Test config validation
        is_valid = config.validate()
        print(f"Config validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Show all config values
        print(f"OpenRouter API Key: {'✅ Set' if config.get_openrouter_api_key() else '❌ Not set'}")
        print(f"OpenRouter Model: {config.get_openrouter_model()}")
        print(f"MCP Server URL: {config.get_mcp_server_url()}")
        print(f"MCP Server Port: {config.get_mcp_server_port()}")
        print(f"Playwright Headless: {config.get_playwright_headless()}")
        print(f"Playwright Timeout: {config.get_playwright_timeout()}")
        print(f"Log Level: {config.get_log_level()}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_mcp_server():
    """Test MCP server connection"""
    print("\n🌐 Testing MCP Server Connection")
    print("=" * 50)
    
    try:
        import requests
        server_url = config.get_mcp_server_url()
        
        print(f"Testing connection to: {server_url}")
        
        # Test health endpoint
        response = requests.get(f"{server_url}/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ MCP Server is running!")
            print(f"Status: {health_data.get('status', 'unknown')}")
            print(f"Browser: {health_data.get('browser_status', 'unknown')}")
            return True
        else:
            print(f"❌ MCP Server responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP server")
        print("Make sure to start the server with: npm start")
        return False
    except Exception as e:
        print(f"❌ MCP Server test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🎭 Playwright Automation - OpenRouter Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))
    
    # Test OpenRouter API
    api_ok = test_openrouter_connection()
    results.append(("OpenRouter API", api_ok))
    
    # Test MCP Server
    mcp_ok = test_mcp_server()
    results.append(("MCP Server", mcp_ok))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Start MCP server: python main.py start-server")
        print("2. Run automation: python main.py run --interactive")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Set OPENROUTER_API_KEY in config.py or environment")
        print("- Start MCP server: npm start")
        print("- Check your internet connection")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())