import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../services/watchlistService', () => ({
  watchlistService: {
    getWatchlist: vi.fn(),
    getTrades: vi.fn(),
    getTransactions: vi.fn(),
    recordTrade: vi.fn(),
    addToWatchlist: vi.fn(),
    removeFromWatchlist: vi.fn(),
  },
}))

const { watchlistService } = await import('../services/watchlistService')
const { useWatchlistStore } = await import('./WatchlistContext')

const store = () => useWatchlistStore.getState()

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(console, 'error').mockImplementation(() => {})
  store().clearWatchlist()
})

describe('initialize', () => {
  it('loads the user data', async () => {
    watchlistService.getWatchlist.mockResolvedValue(['TCS.NS'])
    watchlistService.getTrades.mockResolvedValue({ 'TCS.NS': { quantity: 1, averagePrice: 10 } })
    await store().initialize('u1')
    expect(store().watchlist).toEqual(['TCS.NS'])
    expect(store().initialized).toBe(true)
  })

  it("does not show a previous user's data to a new user", async () => {
    useWatchlistStore.setState({ userId: 'old', watchlist: ['OLD.NS'], trades: { 'OLD.NS': {} } })
    watchlistService.getWatchlist.mockRejectedValue(new Error('offline'))
    await store().initialize('new')
    expect(store().watchlist).toEqual([])
    expect(store().trades).toEqual({})
    expect(store().userId).toBe('new')
  })

  it('keeps cached data for the same user when the backend is down', async () => {
    useWatchlistStore.setState({ userId: 'u1', watchlist: ['TCS.NS'] })
    watchlistService.getWatchlist.mockRejectedValue(new Error('offline'))
    await store().initialize('u1')
    expect(store().watchlist).toEqual(['TCS.NS'])
  })
})

describe('recordTrade', () => {
  beforeEach(() => useWatchlistStore.setState({ userId: 'u1' }))

  it('throws when the trade was not saved', async () => {
    watchlistService.recordTrade.mockResolvedValue({ success: false, error: new Error('RLS denied') })
    await expect(store().recordTrade('TCS.NS', {})).rejects.toThrow('RLS denied')
  })

  it('refreshes the portfolio after a saved trade', async () => {
    watchlistService.recordTrade.mockResolvedValue({ success: true })
    watchlistService.getTrades.mockResolvedValue({ 'TCS.NS': { quantity: 5 } })
    watchlistService.getTransactions.mockResolvedValue([{ id: 1 }])
    await store().recordTrade('TCS.NS', {})
    expect(store().trades).toEqual({ 'TCS.NS': { quantity: 5 } })
    expect(store().transactions['TCS.NS']).toEqual([{ id: 1 }])
  })

  it('does not fail a saved trade when only the refresh fails', async () => {
    watchlistService.recordTrade.mockResolvedValue({ success: true })
    watchlistService.getTrades.mockRejectedValue(new Error('offline'))
    await expect(store().recordTrade('TCS.NS', {})).resolves.toBeUndefined()
  })
})
