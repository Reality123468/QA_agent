export interface HistoryMessage {
  role: string  // 'user' | 'assistant'
  content: string
}

export interface SSEEvent {
  type: 'thinking' | 'answer' | 'citation' | 'done' | 'error'
  content: string
  data: any
}

export interface SSECallbacks {
  onMessage: (event: SSEEvent) => void
  onError: (error: Error) => void
  onDone: () => void
}

export function createChatStream(
  question: string,
  history: HistoryMessage[],
  callbacks: SSECallbacks
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ question, history: history || [] }),
    signal: controller.signal
  }).then(async response => {
    if (!response.ok) {
      if (response.status === 401) {
        callbacks.onError(new Error('请先登录'))
        return
      }
      callbacks.onError(new Error(`HTTP ${response.status}`))
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError(new Error('无法读取响应流'))
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.substring(6)
          if (data === '[DONE]') {
            callbacks.onDone()
            return
          }
          try {
            const parsed: SSEEvent = JSON.parse(data)
            callbacks.onMessage(parsed)
          } catch {
            // skip unparseable lines
          }
        }
      }
    }
    callbacks.onDone()
  }).catch(err => {
    if (err.name !== 'AbortError') {
      callbacks.onError(err)
    }
  })

  return controller
}
