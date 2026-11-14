import { afterEach, describe, expect, it, vi } from 'vitest'
import { geminiService } from './geminiService'

afterEach(() => vi.unstubAllGlobals())

const respond = (status, body = {}) =>
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status, ok: status < 400, json: async () => body }))

describe('geminiService.sendMessage', () => {
  it('returns the agent response', async () => {
    respond(200, { response: 'hello' })
    expect(await geminiService.sendMessage('hi')).toBe('hello')
    const [, request] = fetch.mock.calls[0]
    expect(JSON.parse(request.body)).toMatchObject({ message: 'hi' })
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
