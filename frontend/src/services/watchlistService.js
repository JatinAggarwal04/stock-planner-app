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

  // Get user's trades
  async getTrades(userId) {
    try {
      const { data, error } = await supabase
        .from('trades')
        .select('*')
        .eq('user_id', userId)

      if (error) throw error
      
      const trades = {}
      data.forEach(trade => {
        trades[trade.symbol] = {
          buyPrice: parseFloat(trade.buy_price),
          quantity: trade.quantity,
          date: trade.buy_date,
        }
      })
      return trades
    } catch (error) {
      console.error('Error fetching trades:', error)
      return {}
    }
  },

  // Record trade
  async recordTrade(userId, symbol, tradeData) {
    try {
      const { data, error} = await supabase
        .from('trades')
        .upsert([
          {
            user_id: userId,
            symbol,
            buy_price: tradeData.buyPrice,
            quantity: tradeData.quantity,
            buy_date: tradeData.date,
          }
        ], { onConflict: 'user_id,symbol' })
        .select()

      if (error) throw error
      return { success: true, data }
    } catch (error) {
      console.error('Error recording trade:', error)
      return { success: false, error }
    }
  },

  // Remove trade
  async removeTrade(userId, symbol) {
    try {
      const { error } = await supabase
        .from('trades')
        .delete()
        .eq('user_id', userId)
        .eq('symbol', symbol)

      if (error) throw error
      return { success: true }
    } catch (error) {
      console.error('Error removing trade:', error)
      return { success: false, error }
    }
  },
}