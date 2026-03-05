# Facebook Multi-Post Scraper 🚀

A powerful web application for scraping multiple Facebook posts and comments simultaneously with high speed and efficiency. Extract post content, comments, author information, and timestamps from public Facebook posts.

## 📋 Features

- **Multiple Post Scraping**: Scrape up to 3 posts simultaneously (expandable)
- **High Speed**: Optimized settings for fastest possible scraping
- **Parallel Processing**: Each post scrapes in its own browser instance
- **Real-time Progress**: Live progress tracking for each post
- **Automatic File Naming**: Sequential file naming (facebook_postdire1.json, facebook_postdire2.json, etc.)
- **Clean UI**: Modern, responsive interface with individual controls for each post
- **JSON Output**: Well-structured JSON output with all post data and comments

## 🚀 Performance Optimizations

- Disabled images and JavaScript for faster loading
- Reduced timeout and wait times
- Optimized scroll attempts
- Batch DOM operations
- Parallel browser instances
- Fast polling (300ms intervals)

## 📦 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🔧 Installation

### Step 1: Clone or Download the Project

<!-- Clone the repository (if using git) -->
git clone <your-repository-url>
cd facebook-multi-post-scraper

### Step 2: Create Virtual Environment (Recommended)

<!-- On Windows-->
python -m venv venv
venv\Scripts\

### Step 3: Install Dependencies

pip install -r requirements.txt
### Step 4: Install Playwright Browsers

### Install Chromium browser for Playwright
playwright install chromium

# If you encounter issues, try:
python -m playwright install 


### finally: Start the Flask Server

<!--Make sure you're in the project directory with virtual environment activated-->
python app.py