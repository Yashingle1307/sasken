import asyncio
import json
import os
import requests
from openai import OpenAI
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from datetime import datetime
import time
from config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.get_log_level()))
logger = logging.getLogger(__name__)

@dataclass
class MCPMessage:
    """Structure for MCP messages"""
    id: str
    method: str
    params: Dict[str, Any]
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class PlaywrightMCPClient:
    """Client for interacting with Playwright MCP server using requests"""
    
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or config.get_mcp_server_url()
        self.message_id_counter = 0
        self.session = requests.Session()
        
    def _get_next_message_id(self) -> str:
        """Generate next message ID"""
        self.message_id_counter += 1
        return f"msg_{self.message_id_counter}"
    
    def send_message(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server"""
        message = MCPMessage(
            id=self._get_next_message_id(),
            method=method,
            params=params
        )
        
        try:
            response = self.session.post(
                f"{self.server_url}/messages",
                json={
                    "id": message.id,
                    "method": message.method,
                    "params": message.params
                },
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"MCP server error: {response.status_code} - {response.text}")
                return {"error": f"Server returned {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to MCP server: {e}")
            return {"error": str(e)}
    
    def navigate_to_page(self, url: str) -> Dict[str, Any]:
        """Navigate to a specific page"""
        return self.send_message("navigate", {"url": url})
    
    def click_element(self, selector: str, timeout: Optional[int] = None):
        params = {"selector": selector}
        if timeout is not None:
           params["timeout"] = timeout
        return self.send_message("click", params)
        
    def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        return self.send_message("type", {"selector": selector, "text": text})
    
    def get_text(self, selector: str) -> Dict[str, Any]:
        """Get text from an element"""
        return self.send_message("getText", {"selector": selector})
    
    def wait_for_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Wait for an element to appear"""
        return self.send_message("waitForElement", {"selector": selector, "timeout": timeout})
    
    def wait_for_navigation(self, timeout: int = 15000) -> Dict[str, Any]:
        """Wait for navigation to complete"""
        return self.send_message("waitForNavigation", {"timeout": timeout})
    
    def wait_for_search_results(self, timeout: int = 15000) -> Dict[str, Any]:
        """Wait specifically for search results to load"""
        return self.send_message("waitForSearchResults", {"timeout": timeout})
    
    def smart_wait(self, timeout: int = 15000) -> Dict[str, Any]:
        """Perform context-aware waiting based on current page"""
        return self.send_message("smartWait", {"timeout": timeout})
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """Press a key (with automatic wait for search if Enter on Google)"""
        return self.send_message("pressKey", {"key": key})
    
    def take_screenshot(self, path: str = None) -> Dict[str, Any]:
        """Take a screenshot with automatic timestamped filename if no path provided"""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"automation_result_{timestamp}.png"
        return self.send_message("screenshot", {"path": path})
    
    def debug_page(self) -> Dict[str, Any]:
        """Debug current page to see available elements"""
        return self.send_message("debug", {})
    
    def close(self):
        """Close the session"""
        self.session.close()

class OpenRouterPlaywrightAssistant:
    """Assistant that uses OpenRouter API to interpret user prompts and generate Playwright actions"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # Configure OpenAI client to use OpenRouter
        self.api_key = api_key or config.get_openrouter_api_key()
        self.model = model or config.get_openrouter_model()
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        self.system_prompt = """
        You are a Playwright automation assistant. Your job is to interpret user requests and convert them into specific Playwright actions.

Available actions:
- navigate_to_page(url): Navigate to a webpage
- click_element(selector): Click on an element using CSS selector
- type_text(selector, text): Type text into an input field
- get_text(selector): Get text content from an element
- wait_for_element(selector, timeout): Wait for an element to appear
- take_screenshot(path): Take a screenshot

When given a user request, analyze it and provide a JSON response with the following structure:
{
    "actions": [
        {
            "action": "action_name",
            "params": {"param1": "value1", "param2": "value2"},
            "description": "Human readable description of this action"
        }
    ],
    "explanation": "Brief explanation of what these actions will accomplish"
}

For example, if the user says "Go to google.com and search for cats", respond with:
{
    "actions": [
        {
            "action": "navigate_to_page",
            "params": {"url": "https://google.com"},
            "description": "Navigate to Google homepage"
        },
        {
            "action": "wait_for_element",
            "params": {"selector": "textarea[name='q']", "timeout": 5000},
            "description": "Wait for search input to be ready"
        },
        {
            "action": "type_text",
            "params": {"selector": "textarea[name='q']", "text": "cats"},
            "description": "Type 'cats' into the search box"
        },
        {
            "action": "click_element",
            "params": {"selector": "input[value='Google Search']"},
            "description": "Click the search button"
        }
    ],
    "explanation": "This will navigate to Google and perform a search for 'cats'"
}

Always provide valid CSS selectors and realistic timeouts. Be specific and clear in your actions.
For Google search:
- Use 'textarea[name="q"]' for the search input (modern Google uses textarea, not input)
- Use 'input[value="Google Search"]' for the search button
- Alternative selectors: 'input[name="btnK"]' or 'button[type="submit"]'

        
        """
    
    def interpret_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """Interpret user prompt and generate Playwright actions"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Get content and check if it's None
            content = response.choices[0].message.content
            if content is None:
                return {"error": "OpenRouter returned empty response"}
            
            logger.info(f"OpenRouter response: {content}")
            
            # Try to parse the JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {
                        "error": "Could not parse OpenRouter response as JSON",
                        "raw_response": content
                    }
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter: {e}")
            return {"error": str(e)}

