import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useWatchlistStore = create(
  persist(
    (set, get) => ({
      watchlist: [],
      trades: {},

      addToWatchlist: (symbol) => {
        const current = get().watchlist
        if (!current.includes(symbol)) {
          set({ watchlist: [...current, symbol] })
        }
      },

      removeFromWatchlist: (symbol) => {
        set({ watchlist: get().watchlist.filter((s) => s !== symbol) })
      },

      isInWatchlist: (symbol) => {
        return get().watchlist.includes(symbol)
      },

      recordTrade: (symbol, tradeData) => {
        set({
          trades: {
            ...get().trades,
            [symbol]: tradeData,
          },
        })
      },

      getTrade: (symbol) => {
        return get().trades[symbol] || null
      },

      removeTrade: (symbol) => {
        const trades = { ...get().trades }
        delete trades[symbol]
        set({ trades })
      },

      clearWatchlist: () => {
        set({ watchlist: [], trades: {} })
      },
    }),
    {
      name: 'tradewise-storage',
    }
  )
)