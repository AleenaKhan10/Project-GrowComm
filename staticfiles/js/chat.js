// Modern Chat Application JavaScript

class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.currentUserId = null;
        this.currentUserName = null;
        this.messages = [];
        this.isTyping = false;
        this.typingTimeout = null;
        this.autoRefreshInterval = null;
        this.lastMessageId = null;
        
        // Get CSRF token
        this.csrfToken = this.getCookie('csrftoken');
        
        // Initialize
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadConversations();
        this.startAutoRefresh();
        
        // Load first conversation if exists
        const firstConversation = document.querySelector('.conversation-item');
        if (firstConversation) {
            firstConversation.click();
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    bindEvents() {
        // Message input events
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            messageInput.addEventListener('input', () => {
                this.handleTyping();
                this.autoResizeTextarea(messageInput);
            });
        }
        
        // Send button
        const sendButton = document.getElementById('send-button');
        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        // Search functionality
        const searchInput = document.getElementById('conversation-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterConversations(e.target.value);
            });
        }
        
        // Mobile back button
        const backButton = document.querySelector('.back-button');
        if (backButton) {
            backButton.addEventListener('click', () => {
                document.querySelector('.chat-area').classList.remove('active');
            });
        }
    }
    
    loadConversations() {
        fetch('/messages/api/conversations/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.renderConversations(data.conversations);
            }
        })
        .catch(error => console.error('Error loading conversations:', error));
    }
    
    renderConversations(conversations) {
        const conversationList = document.querySelector('.conversation-list');
        if (!conversationList) return;
        
        conversationList.innerHTML = '';
        
        if (!conversations || conversations.length === 0) {
            conversationList.innerHTML = `
                <div class="empty-state">
                    <p style="text-align: center; padding: 40px; color: #667781;">
                        No conversations yet<br>
                        <a href="/communities/users/" style="color: #00a884;">Start a conversation</a>
                    </p>
                </div>
            `;
            return;
        }
        
        conversations.forEach(conv => {
            const convElement = this.createConversationElement(conv);
            conversationList.appendChild(convElement);
        });
    }
    
    createConversationElement(conversation) {
        const div = document.createElement('div');
        div.className = 'conversation-item';
        div.dataset.conversationId = conversation.id;
        div.dataset.userId = conversation.other_user.id;
        div.dataset.userName = conversation.other_user.name;
        
        const timeAgo = this.formatTimeAgo(conversation.last_message?.timestamp);
        const messagePreview = conversation.last_message?.content || 'Start a conversation';
        const unreadCount = conversation.unread_count || 0;
        
        div.innerHTML = `
            <div class="conversation-avatar">
                ${conversation.other_user.avatar_url ? 
                    `<img src="${conversation.other_user.avatar_url}" alt="${conversation.other_user.name}">` :
                    `<div class="avatar-initial" style="background: ${this.getAvatarColor(conversation.other_user.name)}">
                        ${this.getInitials(conversation.other_user.name)}
                    </div>`
                }
                ${conversation.other_user.is_online ? '<span class="online-indicator"></span>' : ''}
            </div>
            <div class="conversation-info">
                <div class="conversation-header">
                    <span class="conversation-name">${conversation.other_user.name}</span>
                    <span class="conversation-time">${timeAgo}</span>
                </div>
                <div class="conversation-preview">
                    <span class="conversation-message">${this.escapeHtml(messagePreview)}</span>
                    ${unreadCount > 0 ? `<span class="unread-count">${unreadCount}</span>` : ''}
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => this.selectConversation(conversation));
        
        return div;
    }
    
    selectConversation(conversation) {
        this.currentConversationId = conversation.id;
        this.currentUserId = conversation.other_user.id;
        this.currentUserName = conversation.other_user.name;
        
        // Update UI
        this.updateConversationSelection(conversation.id);
        this.updateChatHeader(conversation);
        this.loadMessages(conversation.id);
        
        // Show chat area on mobile
        if (window.innerWidth <= 768) {
            document.querySelector('.chat-area').classList.add('active');
        }
        
        // Show input area
        document.querySelector('.message-input-container').style.display = 'flex';
        document.querySelector('.empty-chat-state')?.remove();
    }
    
    updateConversationSelection(conversationId) {
        // Remove active class from all conversations
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to selected conversation
        const selectedConv = document.querySelector(`.conversation-item[data-conversation-id="${conversationId}"]`);
        if (selectedConv) {
            selectedConv.classList.add('active');
            // Mark as read
            const unreadBadge = selectedConv.querySelector('.unread-count');
            if (unreadBadge) {
                unreadBadge.remove();
            }
        }
    }
    
    updateChatHeader(conversation) {
        const header = document.querySelector('.chat-header');
        if (!header) return;
        
        header.innerHTML = `
            ${window.innerWidth <= 768 ? '<button class="back-button"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg></button>' : ''}
            <div class="chat-user-info">
                <div class="chat-user-avatar">
                    ${conversation.other_user.avatar_url ? 
                        `<img src="${conversation.other_user.avatar_url}" alt="${conversation.other_user.name}">` :
                        `<div class="avatar-initial" style="background: ${this.getAvatarColor(conversation.other_user.name)}">
                            ${this.getInitials(conversation.other_user.name)}
                        </div>`
                    }
                </div>
                <div class="chat-user-details">
                    <div class="chat-user-name">${conversation.other_user.name}</div>
                    <div class="chat-user-status">${conversation.other_user.is_online ? 'Online' : 'Offline'}</div>
                </div>
            </div>
            <div class="chat-actions">
                <button class="chat-action-btn" title="Voice Call">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
                    </svg>
                </button>
                <button class="chat-action-btn" title="Video Call">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                </button>
                <button class="chat-action-btn" title="More Options">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
                    </svg>
                </button>
            </div>
        `;
        
        // Re-bind back button event
        const backButton = header.querySelector('.back-button');
        if (backButton) {
            backButton.addEventListener('click', () => {
                document.querySelector('.chat-area').classList.remove('active');
            });
        }
    }
    
    loadMessages(conversationId) {
        const container = document.querySelector('.messages-container');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner" style="margin: 20px auto;"></div>';
        
        fetch(`/messages/api/conversation/${conversationId}/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.messages = data.messages || [];
                this.renderMessages();
                this.scrollToBottom();
            }
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            container.innerHTML = '<p style="text-align: center; color: #667781;">Error loading messages</p>';
        });
    }
    
    renderMessages() {
        const container = document.querySelector('.messages-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.messages.length === 0) {
            container.innerHTML = `
                <div class="empty-chat-state">
                    <div class="empty-chat-title">Start a conversation</div>
                    <div class="empty-chat-text">Send a message to begin chatting</div>
                </div>
            `;
            return;
        }
        
        let lastDate = null;
        
        this.messages.forEach(message => {
            // Add date divider if needed
            const messageDate = new Date(message.timestamp).toLocaleDateString();
            if (messageDate !== lastDate) {
                const divider = document.createElement('div');
                divider.className = 'message-date-divider';
                divider.innerHTML = `<span class="date-divider-text">${this.formatDate(message.timestamp)}</span>`;
                container.appendChild(divider);
                lastDate = messageDate;
            }
            
            // Add message
            const messageElement = this.createMessageElement(message);
            container.appendChild(messageElement);
        });
        
        // Update last message ID
        if (this.messages.length > 0) {
            this.lastMessageId = this.messages[this.messages.length - 1].id;
        }
    }
    
    createMessageElement(message) {
        const div = document.createElement('div');
        const isSent = message.is_sent;
        div.className = `message-wrapper ${isSent ? 'sent' : 'received'}`;
        
        div.innerHTML = `
            <div class="message-bubble ${isSent ? 'sent' : 'received'}">
                ${!isSent ? `<div class="message-sender">${message.sender_name}</div>` : ''}
                <div class="message-content">${this.escapeHtml(message.content)}</div>
                <div class="message-time">
                    ${this.formatTime(message.timestamp)}
                    ${isSent ? this.getMessageStatus(message.status) : ''}
                </div>
            </div>
        `;
        
        return div;
    }
    
    getMessageStatus(status) {
        const icons = {
            sent: '<svg class="status-sent" viewBox="0 0 16 16"><path fill="currentColor" d="M12.5 3.5L5 11l-3.5-3.5 1.06-1.06L5 8.88l6.44-6.44L12.5 3.5z"/></svg>',
            delivered: '<svg class="status-delivered" viewBox="0 0 16 16"><path fill="currentColor" d="M12.5 3.5L5 11l-3.5-3.5 1.06-1.06L5 8.88l6.44-6.44L12.5 3.5z"/><path fill="currentColor" d="M16 3.5L8.5 11 7 9.5l1.06-1.06L8.5 8.88l6.44-6.44L16 3.5z"/></svg>',
            read: '<svg class="status-read" viewBox="0 0 16 16"><path fill="currentColor" d="M12.5 3.5L5 11l-3.5-3.5 1.06-1.06L5 8.88l6.44-6.44L12.5 3.5z"/><path fill="currentColor" d="M16 3.5L8.5 11 7 9.5l1.06-1.06L8.5 8.88l6.44-6.44L16 3.5z"/></svg>'
        };
        return `<span class="message-status">${icons[status] || icons.sent}</span>`;
    }
    
    sendMessage() {
        const input = document.getElementById('message-input');
        const content = input.value.trim();
        
        if (!content || !this.currentConversationId) return;
        
        // Disable input while sending
        input.disabled = true;
        const sendButton = document.getElementById('send-button');
        sendButton.disabled = true;
        
        // Optimistically add message to UI
        const tempMessage = {
            id: 'temp-' + Date.now(),
            content: content,
            is_sent: true,
            sender_name: 'You',
            timestamp: new Date().toISOString(),
            status: 'sending'
        };
        
        this.messages.push(tempMessage);
        this.renderMessages();
        this.scrollToBottom();
        
        // Clear input
        input.value = '';
        this.autoResizeTextarea(input);
        
        // Send to server
        fetch('/messages/api/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                conversation_id: this.currentConversationId,
                content: content
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update message with real data
                const index = this.messages.findIndex(m => m.id === tempMessage.id);
                if (index !== -1) {
                    this.messages[index] = data.message;
                }
                this.renderMessages();
                this.updateConversationPreview(this.currentConversationId, content);
            } else {
                // Remove failed message
                this.messages = this.messages.filter(m => m.id !== tempMessage.id);
                this.renderMessages();
                alert('Failed to send message: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            // Remove failed message
            this.messages = this.messages.filter(m => m.id !== tempMessage.id);
            this.renderMessages();
            alert('Failed to send message');
        })
        .finally(() => {
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
        });
    }
    
    updateConversationPreview(conversationId, message) {
        const convElement = document.querySelector(`.conversation-item[data-conversation-id="${conversationId}"]`);
        if (convElement) {
            const preview = convElement.querySelector('.conversation-message');
            if (preview) {
                preview.textContent = message;
            }
            const time = convElement.querySelector('.conversation-time');
            if (time) {
                time.textContent = 'now';
            }
        }
    }
    
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            // Send typing indicator to server
            this.sendTypingIndicator(true);
        }
        
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.isTyping = false;
            this.sendTypingIndicator(false);
        }, 1000);
    }
    
    sendTypingIndicator(isTyping) {
        if (!this.currentConversationId) return;
        
        // This would send typing status to server
        // For now, it's a placeholder
        console.log('Typing:', isTyping);
    }
    
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }
    
    filterConversations(query) {
        const conversations = document.querySelectorAll('.conversation-item');
        const lowerQuery = query.toLowerCase();
        
        conversations.forEach(conv => {
            const name = conv.querySelector('.conversation-name').textContent.toLowerCase();
            const message = conv.querySelector('.conversation-message').textContent.toLowerCase();
            
            if (name.includes(lowerQuery) || message.includes(lowerQuery)) {
                conv.style.display = 'flex';
            } else {
                conv.style.display = 'none';
            }
        });
    }
    
    startAutoRefresh() {
        // Auto-refresh messages every 5 seconds
        this.autoRefreshInterval = setInterval(() => {
            if (this.currentConversationId) {
                this.refreshMessages();
            }
        }, 5000);
    }
    
    refreshMessages() {
        if (!this.currentConversationId) return;
        
        fetch(`/messages/api/conversation/${this.currentConversationId}/new/${this.lastMessageId || 0}/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.messages && data.messages.length > 0) {
                // Add new messages
                this.messages.push(...data.messages);
                this.renderMessages();
                this.scrollToBottom();
                
                // Show notification if chat is not focused
                if (!document.hasFocus()) {
                    this.showNotification(data.messages[0]);
                }
            }
        })
        .catch(error => console.error('Error refreshing messages:', error));
    }
    
    showNotification(message) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`New message from ${message.sender_name}`, {
                body: message.content,
                icon: '/static/images/icon.png'
            });
        }
    }
    
    scrollToBottom() {
        const container = document.querySelector('.messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) return 'just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h';
        if (diff < 604800) return Math.floor(diff / 86400) + 'd';
        
        return date.toLocaleDateString();
    }
    
    formatDate(timestamp) {
        const date = new Date(timestamp);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: 'short', 
                day: 'numeric' 
            });
        }
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getInitials(name) {
        if (!name) return '?';
        const parts = name.split(' ');
        if (parts.length > 1) {
            return parts[0][0] + parts[parts.length - 1][0];
        }
        return name.substring(0, 2).toUpperCase();
    }
    
    getAvatarColor(name) {
        const colors = [
            '#25D366', '#128C7E', '#075E54', '#34B7F1',
            '#00BFA5', '#00ACC1', '#0097A7', '#00838F'
        ];
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    }
    
    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
    }
}

// Initialize chat app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
    
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.chatApp) {
        window.chatApp.destroy();
    }
});