import api from './api'

export const stockService = {
  // Get full analysis
  async analyzeStock(symbol, accountSize = 100000, riskPerTrade = 2) {
    try {
      console.log(`Calling API: /analyze/${symbol}`)
      const response = await api.get(`/analyze/${symbol}`, {
        params: { account_size: accountSize, risk_per_trade: riskPerTrade },
      })
      console.log('API Response:', response.data)
      return response.data
    } catch (error) {
      console.error('analyzeStock error:', error)
      throw error
    }
  },

  // Get personalized analysis
  async getPersonalizedAnalysis(symbol, buyPrice, quantity, accountSize = 100000, riskPerTrade = 2) {
    try {
      console.log(`Calling API: /analyze/${symbol}/personalized`)
      const response = await api.get(`/analyze/${symbol}/personalized`, {
        params: {
          buy_price: buyPrice,
          quantity: quantity,
          account_size: accountSize,
          risk_per_trade: riskPerTrade,
        },
      })
      console.log('Personalized API Response:', response.data)
      return response.data
    } catch (error) {
      console.error('getPersonalizedAnalysis error:', error)
      // Fallback to standard analysis if personalized fails
      console.log('Falling back to standard analysis')
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