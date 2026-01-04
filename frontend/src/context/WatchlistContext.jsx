//frontend/src/context/WatchlistContext.jsx
import { create } from 'zustand'
import { watchlistService } from '../services/watchlistService'

export const useWatchlistStore = create((set, get) => ({
  watchlist: [],
  trades: {},
  initialized: false,
  userId: null,

  // Initialize from Supabase
  initialize: async (userId) => {
    if (!userId) return
    
    set({ userId })
    const watchlist = await watchlistService.getWatchlist(userId)
    const trades = await watchlistService.getTrades(userId)
    set({ watchlist, trades, initialized: true })
  },

  addToWatchlist: async (symbol) => {
    const { userId, watchlist } = get()
    if (!userId) return

    if (!watchlist.includes(symbol)) {
      await watchlistService.addToWatchlist(userId, symbol)
      set({ watchlist: [...watchlist, symbol] })
    }
  },

  removeFromWatchlist: async (symbol) => {
    const { userId } = get()
    if (!userId) return

    await watchlistService.removeFromWatchlist(userId, symbol)
    set({ watchlist: get().watchlist.filter((s) => s !== symbol) })
  },

  isInWatchlist: (symbol) => {
    return get().watchlist.includes(symbol)
  },

  recordTrade: async (symbol, tradeData) => {
    const { userId } = get()
    if (!userId) return

    await watchlistService.recordTrade(userId, symbol, tradeData)
    set({
      trades: {
        ...get().trades,
        [symbol]: {
          ...tradeData,
          buyDate: tradeData.buyDate || new Date().toISOString(),
          type: tradeData.type || 'BUY',
        },
      },
    })
  },

  getTrade: (symbol) => {
    return get().trades[symbol] || null
  },

  removeTrade: async (symbol) => {
    const { userId } = get()
    if (!userId) return

    await watchlistService.removeTrade(userId, symbol)
    const trades = { ...get().trades }
    delete trades[symbol]
    set({ trades })
  },

  clearWatchlist: () => {
    set({ watchlist: [], trades: {}, initialized: false, userId: null })
  },
}))