import { beforeEach, describe, expect, it, vi } from 'vitest'

const signOut = vi.fn().mockResolvedValue({ error: null })
vi.mock('../services/supabase', () => ({ supabase: { auth: { signOut: (...args) => signOut(...args) } } }))
vi.mock('react-hot-toast', () => ({ default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }) }))

const { MAX_SESSION_MS, enforceSessionLimit, isSessionExpired } = await import('./AuthContext')

const HOUR = 60 * 60 * 1000
const userSignedIn = (msAgo) => ({ id: 'u1', last_sign_in_at: new Date(Date.now() - msAgo).toISOString() })

beforeEach(() => signOut.mockClear())

describe('12-hour session limit', () => {
  it('is 12 hours', () => {
    expect(MAX_SESSION_MS).toBe(12 * HOUR)
  })

  it.each([
    [1 * HOUR, false],
    [11.9 * HOUR, false],
    [12.1 * HOUR, true],
    [24 * HOUR, true],
  ])('signed in %d ms ago -> expired: %s', (msAgo, expired) => {
    expect(isSessionExpired(userSignedIn(msAgo))).toBe(expired)
  })

  it('treats a missing user or timestamp as not expired', () => {
    expect(isSessionExpired(null)).toBe(false)
    expect(isSessionExpired({ id: 'u1' })).toBe(false)
  })

  it('keeps a fresh session', async () => {
    const user = userSignedIn(2 * HOUR)
    expect(await enforceSessionLimit({ user })).toBe(user)
    expect(signOut).not.toHaveBeenCalled()
  })

  it("signs out a session from yesterday", async () => {
    expect(await enforceSessionLimit({ user: userSignedIn(20 * HOUR) })).toBeNull()
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('handles no session', async () => {
    expect(await enforceSessionLimit(null)).toBeNull()
    expect(signOut).not.toHaveBeenCalled()
  })
})
