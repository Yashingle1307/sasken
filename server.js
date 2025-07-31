import http from 'http';
import { chromium } from 'playwright';
import cors from 'cors';
import fs from 'fs';
import path from 'path';

const PORT = process.env.PORT || 3000;

// Global browser and page instances
let browser = null;
let page = null;

// Configuration from environment or defaults
const config = {
  headless: process.env.PLAYWRIGHT_HEADLESS === 'true' || false,
  timeout: parseInt(process.env.PLAYWRIGHT_TIMEOUT) || 30000,
  viewport: {
    width: parseInt(process.env.VIEWPORT_WIDTH) || 1280,
    height: parseInt(process.env.VIEWPORT_HEIGHT) || 720
  }
};

async function initializeBrowser() {
  if (!browser) {
    try {
      browser = await chromium.launch({
        headless: config.headless,
        args: [
          '--no-sandbox', 
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-web-security',
          '--allow-running-insecure-content'
        ]
      });
      console.log(`Browser initialized successfully (${config.headless ? 'headless' : 'headed'} mode)`);
    } catch (error) {
      console.error('Failed to initialize browser:', error);
      throw error;
    }
  }
  return browser;
}

async function getPage() {
  if (!page) {
    const browserInstance = await initializeBrowser();
    page = await browserInstance.newPage();
    
    // Set viewport
    await page.setViewportSize(config.viewport);
    
    // Set default timeout
    page.setDefaultTimeout(config.timeout);
    
    // Add some useful defaults
    await page.setExtraHTTPHeaders({
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    });
    
    console.log(`New page created with viewport ${config.viewport.width}x${config.viewport.height}`);
  }
  return page;
}

// Helper function to handle Playwright actions
// Add this enhanced error handling to your server.js
async function handlePlaywrightAction(action, params) {
  console.log(`Starting action: ${action} with params:`, params);
  
  try {
    const pageInstance = await getPage();
    
    switch (action) {
      case 'navigate':
        console.log(`Navigating to: ${params.url}`);
        await pageInstance.goto(params.url, { 
          waitUntil: 'networkidle',
          timeout: 30000 
        });
        console.log('Navigation completed');
        
        // Verify navigation actually worked
        const currentUrl = pageInstance.url();
        console.log(`Current URL after navigation: ${currentUrl}`);
        
        return { 
          success: true, 
          message: `Navigated to ${params.url}`,
          currentUrl: currentUrl
        };
        
      case 'click':
        console.log(`Clicking on: ${params.selector}`);
        
        // Check if element exists first
        const element = await pageInstance.$(params.selector);
        if (!element) {
          console.error(`Element not found: ${params.selector}`);
          return { 
            error: `Element not found: ${params.selector}`,
            availableElements: await getAvailableElements(pageInstance)
          };
        }
        
        // Wait for element to be visible and clickable
        await pageInstance.waitForSelector(params.selector, { 
          state: 'visible',
          timeout: 10000 
        });
        
        // Take screenshot before clicking for debugging
        await pageInstance.screenshot({ 
          path: `debug_before_click_${Date.now()}.png` 
        });
        
        await pageInstance.click(params.selector);
        console.log('Click completed');
        
        // Wait a bit and take screenshot after clicking
        await pageInstance.waitForTimeout(2000);
        await pageInstance.screenshot({ 
          path: `debug_after_click_${Date.now()}.png` 
        });
        
        return { 
          success: true, 
          message: `Clicked on ${params.selector}`,
          currentUrl: pageInstance.url()
        };
        
      case 'type':
        console.log(`Typing "${params.text}" into: ${params.selector}`);
        
        // Check if element exists
        const inputElement = await pageInstance.$(params.selector);
        if (!inputElement) {
          console.error(`Input element not found: ${params.selector}`);
          return { 
            error: `Input element not found: ${params.selector}`,
            availableInputs: await getAvailableInputs(pageInstance)
          };
        }
        
        await pageInstance.waitForSelector(params.selector, { 
          state: 'visible',
          timeout: 10000 
        });
        
        // Clear and type
        await pageInstance.fill(params.selector, '');
        await pageInstance.type(params.selector, params.text, { delay: 100 });
        
        // Verify text was entered
        const enteredText = await pageInstance.inputValue(params.selector);
        console.log(`Text entered: "${enteredText}"`);
        
        return { 
          success: true, 
          message: `Typed "${params.text}" into ${params.selector}`,
          enteredText: enteredText
        };
        
      case 'waitForElement':
        console.log(`Waiting for element: ${params.selector}`);
        
        try {
          await pageInstance.waitForSelector(params.selector, { 
            timeout: params.timeout || 10000,
            state: 'visible'
          });
          console.log('Element found and visible');
          return { 
            success: true, 
            message: `Element ${params.selector} found and visible` 
          };
        } catch (error) {
          console.error(`Element not found within timeout: ${params.selector}`);
          return { 
            error: `Element not found within timeout: ${params.selector}`,
            availableElements: await getAvailableElements(pageInstance)
          };
        }
        
      case 'screenshot':
        console.log(`Taking screenshot: ${params.path}`);
        const screenshotPath = params.path || 'screenshot.png';
        await pageInstance.screenshot({ 
          path: screenshotPath,
          fullPage: true 
        });
        console.log('Screenshot completed');
        return { 
          success: true, 
          message: `Screenshot saved to ${screenshotPath}`,
          currentUrl: pageInstance.url()
        };
        
      case 'debug':
        console.log('Debug mode: inspecting page');
        const title = await pageInstance.title();
        const url = pageInstance.url();
        
        // Get all clickable elements
        const clickableElements = await pageInstance.$$eval(
          'a, button, input[type="submit"], input[type="button"], [onclick]',
          elements => elements.map(el => ({
            tag: el.tagName.toLowerCase(),
            text: el.textContent?.trim() || '',
            id: el.id || '',
            className: el.className || '',
            href: el.href || '',
            type: el.type || ''
          })).slice(0, 10) // Limit to first 10
        );
        
        // Get all input elements
        const inputs = await pageInstance.$$eval(
          'input, textarea, select',
          elements => elements.map(el => ({
            tag: el.tagName.toLowerCase(),
            name: el.name || '',
            id: el.id || '',
            type: el.type || '',
            placeholder: el.placeholder || '',
            className: el.className || ''
          }))
        );
        
        return { 
          success: true, 
          debug: {
            title,
            url,
            clickableElements,
            inputs
          }
        };
        
      default:
        console.log(`Unknown action: ${action}`);
        return { error: `Unknown action: ${action}` };
    }
  } catch (error) {
    console.error(`Error executing ${action}:`, error);
    
    // Take error screenshot for debugging
    try {
      const pageInstance = await getPage();
      await pageInstance.screenshot({ 
        path: `error_${action}_${Date.now()}.png` 
      });
    } catch (screenshotError) {
      console.error('Failed to take error screenshot:', screenshotError);
    }
    
    return { 
      error: error.message,
      stack: error.stack,
      currentUrl: (await getPage()).url()
    };
  }
}

