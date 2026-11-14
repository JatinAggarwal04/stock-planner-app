import { beforeEach, describe, expect, it, vi } from 'vitest'

// Minimal stand-in for the Supabase query builder: every call chains,
// and awaiting the chain (or calling .single()) resolves to the table's queued response.
const tables = {}
const writes = []

function queryFor(table) {
  const query = {
    select: () => query,
    eq: () => query,
    order: () => query,
    limit: () => query,
    single: () => Promise.resolve(tables[table].read),
    upsert: (rows) => {
      writes.push({ table, op: 'upsert', rows })
      return Promise.resolve({ error: tables[table].writeError ?? null })
    },
    insert: (rows) => {
      writes.push({ table, op: 'insert', rows })
      return Promise.resolve({ error: tables[table].writeError ?? null })
    },
    then: (resolve, reject) => Promise.resolve(tables[table].read).then(resolve, reject),
  }
  return query
}

vi.mock('./supabase', () => ({ supabase: { from: (table) => queryFor(table) } }))

const { watchlistService } = await import('./watchlistService')

const NO_ROW = { data: null, error: { code: 'PGRST116' } }
const trade = (type, quantity, price) => ({ type, quantity, price, date: '2026-01-01T00:00:00Z' })

beforeEach(() => {
  writes.length = 0
  tables.portfolio = { read: NO_ROW }
  tables.transactions = { read: { data: [], error: null } }
  tables.watchlists = { read: { data: [], error: null } }
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

const portfolioWrite = () => writes.find((w) => w.table === 'portfolio').rows[0]
const transactionWrite = () => writes.find((w) => w.table === 'transactions').rows[0]

describe('recordTrade', () => {
  it('opens a new position when there is no existing row', async () => {
    const result = await watchlistService.recordTrade('u1', 'TCS.NS', trade('BUY', 10, 100))
    expect(result.success).toBe(true)
    expect(portfolioWrite()).toMatchObject({ quantity: 10, average_price: 100 })
    expect(transactionWrite()).toMatchObject({ type: 'BUY', quantity: 10, price: 100, realized_pl: null })
  })

  it('averages the price when adding to a long position', async () => {
    tables.portfolio.read = { data: { quantity: 10, average_price: '100' }, error: null }
    await watchlistService.recordTrade('u1', 'TCS.NS', trade('BUY', 10, 200))
    expect(portfolioWrite()).toMatchObject({ quantity: 20, average_price: 150 })
  })

  it('realises profit when selling a long position', async () => {
    tables.portfolio.read = { data: { quantity: 10, average_price: '100' }, error: null }
    await watchlistService.recordTrade('u1', 'TCS.NS', trade('SELL', 4, 120))
    expect(portfolioWrite()).toMatchObject({ quantity: 6, average_price: 100 })
    expect(transactionWrite().realized_pl).toBe(80)
  })

  it('aborts without writing when the current position cannot be read', async () => {
    tables.portfolio.read = { data: null, error: { code: '500', message: 'server down' } }
    const result = await watchlistService.recordTrade('u1', 'TCS.NS', trade('BUY', 10, 100))
    expect(result.success).toBe(false)
    expect(writes).toHaveLength(0)
  })

  it.each([
    ['zero price', trade('BUY', 10, 0)],
    ['negative price', trade('BUY', 10, -5)],
    ['zero quantity', trade('BUY', 0, 100)],
  ])('rejects %s', async (_name, data) => {
    const result = await watchlistService.recordTrade('u1', 'TCS.NS', data)
    expect(result.success).toBe(false)
    expect(writes).toHaveLength(0)
  })

  it('reports failure when the portfolio write fails', async () => {
    tables.portfolio.writeError = { message: 'RLS denied' }
    const result = await watchlistService.recordTrade('u1', 'TCS.NS', trade('BUY', 10, 100))
    expect(result.success).toBe(false)
  })
})

describe('reads', () => {
  it('throws when the watchlist cannot be loaded', async () => {
    tables.watchlists.read = { data: null, error: { message: 'offline' } }
    await expect(watchlistService.getWatchlist('u1')).rejects.toBeTruthy()
  })

  it('returns only open positions', async () => {
    tables.portfolio.read = {
      data: [
        { symbol: 'A.NS', quantity: 5, average_price: '10', last_updated: 't' },
        { symbol: 'B.NS', quantity: 0, average_price: '10', last_updated: 't' },
        { symbol: 'C.NS', quantity: -2, average_price: '20', last_updated: 't' },
      ],
      error: null,
    }
    expect(Object.keys(await watchlistService.getTrades('u1'))).toEqual(['A.NS', 'C.NS'])
  })
})
