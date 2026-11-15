import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = {
  session: { access_token: 'token-123' },
  getSession: vi.fn(async () => ({ data: { session: auth.session } })),
  signOut: vi.fn(async () => ({ error: null })),
}
vi.mock('./supabase', () => ({ supabase: { auth } }))
vi.mock('react-hot-toast', () => ({ default: vi.fn() }))

const { geminiService } = await import('./geminiService')
const { authHeaders } = await import('./api')

beforeEach(() => {
  auth.session = { access_token: 'token-123' }
  auth.signOut.mockClear()
})
afterEach(() => vi.unstubAllGlobals())

const respond = (status, body = {}) =>
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status, ok: status < 400, json: async () => body }))

describe('authHeaders', () => {
  it('sends the Supabase access token', async () => {
    expect(await authHeaders()).toEqual({ Authorization: 'Bearer token-123' })
  })

  it('sends nothing when signed out', async () => {
    auth.session = null
    expect(await authHeaders()).toEqual({})
  })
})

describe('geminiService.sendMessage', () => {
  it('returns the agent response and sends the token', async () => {
    respond(200, { response: 'hello' })
    expect(await geminiService.sendMessage('hi')).toBe('hello')
    const [, request] = fetch.mock.calls[0]
    expect(JSON.parse(request.body)).toMatchObject({ message: 'hi' })
    expect(request.headers.Authorization).toBe('Bearer token-123')
  })

  it('signs out when the backend rejects the session', async () => {
    respond(401)
    expect(await geminiService.sendMessage('hi')).toMatch(/session has expired/)
    expect(auth.signOut).toHaveBeenCalledTimes(1)
  })

  it("sends an empty context in general mode instead of the string 'general'", async () => {
    respond(200, { response: 'ok' })
    geminiService.startChat('general')
    await geminiService.sendMessage('hi')
    expect(JSON.parse(fetch.mock.calls[0][1].body).context).toEqual({})
    geminiService.resetChat()
  })

  it('explains the rate limit', async () => {
    respond(429)
    expect(await geminiService.sendMessage('hi')).toMatch(/too quickly/)
  })

  it('falls back to a friendly message on errors', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    respond(500)
    expect(await geminiService.sendMessage('hi')).toMatch(/trouble connecting/)
  })
})
