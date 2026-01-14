//frontend/src/context/WatchlistContext.jsx
import { create } from 'zustand'
import { watchlistService } from '../services/watchlistService'
//.
export const useWatchlistStore = create((set, get) => ({
  watchlist: [],
  trades: {}, // Active Portfolio
  transactions: {}, // History per symbol
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
//,
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

    const result = await watchlistService.recordTrade(userId, symbol, tradeData)

    if (result.success) {
      // Optimistically update or re-fetch?
      // Let's re-fetch to be safe with the math logic
      const trades = await watchlistService.getTrades(userId)

      // Also update transactions for this symbol
      const history = await watchlistService.getTransactions(userId, symbol)

      set({
        trades,
        transactions: {
          ...get().transactions,
          [symbol]: history
        }
      })
    }
  },

  getTrade: (symbol) => {
    return get().trades[symbol] || null
  },

  fetchTransactions: async (symbol) => {
    const { userId } = get()
    if (!userId) return

    const history = await watchlistService.getTransactions(userId, symbol)
    set({
      transactions: {
        ...get().transactions,
        [symbol]: history
      }
    })
  },

  getHistory: (symbol) => {
    return get().transactions[symbol] || []
  },

  clearWatchlist: () => {
    set({ watchlist: [], trades: {}, transactions: {}, initialized: false, userId: null })
  },
}))