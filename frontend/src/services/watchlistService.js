//frontend/src/services/watchlistService.js
import { supabase } from './supabase'

export const watchlistService = {
  // Fetch user's watchlist from Supabase
  async getWatchlist(userId) {
    try {
      const { data, error } = await supabase
        .from('watchlists')
        .select('*')
        .eq('user_id', userId)
        .order('added_at', { ascending: false })

      if (error) throw error
      return data.map(item => item.symbol)
    } catch (error) {
      console.error('Error fetching watchlist:', error)
      return []
    }
  },

  // Add stock to watchlist
  async addToWatchlist(userId, symbol) {
    try {
      const { data, error } = await supabase
        .from('watchlists')
        .insert([{ user_id: userId, symbol }])
        .select()

      if (error) throw error
      return { success: true, data }
    } catch (error) {
      console.error('Error adding to watchlist:', error)
      return { success: false, error }
    }
  },

  // Remove from watchlist
  async removeFromWatchlist(userId, symbol) {
    try {
      const { error } = await supabase
        .from('watchlists')
        .delete()
        .eq('user_id', userId)
        .eq('symbol', symbol)

      if (error) throw error
      return { success: true }
    } catch (error) {
      console.error('Error removing from watchlist:', error)
      return { success: false, error }
    }
  },

  // Get active portfolio positions
  async getTrades(userId) {
    try {
      const { data, error } = await supabase
        .from('portfolio')
        .select('*')
        .eq('user_id', userId)

      if (error) throw error
      
      const portfolio = {}
      data.forEach(item => {
        if (item.quantity > 0 || item.quantity < 0) { // Only active positions
          portfolio[item.symbol] = {
            averagePrice: parseFloat(item.average_price),
            quantity: item.quantity,
            lastUpdated: item.last_updated,
          }
        }
      })
      return portfolio
    } catch (error) {
      console.error('Error fetching portfolio:', error)
      return {}
    }
  },

  // Get transaction history for a symbol
  async getTransactions(userId, symbol) {
    try {
      const { data, error } = await supabase
        .from('transactions')
        .select('*')
        .eq('user_id', userId)
        .eq('symbol', symbol)
        .order('trade_date', { ascending: false })
        .limit(5)

      if (error) throw error
      return data
    } catch (error) {
      console.error('Error fetching transactions:', error)
      return []
    }
  },

  // Record a new trade (Buy/Sell) and update portfolio
  async recordTrade(userId, symbol, tradeData) {
    try {
      // 1. Fetch current portfolio position
      const { data: currentPosition } = await supabase
        .from('portfolio')
        .select('*')
        .eq('user_id', userId)
        .eq('symbol', symbol)
        .single()

      let newQuantity = 0
      let newAveragePrice = 0

      const currentQty = currentPosition ? currentPosition.quantity : 0
      const currentAvg = currentPosition ? parseFloat(currentPosition.average_price) : 0
      const tradeQty = parseInt(tradeData.quantity)
      const tradePrice = parseFloat(tradeData.price)

      let realized_pl = null

      // 2. Calculate New Position Logic
      if (tradeData.type === 'BUY') {
        newQuantity = currentQty + tradeQty
        
        // Check for Short Cover (Profit/Loss realization)
        if (currentQty < 0) {
             const qtyCovered = Math.min(Math.abs(currentQty), tradeQty)
             // Profit on short = (Sell Avg - Buy Price) * Qty
             realized_pl = (currentAvg - tradePrice) * qtyCovered
        }

        // Calculate Weighted Average Price only for Buys (if active long)
        // If switching from Short to Long, math is complex. Simplified:
        if (currentQty >= 0) {
            const totalValue = (currentQty * currentAvg) + (tradeQty * tradePrice)
            newAveragePrice = totalValue / newQuantity
        } else {
            // Covering a short position (buying back)
            // Just reducing the negative quantity, Avg price of SHORT remains same?
            // Usually avg price of open position doesn't change when reducing.
            newAveragePrice = currentAvg
            // If flipping to long... edge case.
            if (newQuantity > 0) {
                 // Remaining positive part is new long at this trade price
                 newAveragePrice = tradePrice 
            }
        }
      } else { // SELL (or Short Sell)
        newQuantity = currentQty - tradeQty
        
        // Check for Long Sell (Profit/Loss realization)
        if (currentQty > 0) {
             const qtySold = Math.min(currentQty, tradeQty)
             // Profit on long = (Sell Price - Buy Avg) * Qty
             realized_pl = (tradePrice - currentAvg) * qtySold
        }

        if (currentQty <= 0) {
            // Adding to short position
             const totalValue = (Math.abs(currentQty) * currentAvg) + (tradeQty * tradePrice)
             newAveragePrice = totalValue / Math.abs(newQuantity) // Avg Short Price
        } else {
             // Selling long position (reducing)
             // Avg price doesn't change when selling
             newAveragePrice = currentAvg
             if (newQuantity < 0) {
                 // Flipping to short
                 newAveragePrice = tradePrice
             }
        }
      }

      // 3. Upsert into Portfolio
      const { error: portfolioError } = await supabase
        .from('portfolio')
        .upsert([
          {
            user_id: userId,
            symbol,
            quantity: newQuantity,
            average_price: newAveragePrice,
            last_updated: new Date().toISOString()
          }
        ], { onConflict: 'user_id,symbol' })

      if (portfolioError) throw portfolioError

      // 4. Record Transaction History
      const { error: txnError } = await supabase
        .from('transactions')
        .insert([
          {
            user_id: userId,
            symbol,
            type: tradeData.type, // 'BUY' or 'SELL'
            quantity: tradeQty,
            price: tradePrice,
            trade_date: tradeData.date,
            realized_pl: realized_pl // Store the calculated P&L
          }
        ])


      if (txnError) throw txnError

      return { success: true, newPosition: { quantity: newQuantity, averagePrice: newAveragePrice } }
    } catch (error) {
      console.error('Error recording trade:', error)
      return { success: false, error }
    }
  },
}