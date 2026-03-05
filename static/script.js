// Store active sessions
const activeSessions = new Map();
let inputCounter = 3; // Start with 3 input fields

// Initialize the page with 3 input fields
document.addEventListener('DOMContentLoaded', () => {
    for (let i = 0; i < 3; i++) {
        addInputField();
    }
    startStatusPolling();
});

function addInputField() {
    const grid = document.getElementById('inputGrid');
    const inputCount = grid.children.length + 1;
    
    const card = document.createElement('div');
    card.className = 'input-card';
    card.id = `input-card-${inputCount}`;
    card.innerHTML = `
        <h3>
            <span class="post-number">${inputCount}</span>
            Post ${inputCount}
            <button class="remove-btn" onclick="removeInputField('input-card-${inputCount}')" title="Remove">×</button>
        </h3>
        <input 
            type="url" 
            id="url-${inputCount}" 
            placeholder="Enter Facebook post URL ${inputCount}"
            class="url-input"
        >
        <button 
            class="scrape-btn" 
            id="scrape-${inputCount}" 
            onclick="startScraping(${inputCount})"
        >
            🚀 Start Scraping
        </button>
        <div class="progress-mini" id="progress-${inputCount}-container" style="display: none;">
            <div class="progress-mini-fill" id="progress-${inputCount}-fill" style="width: 0%"></div>
        </div>
        <div class="status-mini" id="status-${inputCount}"></div>
    `;
    
    grid.appendChild(card);
}

function removeInputField(cardId) {
    const card = document.getElementById(cardId);
    if (card && document.getElementById('inputGrid').children.length > 1) {
        card.remove();
        // Renumber remaining cards
        renumberInputCards();
    }
}

function renumberInputCards() {
    const cards = document.querySelectorAll('.input-card');
    cards.forEach((card, index) => {
        const newNumber = index + 1;
        card.id = `input-card-${newNumber}`;
        card.querySelector('.post-number').textContent = newNumber;
        card.querySelector('h3').innerHTML = `
            <span class="post-number">${newNumber}</span>
            Post ${newNumber}
            <button class="remove-btn" onclick="removeInputField('input-card-${newNumber}')" title="Remove">×</button>
        `;
        card.querySelector('.url-input').id = `url-${newNumber}`;
        card.querySelector('.scrape-btn').id = `scrape-${newNumber}`;
        card.querySelector('.scrape-btn').setAttribute('onclick', `startScraping(${newNumber})`);
        card.querySelector(`#progress-${index + 1}-container`)?.setAttribute('id', `progress-${newNumber}-container`);
        card.querySelector(`#progress-${index + 1}-fill`)?.setAttribute('id', `progress-${newNumber}-fill`);
        card.querySelector(`#status-${index + 1}`)?.setAttribute('id', `status-${newNumber}`);
    });
}

function clearAllInputs() {
    document.querySelectorAll('.url-input').forEach(input => {
        input.value = '';
    });
}

async function startScraping(inputIndex) {
    const urlInput = document.getElementById(`url-${inputIndex}`);
    const url = urlInput.value.trim();
    const scrapeBtn = document.getElementById(`scrape-${inputIndex}`);
    
    if (!url) {
        alert(`Please enter a URL for Post ${inputIndex}`);
        return;
    }
    
    if (!isValidFacebookUrl(url)) {
        alert('Please enter a valid Facebook URL');
        return;
    }
    
    // Disable button and show progress
    scrapeBtn.disabled = true;
    document.getElementById(`progress-${inputIndex}-container`).style.display = 'block';
    updateProgress(inputIndex, 0, 'Starting...');
    
    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                url: url, 
                input_index: inputIndex 
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            enableInput(inputIndex);
        } else {
            // Store session
            activeSessions.set(data.session_id, {
                inputIndex: inputIndex,
                sessionId: data.session_id,
                url: url
            });
            
            // Start polling for this session
            pollSessionProgress(data.session_id, inputIndex);
        }
    } catch (error) {
        showError('Failed to start scraping: ' + error.message);
        enableInput(inputIndex);
    }
}

