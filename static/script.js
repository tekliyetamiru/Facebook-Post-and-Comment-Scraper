let progressInterval;

function startScraping() {
    const url = document.getElementById('urlInput').value.trim();
    
    if (!url) {
        alert('Please enter a Facebook post URL');
        return;
    }
    
    if (!url.includes('facebook.com/') && !url.includes('fb.com/')) {
        alert('Please enter a valid Facebook URL');
        return;
    }
    
    // Show progress section
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
    
    // Disable input and button during scraping
    document.getElementById('urlInput').disabled = true;
    document.getElementById('scrapeBtn').disabled = true;
    
    // Reset progress
    updateProgress(0, 'Starting...');
    
    // Start scraping
    fetch('/scrape', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            // Start polling for progress
            progressInterval = setInterval(checkProgress, 500);
        }
    })
    .catch(error => {
        showError('Failed to start scraping: ' + error.message);
    });
}

function checkProgress() {
    fetch('/progress')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                clearInterval(progressInterval);
                return;
            }
            
            updateProgress(data.progress, data.status);
            
            if (data.progress >= 100) {
                clearInterval(progressInterval);
                fetchResult();
            }
        })
        .catch(error => {
            console.error('Progress check failed:', error);
        });
}

function updateProgress(percent, status) {
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('progressPercentage').textContent = percent + '%';
    document.getElementById('status').textContent = status;
}

function fetchResult() {
    fetch('/result')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
            } else {
                displayResults(data);
            }
        })
        .catch(error => {
            showError('Failed to fetch results: ' + error.message);
        });
}

function displayResults(data) {
    // Update stats
    document.getElementById('postTextPreview').textContent = 
        data.post.post_text ? data.post.post_text.substring(0, 50) + '...' : 'No text found';
    document.getElementById('commentCount').textContent = data.total_comments;
    document.getElementById('postAuthor').textContent = data.post.post_author || 'Unknown';
    
    // Display full post content
    document.getElementById('postContent').innerHTML = 
        `<strong>Author:</strong> ${data.post.post_author || 'Unknown'}<br>
         <strong>Time:</strong> ${data.post.post_time || 'Unknown'}<br>
         <strong>Post ID:</strong> ${data.post.post_id}<br><br>
         ${data.post.post_text || 'No post text found'}`;
    
    // Display comments preview
    const commentsList = document.getElementById('commentsList');
    commentsList.innerHTML = '';
    
    if (data.comments && data.comments.length > 0) {
        data.comments.slice(0, 10).forEach(comment => {
            const commentDiv = document.createElement('div');
            commentDiv.className = 'comment-item';
            commentDiv.innerHTML = `
                <div class="comment-author">${comment.author}</div>
                <div class="comment-text">${comment.text}</div>
            `;
            commentsList.appendChild(commentDiv);
        });
        
        if (data.comments.length > 10) {
            const moreDiv = document.createElement('div');
            moreDiv.className = 'comment-item';
            moreDiv.innerHTML = `<em>... and ${data.comments.length - 10} more comments</em>`;
            commentsList.appendChild(moreDiv);
        }
    } else {
        commentsList.innerHTML = '<p>No comments found</p>';
    }
    
    // Show result section
    document.getElementById('resultSection').style.display = 'block';
    
    // Re-enable input
    document.getElementById('urlInput').disabled = false;
    document.getElementById('scrapeBtn').disabled = false;
}

function downloadData() {
    window.location.href = '/download';
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('progressSection').style.display = 'none';
    
    // Re-enable input
    document.getElementById('urlInput').disabled = false;
    document.getElementById('scrapeBtn').disabled = false;
    
    clearInterval(progressInterval);
}

// Allow Enter key to start scraping
document.getElementById('urlInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        startScraping();
    }
});