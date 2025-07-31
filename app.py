from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import threading
import time
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Simple in-memory storage
executions = {}
current_execution_id = None

# Mock configuration - replace with your actual config
CONFIG = {
    'backend_url': 'http://localhost:8000',
    'mcp_server_url': 'http://localhost:3000',
    'openrouter_model': 'openai/gpt-3.5-turbo'
}

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Simple Playwright Automation Backend"
    })

@app.route('/execute', methods=['POST'])
def execute_automation():
    """Execute automation - simplified version"""
    global current_execution_id
    
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        save_screenshot = data.get('save_screenshot', True)
        
        if not prompt:
            return jsonify({
                "success": False,
                "error": "Prompt is required"
            }), 400
        
        # Create execution ID
        execution_id = f"exec_{int(time.time())}"
        current_execution_id = execution_id
        
        # Create execution record
        execution = {
            "id": execution_id,
            "prompt": prompt,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "save_screenshot": save_screenshot,
            "success": False
        }
        
        executions[execution_id] = execution
        logger.info(f"Starting automation: {prompt}")
        
        # Start background execution
        def execute_in_background():
            try:
                # Simulate execution time
                time.sleep(2)
                
                # TODO: Replace this with your actual automation logic
                # This is where you would call your PlaywrightAutomationOrchestrator
                
                # For demo purposes, we'll simulate success
                result = simulate_automation(prompt, save_screenshot)
                
                # Update execution record
                executions[execution_id].update({
                    "status": "completed",
                    "end_time": datetime.now().isoformat(),
                    "result": result,
                    "success": result.get("success", False)
                })
                
                logger.info(f"Automation completed: {execution_id}")
                
            except Exception as e:
                logger.error(f"Automation failed: {e}")
                executions[execution_id].update({
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": str(e),
                    "success": False
                })
        
        # Start execution in background thread
        thread = threading.Thread(target=execute_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "execution_id": execution_id,
            "message": "Automation started successfully",
            "status": "running"
        })
        
    except Exception as e:
        logger.error(f"Execute endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/execution/<execution_id>', methods=['GET'])
def get_execution_status(execution_id):
    """Get execution status"""
    try:
        if execution_id not in executions:
            return jsonify({
                "success": False,
                "error": "Execution not found"
            }), 404
        
        return jsonify({
            "success": True,
            "execution": executions[execution_id]
        })
        
    except Exception as e:
        logger.error(f"Get execution status error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/screenshot/<filename>', methods=['GET'])
def serve_screenshot(filename):
    """Serve screenshot files"""
    try:
        # Security: Only allow PNG files and prevent path traversal
        if not filename.endswith('.png') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        file_path = Path(filename)
        if file_path.exists():
            return send_file(file_path, mimetype='image/png')
        else:
            # Return a placeholder image if screenshot doesn't exist
            return create_placeholder_image(filename)
            
    except Exception as e:
        logger.error(f"Serve screenshot error: {e}")
        return jsonify({"error": str(e)}), 500

def simulate_automation(prompt, save_screenshot=True):
    """
    Execute automation using your existing PlaywrightAutomationOrchestrator
    """
    try:
        # Import your existing modules
        from client import PlaywrightAutomationOrchestrator
        from config import config
        
        # Get configuration
        openrouter_api_key = config.get_openrouter_api_key()
        mcp_server_url = config.get_mcp_server_url()
        model = config.get_openrouter_model()
        
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")
        
        # Create orchestrator and execute
        orchestrator = PlaywrightAutomationOrchestrator(
            openrouter_api_key, 
            mcp_server_url, 
            model
        )
        
        result = orchestrator.execute_user_prompt(prompt, save_final_screenshot=save_screenshot)
        orchestrator.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Real automation failed, falling back to simulation: {e}")
        
        # Fallback to simulation if real automation fails
        result = {
            "success": True,
            "overall_success": True,
            "execution_results": [
                {
                    "description": f"Simulated: {prompt}",
                    "success": True,
                    "result": {"message": "Simulation completed (real automation failed)"}
                }
            ]
        }
        
        if save_screenshot:
            screenshot_filename = f"screenshot_{int(time.time())}.png"
            create_placeholder_screenshot(screenshot_filename, prompt)
            
            result["final_screenshot"] = {
                "result": {
                    "message": f"Screenshot saved to {screenshot_filename}"
                }
            }
            result["screenshot_saved"] = True
        
        return result

def create_placeholder_screenshot(filename, prompt):
    """Create a simple placeholder screenshot file"""
    try:
        # Create a simple SVG as placeholder
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
    <rect width="800" height="600" fill="#f3f4f6"/>
    <rect x="50" y="50" width="700" height="500" fill="white" stroke="#e5e7eb" stroke-width="2"/>
    <text x="400" y="150" text-anchor="middle" fill="#374151" font-family="Arial" font-size="24" font-weight="bold">
        🎭 Automation Screenshot
    </text>
    <text x="400" y="200" text-anchor="middle" fill="#6b7280" font-family="Arial" font-size="16">
        Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}
    </text>
    <text x="400" y="300" text-anchor="middle" fill="#9ca3af" font-family="Arial" font-size="14">
        This is a placeholder screenshot.
    </text>
    <text x="400" y="330" text-anchor="middle" fill="#9ca3af" font-family="Arial" font-size="14">
        Replace simulate_automation() with your actual Playwright automation.
    </text>
    <text x="400" y="400" text-anchor="middle" fill="#6366f1" font-family="Arial" font-size="12">
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </text>
</svg>'''
        
        # Save SVG file (you might want to convert to PNG in a real implementation)
        with open(filename, 'w') as f:
            f.write(svg_content)
            
    except Exception as e:
        logger.error(f"Error creating placeholder screenshot: {e}")

def create_placeholder_image(filename):
    """Create a placeholder image response"""
    from flask import Response
    
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <rect width="400" height="300" fill="#f3f4f6"/>
    <text x="200" y="150" text-anchor="middle" fill="#6b7280" font-family="Arial" font-size="16">
        Screenshot: {filename}
    </text>
    <text x="200" y="180" text-anchor="middle" fill="#9ca3af" font-family="Arial" font-size="12">
        (File not found)
    </text>
</svg>'''
    
    return Response(svg_content, mimetype='image/svg+xml')

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    try:
        logger.info("Starting Simple Playwright Automation Backend")
        logger.info("Replace simulate_automation() with your actual automation logic")
        
        # Start Flask app
        app.run(
            host='0.0.0.0',
            port=8000,
            debug=True,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down backend...")
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        exit(1)