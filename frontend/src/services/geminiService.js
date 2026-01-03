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
    this.model = this.genAI.getGenerativeModel({ 
      model: 'gemini-2.5-flash',
      generationConfig: {
        maxOutputTokens: 800,
        temperature: 0.7,
      },
    })
    this.chat = null
  }

  async startChat(context = 'general') {
    if (!this.genAI) return null

    let systemPrompt = ''
    
    if (context === 'general') {
      systemPrompt = `You are TradeWise AI, an expert stock market assistant for Indian equities (NSE/BSE). 

Your role:
- Help users understand their watchlist and market trends
- Provide educational insights about stocks and trading
- Explain technical analysis concepts
- Answer questions about Indian stock market

Guidelines:
- Keep responses concise (max 4-5 sentences)
- Use bullet points for multiple items
- Always include disclaimer that this is not financial advice
- Be conversational and friendly
- Focus on education, not predictions
- Use Indian context (INR currency, NSE/BSE references)

Remember: You're an educational assistant, not a financial advisor.`
    } else {
      // Stock-specific context
      const hasPosition = context.has_position ? 'YES' : 'NO'
      systemPrompt = `You are TradeWise AI analyzing ${context.symbol.replace('.NS', '')} for the user.

CURRENT DATA:
- Stock: ${context.symbol}
- Current Price: ₹${context.current_price}
- AI Signal: ${context.signal}
- User has position: ${hasPosition}
${context.has_position ? `- Buy Price: ₹${context.buy_price}\n- Quantity: ${context.quantity} shares` : ''}

Your role:
- Answer ONLY about THIS specific stock
- Reference the current price and signal when relevant
- If user has a position, consider their entry price in advice
- Explain the AI signal and what it means
- Discuss technical levels and trends for this stock
- Compare user's entry vs current price if they have a position

Guidelines:
- Be specific to ${context.symbol}
- Keep responses focused and actionable
- Always include "This is not financial advice" disclaimer
- If asked about other stocks, politely redirect to this stock
- Use bullet points for clarity
- Limit responses to 5-6 sentences max

Remember: Focus on education about THIS stock specifically.`
    }

    this.chat = this.model.startChat({
      history: [
        {
          role: 'user',
          parts: [{ text: systemPrompt }],
        },
        {
          role: 'model',
          parts: [{ text: 'Understood. I\'m ready to assist with your stock analysis questions.' }],
        },
      ],
    })

    return this.chat
  }

  async sendMessage(message, context = null) {
    try {
      if (!this.chat) {
        await this.startChat(context || 'general')
      }

      const result = await this.chat.sendMessage(message)
      const response = await result.response
      return response.text()
    } catch (error) {
      console.error('Gemini API Error:', error)
      
      if (error.message?.includes('quota')) {
        return 'I\'ve reached my API limit for now. Please try again in a few minutes.'
      }
      
      return 'Sorry, I encountered an error processing your request. Please try again.'
    }
  }

  resetChat() {
    this.chat = null
  }
}

export const geminiService = new GeminiService()