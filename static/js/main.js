// DOM Elements
const urlInput = document.getElementById('url-input');
const qualitySelect = document.getElementById('quality-select');
const startBtn = document.getElementById('start-btn');
const logsContainer = document.getElementById('logs-container');
const statusSection = document.getElementById('status-section');
const progressFill = document.getElementById('progress-fill');
const progressCount = document.getElementById('progress-count');
const progressPercent = document.getElementById('progress-percent');
const currentVideoName = document.getElementById('current-video-name');
const statusText = document.getElementById('status-text');
const folderName = document.getElementById('folder-name');
const downloadTypeRadios = document.querySelectorAll('input[name="download-type"]');
const historyContainer = document.getElementById('history-container');

// State
let statusCheckInterval = null;

// Event Listeners
startBtn.addEventListener('click', startDownload);
downloadTypeRadios.forEach(radio => {
    radio.addEventListener('change', updateUrlHint);
});

// Initialize
updateUrlHint();
loadHistory();

function updateUrlHint() {
    const type = document.querySelector('input[name="download-type"]:checked').value;
    const hint = document.getElementById('url-hint');
    
    if (type === 'channel') {
        hint.textContent = 'Paste a full YouTube channel URL or just the channel handle (e.g., @mkbhd)';
    } else {
        hint.textContent = 'Paste a full YouTube playlist URL';
    }
}

async function startDownload() {
    const url = urlInput.value.trim();
    const quality = qualitySelect.value;
    const type = document.querySelector('input[name="download-type"]:checked').value;
    
    if (!url) {
        showNotification('Please enter a URL or channel handle', 'error');
        return;
    }
    
    startBtn.disabled = true;
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                quality: quality,
                type: type
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start download');
        }
        
        // Show status section and start monitoring
        statusSection.style.display = 'block';
        startMonitorStatus();
        
        showNotification('Download started!', 'success');
    } catch (error) {
        showNotification(error.message, 'error');
        startBtn.disabled = false;
    }
}

function startMonitorStatus() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // Check immediately
    checkStatus();
    
    // Then check every 500ms
    statusCheckInterval = setInterval(checkStatus, 500);
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateUI(data);
        
        // Stop checking if not active and status is complete or error
        if (!data.active && (data.status === 'complete' || data.status === 'error')) {
            clearInterval(statusCheckInterval);
            startBtn.disabled = false;
            loadHistory();
        }
    } catch (error) {
        console.error('Status check error:', error);
    }
}

function updateUI(data) {
    // Update progress
    progressCount.textContent = `${data.progress} / ${data.total}`;
    const percent = data.total > 0 ? Math.round((data.progress / data.total) * 100) : 0;
    progressPercent.textContent = `${percent}%`;
    progressFill.style.width = `${percent}%`;
    
    // Update current video
    currentVideoName.textContent = data.current_video || '-';
    
    // Update status
    folderName.textContent = data.folder || '-';
    updateStatusText(data.status);
    
    // Update logs
    updateLogs(data.logs);
}

function updateStatusText(status) {
    statusText.className = 'value';
    
    switch (status) {
        case 'running':
            statusText.textContent = '⏳ Running';
            statusText.classList.add('status-running');
            break;
        case 'complete':
            statusText.textContent = '✅ Complete';
            statusText.classList.add('status-complete');
            break;
        case 'error':
            statusText.textContent = '❌ Error';
            statusText.classList.add('status-error');
            break;
        default:
            statusText.textContent = '⏱️ Idle';
    }
}

function updateLogs(logs) {
    // Only update if logs changed
    const currentLogs = logsContainer.querySelectorAll('.log-entry').length;
    
    if (logs.length > currentLogs) {
        logsContainer.innerHTML = '';
        
        if (logs.length === 0) {
            logsContainer.innerHTML = '<p class="empty-message">Logs will appear here during download...</p>';
            return;
        }
        
        logs.forEach(log => {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            if (log.includes('❌') || log.includes('Error')) {
                entry.classList.add('error');
            } else if (log.includes('✅')) {
                entry.classList.add('success');
            } else if (log.includes('⏳') || log.includes('📥')) {
                entry.classList.add('warning');
            }
            
            entry.textContent = log;
            logsContainer.appendChild(entry);
        });
        
        // Auto-scroll to bottom
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        
        const history = data.history;
        
        if (Object.keys(history).length === 0) {
            historyContainer.innerHTML = '<p class="empty-message">No download history yet</p>';
            return;
        }
        
        historyContainer.innerHTML = '';
        
        Object.entries(history).forEach(([url, lastVideoId]) => {
            const item = document.createElement('div');
            item.className = 'history-item';
            
            const title = document.createElement('div');
            title.className = 'history-item-title';
            title.textContent = `Last Video ID: ${lastVideoId}`;
            
            const urlEl = document.createElement('div');
            urlEl.className = 'history-item-url';
            urlEl.textContent = url;
            
            item.appendChild(title);
            item.appendChild(urlEl);
            
            // Add click to re-download
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                urlInput.value = url;
                urlInput.focus();
            });
            
            historyContainer.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    const style = document.createElement('style');
    if (!document.querySelector('style[data-notification]')) {
        style.setAttribute('data-notification', 'true');
        style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem 1.5rem;
                border-radius: 6px;
                font-weight: 600;
                z-index: 1000;
                animation: slideIn 0.3s ease;
            }
            
            .notification-success {
                background-color: var(--success);
                color: var(--secondary);
            }
            
            .notification-error {
                background-color: var(--error);
                color: white;
            }
            
            .notification-info {
                background-color: var(--primary);
                color: white;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Keyboard shortcut: Enter to start download
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        startDownload();
    }
});
