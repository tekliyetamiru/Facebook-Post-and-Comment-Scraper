from flask import Flask, render_template, request, jsonify, send_file
import asyncio
import json
import os
import time
import glob
from playwright.async_api import async_playwright
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_SCRAPE_THREADS'] = 3  # Maximum parallel scraping threads

# Ensure download folder exists
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Store active scraping sessions
active_sessions = {}

def get_next_filename(base_name="facebook_postdire"):
    """Generate sequential filename like facebook_postdire1.json, facebook_postdire2.json, etc."""
    pattern = os.path.join(app.config['DOWNLOAD_FOLDER'], f'{base_name}*.json')
    existing_files = glob.glob(pattern)
    
    if not existing_files:
        return f'{base_name}1.json'
    
    # Extract numbers from existing files
    numbers = []
    for file in existing_files:
        try:
            # Extract number from filename (facebook_postdireN.json)
            basename = os.path.basename(file)
            num = int(basename.replace(base_name, '').replace('.json', ''))
            numbers.append(num)
        except:
            continue
    
    if numbers:
        next_num = max(numbers) + 1
    else:
        next_num = 1
    
    return f'{base_name}{next_num}.json'

class FacebookScraper:
    def __init__(self, session_id, url, input_index):
        self.session_id = session_id
        self.url = url
        self.input_index = input_index
        self.progress = 0
        self.status = "idle"
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        
    def reset(self):
        """Reset scraper state"""
        self.progress = 0
        self.status = "idle"
        self.result = None
        self.error = None
        
    async def scrape_post(self):
        """Scrape Facebook post and comments with optimized speed"""
        self.reset()
        self.start_time = time.time()
        self.progress = 5
        self.status = "Initializing..."
        
        async with async_playwright() as p:
            try:
                # Launch browser with optimized settings for speed
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-notifications',
                        '--disable-popup-blocking',
                        '--disable-extensions',
                        '--disable-gpu',
                        '--disable-images',
                        '--disable-javascript'  # Disable unnecessary JS for faster loading
                    ]
                )
                
                # Create context with faster settings
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800},
                    device_scale_factor=1,
                    has_touch=False,
                    java_script_enabled=False  # Disable JS completely for faster loading
                )
                
                page = await context.new_page()
                
                self.progress = 15
                self.status = f"Loading post {self.input_index + 1}..."
                
                # Set timeout to be shorter
                page.set_default_timeout(30000)
                
                # Go to the URL with faster loading strategy
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # Reduced wait time
                
                self.progress = 30
                self.status = "Extracting post content..."
                
                # Extract post ID from URL
                post_id = self.url.split('/')[-1] if '/' in self.url else self.url
                
                # Scrape main post - use faster selectors
                post_data = {"post_id": post_id, "post_text": "", "post_time": "", "post_author": ""}
                
                # Use faster evaluation methods
                post_data["post_author"] = await page.evaluate('''
                    () => {
                        const author = document.querySelector('h2 span a');
                        return author ? author.innerText : '';
                    }
                ''')
                
                post_data["post_text"] = await page.evaluate('''
                    () => {
                        const post = document.querySelector('div[data-ad-comet-preview="message"]');
                        return post ? post.innerText.trim() : '';
                    }
                ''')
                
                post_data["post_time"] = await page.evaluate('''
                    () => {
                        const time = document.querySelector('a[href*="/posts/"] span');
                        return time ? time.innerText : '';
                    }
                ''')
                
                self.progress = 50
                self.status = "Loading comments..."
                
                # Optimized scrolling - fewer attempts
                comments = []
                previous_height = 0
                scroll_attempts = 0
                max_scroll_attempts = 5  # Reduced for speed
                
                while scroll_attempts < max_scroll_attempts:
                    # Scroll down faster
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(1000)  # Reduced wait time
                    
                    new_height = await page.evaluate('document.body.scrollHeight')
                    if new_height == previous_height:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        previous_height = new_height
                
                self.progress = 70
                self.status = "Extracting comments..."
                
                # Use faster comment extraction with evaluate
                comments_data = await page.evaluate('''
                    () => {
                        const comments = [];
                        const articles = document.querySelectorAll('div[role="article"]');
                        
                        articles.forEach((article, index) => {
                            // Skip if it's the main post
                            if (article.querySelector('div[data-ad-comet-preview="message"]')) {
                                return;
                            }
                            
                            const textNode = article.querySelector('div[dir="auto"]');
                            if (textNode) {
                                const text = textNode.innerText.trim();
                                if (text) {
                                    const authorNode = article.querySelector('h3 a');
                                    const author = authorNode ? authorNode.innerText.trim() : 'Unknown';
                                    
                                    comments.push({
                                        comment_id: 'comment_' + index,
                                        author: author,
                                        text: text
                                    });
                                }
                            }
                        });
                        
                        return comments;
                    }
                ''')
                
                comments = comments_data
                
                self.progress = 90
                self.status = "Finalizing..."
                
                # Prepare result
                self.result = {
                    "url": self.url,
                    "input_index": self.input_index,
                    "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "scrape_time_seconds": round(time.time() - self.start_time, 2),
                    "post": post_data,
                    "comments": comments,
                    "total_comments": len(comments)
                }
                
                self.progress = 100
                self.status = "Complete!"
                self.end_time = time.time()
                
                await browser.close()
                return self.result
                
            except Exception as e:
                self.error = str(e)
                self.status = f"Error: {str(e)}"
                await browser.close()
                return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get('url', '')
    input_index = data.get('input_index', 0)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create new scraper instance
    scraper = FacebookScraper(session_id, url, input_index)
    active_sessions[session_id] = scraper
    
    # Run scraper in background
    def run_scraper():
        asyncio.run(scraper.scrape_post())
    
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Scraping started',
        'session_id': session_id,
        'input_index': input_index
    })

@app.route('/progress/<session_id>')
def get_progress(session_id):
    scraper = active_sessions.get(session_id)
    if scraper:
        return jsonify({
            'progress': scraper.progress,
            'status': scraper.status,
            'error': scraper.error,
            'input_index': scraper.input_index
        })
    return jsonify({'error': 'Session not found'}), 404

@app.route('/download/<session_id>')
def download(session_id):
    scraper = active_sessions.get(session_id)
    if scraper and scraper.result and scraper.result.get('post'):
        # Generate sequential filename with custom prefix
        filename = get_next_filename("facebook_postdire")
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        # Save the file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scraper.result, f, ensure_ascii=False, indent=2)
        
        # Send file
        response = send_file(
            filepath, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/json'
        )
        
        response.headers['X-Download-Success'] = 'true'
        response.headers['X-Filename'] = filename
        
        # Remove session after download
        del active_sessions[session_id]
        
        return response
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/result/<session_id>')
def get_result(session_id):
    scraper = active_sessions.get(session_id)
    if scraper and scraper.result:
        return jsonify(scraper.result)
    return jsonify({'error': 'No result yet'}), 404

@app.route('/status/all')
def get_all_status():
    """Get status of all active scraping sessions"""
    statuses = []
    for session_id, scraper in active_sessions.items():
        statuses.append({
            'session_id': session_id,
            'input_index': scraper.input_index,
            'url': scraper.url,
            'progress': scraper.progress,
            'status': scraper.status,
            'error': scraper.error,
            'has_result': scraper.result is not None
        })
    return jsonify(statuses)

@app.route('/clear-session/<session_id>', methods=['POST'])
def clear_session(session_id):
    """Clear a specific session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return jsonify({'message': 'Session cleared'})
    return jsonify({'error': 'Session not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)