class PlaywrightAutomationOrchestrator:
    """Main orchestrator that combines OpenRouter and Playwright MCP client"""
    
    def __init__(self, openrouter_api_key: str, mcp_server_url: str = "http://localhost:3000", model: str = "openai/gpt-3.5-turbo"):
        self.assistant = OpenRouterPlaywrightAssistant(openrouter_api_key, model)
        self.mcp_client = PlaywrightMCPClient(mcp_server_url)
        
    def execute_user_prompt(self, user_prompt: str, save_final_screenshot: bool = True) -> Dict[str, Any]:
        """Execute a user prompt end-to-end with optional final screenshot"""
        logger.info(f"Processing user prompt: {user_prompt}")
        
        # Step 1: Interpret the prompt using OpenRouter
        interpretation = self.assistant.interpret_prompt(user_prompt)
        if "error" in interpretation:
            return {"error": "Failed to interpret prompt", "details": interpretation}
        
        logger.info(f"OpenRouter response: {interpretation}")
        
        # Step 2: Execute the actions using Playwright MCP client
        results = []
        
        for action_spec in interpretation.get("actions", []):
            action_name = action_spec["action"]
            params = action_spec["params"]
            description = action_spec.get("description", "")
            
            logger.info(f"Executing: {description}")
            
            # Map action names to client methods
            action_mapping = {
                "navigate_to_page": self.mcp_client.navigate_to_page,
                "click_element": self.mcp_client.click_element,
                "type_text": self.mcp_client.type_text,
                "get_text": self.mcp_client.get_text,
                "wait_for_element": self.mcp_client.wait_for_element,
                "wait_for_navigation": self.mcp_client.wait_for_navigation,
                "wait_for_search_results": self.mcp_client.wait_for_search_results,
                "smart_wait": self.mcp_client.smart_wait,
                "press_key": self.mcp_client.press_key,
                "take_screenshot": self.mcp_client.take_screenshot,
                "debug_page": self.mcp_client.debug_page
            }
            
            if action_name in action_mapping:
                try:
                    result = action_mapping[action_name](**params)
                    results.append({
                        "action": action_name,
                        "params": params,
                        "description": description,
                        "result": result,
                        "success": "error" not in result
                    })
                    
                    # Add small delay between actions for stability
                    time.sleep(0.5)
                    
                except Exception as e:
                    results.append({
                        "action": action_name,
                        "params": params,
                        "description": description,
                        "result": {"error": str(e)},
                        "success": False
                    })
                    # Stop execution on error
                    break
            else:
                results.append({
                    "action": action_name,
                    "params": params,
                    "description": description,
                    "result": {"error": f"Unknown action: {action_name}"},
                    "success": False
                })
                # Stop execution on unknown action
                break
        
        # Step 3: Take final screenshot if requested and there were no critical errors
        final_screenshot_result = None
        if save_final_screenshot:
            try:
                logger.info("Taking final screenshot...")
                screenshot_result = self.mcp_client.take_screenshot()
                
                if "error" not in screenshot_result:
                    final_screenshot_result = screenshot_result
                    results.append({
                        "action": "take_screenshot",
                        "params": {},
                        "description": "Capture final automation result",
                        "result": screenshot_result,
                        "success": True
                    })
                    logger.info(f"Final screenshot saved: {screenshot_result.get('result', {}).get('message', 'Unknown location')}")
                else:
                    logger.error(f"Failed to take final screenshot: {screenshot_result.get('error')}")
                    results.append({
                        "action": "take_screenshot",
                        "params": {},
                        "description": "Capture final automation result",
                        "result": screenshot_result,
                        "success": False
                    })
                    
            except Exception as e:
                logger.error(f"Exception while taking final screenshot: {e}")
                results.append({
                    "action": "take_screenshot",
                    "params": {},
                    "description": "Capture final automation result",
                    "result": {"error": str(e)},
                    "success": False
                })
        
        overall_success = all(r["success"] for r in results if r["action"] != "take_screenshot")
        screenshot_success = final_screenshot_result is not None and "error" not in final_screenshot_result
        
        return {
            "user_prompt": user_prompt,
            "interpretation": interpretation,
            "execution_results": results,
            "overall_success": overall_success,
            "final_screenshot": final_screenshot_result,
            "screenshot_saved": screenshot_success
        }
    
    def close(self):
        """Close the MCP client"""
        self.mcp_client.close()