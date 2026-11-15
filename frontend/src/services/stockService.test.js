import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn()
vi.mock('./api', () => ({ default: { post: (...args) => post(...args) } }))

const { stockService } = await import('./stockService')

beforeEach(() => post.mockReset())

describe('reviewHoldings', () => {
  it('sends open positions, including shorts and entry dates', async () => {
    post.mockResolvedValue({ data: { summary: {}, positions: [] } })
    await stockService.reviewHoldings({
      'GROWW.NS': { quantity: 9, averagePrice: 219, lastUpdated: '2026-10-01T10:00:00Z' },
      'IDEA.NS': { quantity: -100, averagePrice: 13 },
      'OLD.NS': { quantity: 0, averagePrice: 50 },
    })
    expect(post).toHaveBeenCalledWith('/portfolio/review', {
      holdings: [
        { symbol: 'GROWW.NS', quantity: 9, average_price: 219, since: '2026-10-01T10:00:00Z' },
        { symbol: 'IDEA.NS', quantity: -100, average_price: 13, since: null },
      ],
    })
  })

  it('does not call the backend without positions', async () => {
    expect(await stockService.reviewHoldings({ 'OLD.NS': { quantity: 0, averagePrice: 50 } })).toBeNull()
    expect(post).not.toHaveBeenCalled()
  })
})
