import api from './api'

export const stockService = {
  // Get full analysis
  async analyzeStock(symbol, accountSize = 100000, riskPerTrade = 2) {
    const response = await api.get(`/analyze/${symbol}`, {
      params: { account_size: accountSize, risk_per_trade: riskPerTrade },
    })
    return response.data
  },

  // Get personalized analysis
  async getPersonalizedAnalysis(symbol, buyPrice, quantity, accountSize = 100000, riskPerTrade = 2) {
    const response = await api.get(`/analyze/${symbol}/personalized`, {
      params: {
        buy_price: buyPrice,
        quantity: quantity,
        account_size: accountSize,
        risk_per_trade: riskPerTrade,
      },
    })
    return response.data
  },

  // Quick quote for watchlist
  async getQuote(symbol) {
    const response = await api.get(`/quote/${symbol}`)
    return response.data
  },

  // Batch quotes
  async getBatchQuotes(symbols) {
    const promises = symbols.map((symbol) => this.getQuote(symbol))
    const results = await Promise.allSettled(promises)
    
    return results.map((result, index) => {
      if (result.status === 'fulfilled') {
        return result.value
      }
      return {
        symbol: symbols[index],
        error: true,
        message: 'Failed to fetch',
      }
    })
  },
}