// Helper function to get available elements for debugging
async function getAvailableElements(page) {
  try {
    return await page.$$eval('*', elements => 
      elements.map(el => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        className: el.className || '',
        text: el.textContent?.trim().substring(0, 50) || ''
      })).filter(el => el.id || el.className || el.text).slice(0, 20)
    );
  } catch (error) {
    return ['Error getting elements'];
  }
}

// Helper function to get available input elements
async function getAvailableInputs(page) {
  try {
    return await page.$$eval('input, textarea, select', elements =>
      elements.map(el => ({
        tag: el.tagName.toLowerCase(),
        name: el.name || '',
        id: el.id || '',
        type: el.type || '',
        placeholder: el.placeholder || ''
      }))
    );
  } catch (error) {
    return ['Error getting inputs'];
  }
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);

  try {
    if (req.url === '/messages' && req.method === 'POST') {
      let body = '';
      req.on('data', chunk => {
        body += chunk.toString();
      });
      
      req.on('end', async () => {
        try {
          const message = JSON.parse(body);
          console.log('Received HTTP message:', message);
          
          const { method, params } = message;
          const result = await handlePlaywrightAction(method, params);
          
          console.log('Action result:', result);
          
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            id: message.id,
            result: result,
            success: !result.error,
            timestamp: new Date().toISOString()
          }));
        } catch (error) {
          console.error('Error processing HTTP message:', error);
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ 
            error: error.message,
            timestamp: new Date().toISOString()
          }));
        }
      });
      
      req.setTimeout(45000, () => {
        console.error('Request timeout');
        res.writeHead(408, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
          error: 'Request timeout',
          timestamp: new Date().toISOString()
        }));
      });
      
    } else if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        browser_status: browser ? 'connected' : 'not_connected',
        page_status: page ? 'ready' : 'not_ready',
        config: {
          headless: config.headless,
          timeout: config.timeout,
          viewport: config.viewport
        }
      }));
      
    } else if (req.url === '/config' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        config: config,
        browser_connected: !!browser,
        page_ready: !!page
      }));
      
    } else if (req.url === '/close' && req.method === 'POST') {
      if (page) {
        await page.close();
        page = null;
      }
      if (browser) {
        await browser.close();
        browser = null;
      }
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        message: 'Browser closed successfully',
        timestamp: new Date().toISOString()
      }));
      
    } else {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
    }
  } catch (error) {
    console.error('Error handling request:', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      error: 'Internal Server Error', 
      message: error.message,
      timestamp: new Date().toISOString()
    }));
  }
});

server.listen(PORT, () => {
  console.log(`🎭 Playwright HTTP Server running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`⚡ HTTP endpoint: http://localhost:${PORT}/messages (POST)`);
  console.log(`⚙️  Configuration: http://localhost:${PORT}/config`);
  console.log(`🔒 Close browser: http://localhost:${PORT}/close (POST)`);
  console.log(`🖥️  Browser mode: ${config.headless ? 'HEADLESS' : 'HEADED'}`);
  console.log(`⏱️  Timeout: ${config.timeout}ms`);
  console.log(`📱 Viewport: ${config.viewport.width}x${config.viewport.height}`);
});

initializeBrowser().catch(console.error);

async function shutdown() {
  console.log('Shutting down gracefully...');
  
  if (page) {
    try {
      await page.close();
      console.log('Page closed');
    } catch (error) {
      console.error('Error closing page:', error);
    }
  }
  
  if (browser) {
    try {
      await browser.close();
      console.log('Browser closed');
    } catch (error) {
      console.error('Error closing browser:', error);
    }
  }
  
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  shutdown();
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
  shutdown();
});