function pollSessionProgress(sessionId, inputIndex) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/progress/${sessionId}`);
            const data = await response.json();
            
            if (data.error) {
                clearInterval(pollInterval);
                showError(data.error);
                enableInput(inputIndex);
                return;
            }
            
            updateProgress(inputIndex, data.progress, data.status);
            
            if (data.progress >= 100) {
                clearInterval(pollInterval);
                fetchResult(sessionId, inputIndex);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 300); // Poll every 300ms for faster updates
}

function updateProgress(inputIndex, percent, status) {
    const fillElement = document.getElementById(`progress-${inputIndex}-fill`);
    const statusElement = document.getElementById(`status-${inputIndex}`);
    
    if (fillElement) {
        fillElement.style.width = percent + '%';
    }
    if (statusElement) {
        statusElement.textContent = `${percent}% - ${status}`;
    }
}

async function fetchResult(sessionId, inputIndex) {
    try {
        const response = await fetch(`/result/${sessionId}`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            enableInput(inputIndex);
        } else {
            // Show download button in the card
            const statusElement = document.getElementById(`status-${inputIndex}`);
            statusElement.innerHTML = `
                <span>✅ Complete!</span>
                <button class="download-mini" onclick="downloadResult('${sessionId}', ${inputIndex})">
                    💾 Download
                </button>
            `;
        }
    } catch (error) {
        showError('Failed to fetch results: ' + error.message);
        enableInput(inputIndex);
    }
}

async function downloadResult(sessionId, inputIndex) {
    try {
        const response = await fetch(`/download/${sessionId}`);
        
        if (!response.ok) {
            throw new Error('Download failed');
        }
        
        const blob = await response.blob();
        const filename = response.headers.get('X-Filename') || 'facebook_postdire.json';
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Show success and reset the card
        showTemporaryMessage(`✅ Downloaded: ${filename}`);
        
        // Reset the card for new input
        resetInputCard(inputIndex);
        
        // Remove session from active sessions
        activeSessions.delete(sessionId);
        
    } catch (error) {
        alert('❌ Download failed: ' + error.message);
    }
}

function resetInputCard(inputIndex) {
    const urlInput = document.getElementById(`url-${inputIndex}`);
    const scrapeBtn = document.getElementById(`scrape-${inputIndex}`);
    const progressContainer = document.getElementById(`progress-${inputIndex}-container`);
    const statusElement = document.getElementById(`status-${inputIndex}`);
    
    if (urlInput) urlInput.value = '';
    if (scrapeBtn) scrapeBtn.disabled = false;
    if (progressContainer) progressContainer.style.display = 'none';
    if (statusElement) statusElement.textContent = '';
}

function enableInput(inputIndex) {
    const scrapeBtn = document.getElementById(`scrape-${inputIndex}`);
    if (scrapeBtn) scrapeBtn.disabled = false;
}

function isValidFacebookUrl(url) {
    return url.includes('facebook.com/') || url.includes('fb.com/') || url.includes('web.facebook.com/');
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorSection').style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        document.getElementById('errorSection').style.display = 'none';
    }, 5000);
}

function showTemporaryMessage(message) {
    const msgDiv = document.createElement('div');
    msgDiv.textContent = message;
    msgDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 15px 25px;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(msgDiv);
    
    setTimeout(() => {
        msgDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(msgDiv);
        }, 300);
    }, 3000);
}

function startStatusPolling() {
    // Poll for all active sessions status every 2 seconds
    setInterval(async () => {
        try {
            const response = await fetch('/status/all');
            const sessions = await response.json();
            
            // Update UI with all session statuses
            updateSessionsDisplay(sessions);
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 2000);
}

function updateSessionsDisplay(sessions) {
    const container = document.getElementById('sessionsContainer');
    
    if (sessions.length === 0) {
        container.innerHTML = '<p class="small" style="text-align: center;">No active scraping sessions</p>';
        return;
    }
    
    let html = '<h3>Active Sessions</h3>';
    sessions.forEach(session => {
        const statusClass = session.error ? 'error' : 
                           session.progress >= 100 ? 'completed' : 'active';
        
        html += `
            <div class="session-card ${statusClass}">
                <div class="session-header">
                    <span class="session-title">Post ${session.input_index + 1}</span>
                    <span class="session-status ${statusClass}">${session.status}</span>
                </div>
                <div class="session-progress">
                    <div class="session-progress-fill" style="width: ${session.progress}%"></div>
                </div>
                <div class="session-url">${truncateUrl(session.url)}</div>
                ${session.has_result ? `
                    <div class="session-actions">
                        <button onclick="downloadResult('${session.session_id}', ${session.input_index})" 
                                class="download-mini">Download</button>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function truncateUrl(url, maxLength = 50) {
    return url.length > maxLength ? url.substring(0, maxLength) + '...' : url;
}

// Allow Enter key to start scraping
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && e.target.classList.contains('url-input')) {
        const inputIndex = e.target.id.split('-')[1];
        startScraping(parseInt(inputIndex));
    }
});