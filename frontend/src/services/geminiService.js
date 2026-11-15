//frontend/src/services/geminiService.js
// import { v4 as uuidv4 } from 'uuid' // Removed to avoid dependency issue

import { authHeaders, handleUnauthorized } from './api'

// Use VITE_API_URL for consistency across the app
const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const generateSessionId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

class GeminiService {
  constructor() {
    this.sessionId = generateSessionId() // Generate session ID for agent context
    this.chat = null // Stub for compatibility
  }

  // Stub to maintain compatibility with ChatInterface
  async startChat(context = 'general') {
    // In backend-driven chat, we just reset or prepare context metadata
    this.currentContext = context
    return true 
  }

  async sendMessage(message, context = null) {
    try {
      const payload = {
        user_id: this.sessionId,
        message: message,
        // Only stock contexts are objects; 'general' mode sends an empty context
        context: [context, this.currentContext].find((c) => c && typeof c === 'object') || {}
      }

      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(await authHeaders()),
        },
        body: JSON.stringify(payload),
      })

      if (response.status === 401) {
        handleUnauthorized()
        return 'Your session has expired. Please sign in again.'
      }

      if (response.status === 429) {
        return "You're sending messages too quickly. Please wait a minute and try again."
      }

      if (!response.ok) {
        throw new Error('Failed to fetch from backend agent')
      }

      const data = await response.json()
      return data.response

    } catch (error) {
      console.error('Agent API Error:', error)
      return "I'm having trouble connecting to the TradeWise Agent server. Please try again."
    }
  }

  resetChat() {
    this.sessionId = generateSessionId() // New session on reset
    this.currentContext = null
  }
}

export const geminiService = new GeminiService()