export interface HistoryMessage {
  role: string  // 'user' | 'assistant'
  content: string
}

export interface ConversationDto {
  id: number
  title: string
  updatedAt: string
  messageCount: number
}

export interface MessageDto {
  id: number
  role: string
  content: string
  citations: any[]
  agentSteps: any[]
  feedback?: string
  timestamp: string
}

export async function listConversations(): Promise<ConversationDto[]> {
  const token = localStorage.getItem('token')
  const res = await fetch('/api/chat/conversations', {
    headers: { 'Authorization': token ? `Bearer ${token}` : '' }
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '加载会话列表失败')
  return json.data
}

export async function getMessages(conversationId: number): Promise<MessageDto[]> {
  const token = localStorage.getItem('token')
  const res = await fetch(`/api/chat/conversations/${conversationId}`, {
    headers: { 'Authorization': token ? `Bearer ${token}` : '' }
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '加载消息失败')
  return json.data
}

export async function submitFeedback(messageId: number, feedback: string): Promise<void> {
  const token = localStorage.getItem('token')
  const res = await fetch(`/api/chat/conversations/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ feedback })
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '提交反馈失败')
}

export async function deleteConversation(conversationId: number): Promise<void> {
  const token = localStorage.getItem('token')
  const res = await fetch(`/api/chat/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: { 'Authorization': token ? `Bearer ${token}` : '' }
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '删除会话失败')
}

export interface SSEEvent {
  type: 'thinking' | 'answer' | 'citation' | 'done' | 'error' | 'thought' | 'action' | 'observation'
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
  callbacks: SSECallbacks,
  mode: string = 'rag',
  conversationId?: number | null
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ question, history: history || [], mode, conversationId }),
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
        if (trimmed.startsWith('data:')) {
          let payload = trimmed.substring(5)
          if (payload.startsWith(' ')) payload = payload.substring(1)
          if (payload === '[DONE]') {
            callbacks.onDone()
            return
          }
          try {
            const parsed: SSEEvent = JSON.parse(payload)
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
