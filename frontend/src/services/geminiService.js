import { GoogleGenerativeAI } from '@google/generative-ai'

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY

class GeminiService {
  constructor() {
    if (!API_KEY) {
      console.warn('Gemini API key not found')
      this.genAI = null
      return
    }
    
    this.genAI = new GoogleGenerativeAI(API_KEY)
    this.model = this.genAI.getGenerativeModel({ model: 'gemini-pro' })
    this.chat = null
  }

  async startChat(context = 'general') {
    if (!this.genAI) return null

    let systemPrompt = ''
    
    if (context === 'general') {
      systemPrompt = `You are TradeWise AI, an expert stock market assistant for Indian equities. 
      You help users understand their watchlist, market trends, and make informed trading decisions.
      Keep responses concise and actionable. Use bullet points when listing information.
      Always include disclaimers that this is not financial advice.`
    } else {
      // Stock-specific context
      systemPrompt = `You are TradeWise AI, analyzing ${context.symbol} for the user.
      Current Price: ₹${context.current_price}
      Signal: ${context.signal}
      User has ${context.has_position ? 'a position' : 'no position'} in this stock.
      ${context.has_position ? `Buy Price: ₹${context.buy_price}, Quantity: ${context.quantity}` : ''}
      
      Provide specific, actionable insights about THIS stock only.
      Reference the current data when answering questions.
      Always include disclaimers that this is not financial advice.`
    }

    this.chat = this.model.startChat({
      history: [
        {
          role: 'user',
          parts: [{ text: systemPrompt }],
        },
        {
          role: 'model',
          parts: [{ text: 'I understand. I\'m ready to assist you with stock market analysis.' }],
        },
      ],
      generationConfig: {
        maxOutputTokens: 500,
        temperature: 0.7,
      },
    })

    return this.chat
  }

  async sendMessage(message, context = null) {
    try {
      if (!this.chat) {
        await this.startChat(context)
      }

      const result = await this.chat.sendMessage(message)
      const response = await result.response
      return response.text()
    } catch (error) {
      console.error('Gemini API Error:', error)
      return 'Sorry, I encountered an error. Please try again.'
    }
  }

  resetChat() {
    this.chat = null
  }
}

export const geminiService = new GeminiService()