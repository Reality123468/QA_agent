// SSE utility — kept separate so it can be reused if needed later.
// Currently chat.ts uses the inline fetch+ReadableStream approach directly,
// since it needs to pass JWT token from localStorage.
export function parseSSELine(line: string): any | null {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith(':')) return null
  if (trimmed.startsWith('data: ')) {
    const data = trimmed.substring(6)
    if (data === '[DONE]') return { __done: true }
    try { return JSON.parse(data) } catch { return null }
  }
  return null
}
