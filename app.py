from flask import Flask, render_template, request, jsonify, send_file
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright
import threading

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'

# Ensure download folder exists
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

class FacebookScraper:
    def __init__(self):
        self.progress = 0
        self.status = "idle"
        self.result = None
        self.error = None
        
    async def scrape_post(self, url):
        """Scrape Facebook post and comments"""
        self.progress = 10
        self.status = "Opening browser..."
        
        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )
                page = await context.new_page()
                
                self.progress = 20
                self.status = f"Navigating to URL..."
                
                # Go to the URL
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                self.progress = 40
                self.status = "Scraping post content..."
                
                # Extract post ID from URL
                post_id = url.split('/')[-1] if '/' in url else url
                
                # Scrape main post
                post_data = {"post_id": post_id, "post_text": "", "post_time": "", "post_author": ""}
                
                # Try to get post author
                author_element = await page.query_selector('h2 span a')
                if author_element:
                    post_data["post_author"] = await author_element.inner_text()
                
                # Get post text
                post_element = await page.query_selector('div[data-ad-comet-preview="message"]')
                if post_element:
                    post_data["post_text"] = (await post_element.inner_text()).strip()
                
                # Get post time
                time_element = await page.query_selector('a[href*="/posts/"] span')
                if time_element:
                    post_data["post_time"] = await time_element.inner_text()
                
                self.progress = 60
                self.status = "Loading comments..."
                
                # Scroll to load comments
                comments = []
                previous_height = 0
                scroll_attempts = 0
                max_scroll_attempts = 10
                
                while scroll_attempts < max_scroll_attempts:
                    # Scroll down
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(2000)
                    
                    # Check if we've reached the bottom
                    new_height = await page.evaluate('document.body.scrollHeight')
                    if new_height == previous_height:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        previous_height = new_height
                    
                    self.status = f"Loading comments... (attempt {scroll_attempts + 1}/{max_scroll_attempts})"
                
                self.progress = 80
                self.status = "Extracting comments..."
                
                # Find all comment elements
                comment_elements = await page.query_selector_all('div[role="article"]')
                
                for index, element in enumerate(comment_elements):
                    try:
                        # Check if it's a comment (not the main post)
                        is_main_post = await element.query_selector('div[data-ad-comet-preview="message"]')
                        if is_main_post:
                            continue
                        
                        # Get comment text
                        text_node = await element.query_selector('div[dir="auto"]')
                        if text_node:
                            text = await text_node.inner_text()
                            
                            # Try to get comment author
                            author_node = await element.query_selector('h3 a')
                            author = await author_node.inner_text() if author_node else "Unknown"
                            
                            if text and text.strip() and text.strip() != post_data["post_text"]:
                                comments.append({
                                    "comment_id": f"comment_{index}",
                                    "author": author.strip(),
                                    "text": text.strip()
                                })
                    except Exception:
                        continue
                
                self.progress = 90
                self.status = "Finalizing data..."
                
                # Prepare result
                self.result = {
                    "url": url,
                    "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "post": post_data,
                    "comments": comments,
                    "total_comments": len(comments)
                }
                
                self.progress = 100
                self.status = "Complete!"
                
                await browser.close()
                return self.result
                
            except Exception as e:
                self.error = str(e)
                self.status = f"Error: {str(e)}"
                await browser.close()
                return None

# Global scraper instance
scraper = FacebookScraper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    global scraper
    url = request.json.get('url', '')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Reset scraper
    scraper = FacebookScraper()
    
    # Run scraper in background
    def run_scraper():
        asyncio.run(scraper.scrape_post(url))
    
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scraping started'})

@app.route('/progress')
def get_progress():
    return jsonify({
        'progress': scraper.progress,
        'status': scraper.status,
        'error': scraper.error
    })

@app.route('/download')
def download():
    if scraper.result:
        # Save to file
        filename = f"facebook_post_{int(time.time())}.json"
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scraper.result, f, ensure_ascii=False, indent=2)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'No data available'}), 404

@app.route('/result')
def get_result():
    if scraper.result:
        return jsonify(scraper.result)
    return jsonify({'error': 'No result yet'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)