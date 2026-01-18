import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { watchlistService } from '../services/watchlistService'

export const useWatchlistStore = create(
  persist(
    (set, get) => ({
      watchlist: [],
      trades: {}, // Active Portfolio
      transactions: {}, // History per symbol
      initialized: false,
      userId: null,

      // Initialize from Supabase
      initialize: async (userId) => {
        if (!userId) return

        set({ userId })
        // Always fetch fresh data to ensure sync, but store serves as cache
        try {
          const watchlist = await watchlistService.getWatchlist(userId)
          const trades = await watchlistService.getTrades(userId)
          set({ watchlist, trades, initialized: true })
        } catch (error) {
          console.error('Failed to sync watchlist:', error)
          // On error, we still have the persisted data!
          set({ initialized: true })
        }
      },

      addToWatchlist: async (symbol) => {
        const { userId, watchlist } = get()
        if (!userId) return

        if (!watchlist.includes(symbol)) {
          // Optimistic update
          set({ watchlist: [...watchlist, symbol] })
          try {
            await watchlistService.addToWatchlist(userId, symbol)
          } catch (error) {
            // Revert on failure
            set({ watchlist: watchlist })
            console.error('Failed to add to watchlist:', error)
          }
        }
      },

      removeFromWatchlist: async (symbol) => {
        const { userId, watchlist } = get()
        if (!userId) return

        const oldWatchlist = watchlist
        // Optimistic update
        set({ watchlist: watchlist.filter((s) => s !== symbol) })

        try {
          await watchlistService.removeFromWatchlist(userId, symbol)
        } catch (error) {
          // Revert on failure
          set({ watchlist: oldWatchlist })
          console.error('Failed to remove from watchlist:', error)
        }
      },

      isInWatchlist: (symbol) => {
        return get().watchlist.includes(symbol)
      },

      recordTrade: async (symbol, tradeData) => {
        const { userId } = get()
        if (!userId) return

        const result = await watchlistService.recordTrade(userId, symbol, tradeData)

        if (result.success) {
          // Sync fresh data after trade
          const trades = await watchlistService.getTrades(userId)
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
    }),
    {
      name: 'tradewise-storage', // name of item in the storage (must be unique)
      storage: createJSONStorage(() => localStorage), // (optional) by default the 'localStorage' is used
      partialize: (state) => ({
        watchlist: state.watchlist,
        trades: state.trades,
        transactions: state.transactions,
        userId: state.userId
      }), // Only persist data, not initialization status
    }
  )
)