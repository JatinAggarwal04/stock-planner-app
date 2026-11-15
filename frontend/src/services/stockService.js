//frontend/src/services/stockService.js
import api from './api'

export const stockService = {
  // Get full analysis
  async analyzeStock(symbol, accountSize = 100000, riskPerTrade = 2) {
    try {
      const response = await api.get(`/analyze/${symbol}`, {
        params: { account_size: accountSize, risk_per_trade: riskPerTrade },
      })
      return response.data
    } catch (error) {
      console.error('analyzeStock error:', error)
      throw error
    }
  },

  // Get personalized analysis
  async getPersonalizedAnalysis(symbol, buyPrice, quantity, accountSize = 100000, riskPerTrade = 2) {
    try {
      const response = await api.get(`/analyze/${symbol}/personalized`, {
        params: {
          buy_price: buyPrice,
          quantity: quantity,
          account_size: accountSize,
          risk_per_trade: riskPerTrade,
        },
      })
      return response.data
    } catch (error) {
      console.error('getPersonalizedAnalysis error:', error)
      // Don't fallback on rate-limit (429) errors — it would just make things worse
      if (error?.response?.status === 429) {
        throw error
      }
      // Fallback to standard analysis for other errors
      return await this.analyzeStock(symbol, accountSize, riskPerTrade)
    }
  },

  // Quick quote for watchlist
  async getQuote(symbol) {
    try {
      const response = await api.get(`/quote/${symbol}`)
      return response.data
    } catch (error) {
      console.error('getQuote error:', error)
      throw error
    }
  },

  // Search stocks
  async searchStocks(query) {
    try {
      const response = await api.get('/search', {
        params: { query }
      })
      return response.data
    } catch (error) {
      console.error('searchStocks error:', error)
      return []
    }
  },

  // Get historical data
  async getHistory(symbol, period = '1mo') {
    try {
      const response = await api.get(`/history/${symbol}`, {
        params: { period }
      })
      return response.data
    } catch (error) {
      console.error('getHistory error:', error)
      throw error
    }
  },

  // Exit plans, alerts and portfolio risk for held positions ({ symbol: { quantity, averagePrice, lastUpdated } })
  async reviewHoldings(trades) {
    const holdings = Object.entries(trades)
      .filter(([, t]) => t.quantity)
      .map(([symbol, t]) => ({
        symbol,
        quantity: t.quantity,
        average_price: t.averagePrice,
        since: t.lastUpdated || null,
      }))
    if (holdings.length === 0) return null
    const response = await api.post('/portfolio/review', { holdings })
    return response.data
  },

  // Batch quotes
  async getBatchQuotes(symbols) {
    const promises = symbols.map((symbol) => 
      this.getQuote(symbol).catch(err => ({
        symbol,
        error: true,
        message: err.message || 'Failed to fetch',
      }))
    )
    
    const results = await Promise.all(promises)
    return results
  },
}