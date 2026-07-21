import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createChatStream, SSEEvent, HistoryMessage } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  isStreaming: boolean
  timestamp: number
}

export interface Citation {
  title: string
  chunk: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  let abortController: AbortController | null = null
  const historyMessages = ref<HistoryMessage[]>([])

  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substring(2)
  }

  function sendMessage(question: string) {
    if (isStreaming.value) return

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: question,
      citations: [],
      isStreaming: false,
      timestamp: Date.now()
    }
    messages.value.push(userMsg)

    const assistantMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
      timestamp: Date.now()
    }
    messages.value.push(assistantMsg)
    isStreaming.value = true

    abortController = createChatStream(
      question,
      historyMessages.value,
      {
        onMessage(event: SSEEvent) {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (!msg) return

          switch (event.type) {
            case 'thinking':
              msg.content = event.content
              break
            case 'answer':
              if (msg.content.startsWith('思考中')) msg.content = ''
              msg.content += event.content || ''
              break
            case 'citation':
              if (event.data) {
                msg.citations.push({
                  title: event.data.title || '',
                  chunk: event.data.chunk || event.content || ''
                })
              }
              break
            case 'error':
              msg.content = '回答出错: ' + (event.content || '未知错误')
              msg.isStreaming = false
              isStreaming.value = false
              break
            case 'done':
              msg.isStreaming = false
              isStreaming.value = false
              break
          }
        },
        onError(error: Error) {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (msg) {
            msg.content = '连接失败: ' + error.message
            msg.isStreaming = false
          }
          isStreaming.value = false
        },
        onDone() {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (msg) {
            msg.isStreaming = false
          }
          isStreaming.value = false
          historyMessages.value.push({ role: 'user', content: question })
          historyMessages.value.push({ role: 'assistant', content: msg?.content || '' })
          if (historyMessages.value.length > 20) {
            historyMessages.value = historyMessages.value.slice(-20)
          }
        }
      }
    )
  }

  function stopStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isStreaming.value = false
  }

  function clearHistory() {
    messages.value = []
    historyMessages.value = []
  }

  return { messages, isStreaming, sendMessage, stopStreaming, clearHistory }
})
