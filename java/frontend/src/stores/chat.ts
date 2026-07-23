import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createChatStream, SSEEvent, HistoryMessage, listConversations, getMessages, deleteConversation, ConversationDto } from '@/api/chat'

export interface AgentStep {
  type: 'thought' | 'action' | 'observation'
  content: string
  tool?: string
  args?: Record<string, any>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  agentSteps: AgentStep[]
  isStreaming: boolean
  timestamp: number
}

export interface Citation {
  title: string
  chunk: string
  heading?: string
  page?: number
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const conversations = ref<ConversationDto[]>([])
  const currentConversationId = ref<number | null>(null)
  const conversationsLoading = ref(false)
  let abortController: AbortController | null = null
  const historyMessages = ref<HistoryMessage[]>([])

  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substring(2)
  }

  async function loadConversations() {
    conversationsLoading.value = true
    try {
      conversations.value = await listConversations()
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      conversationsLoading.value = false
    }
  }

  async function switchConversation(conversationId: number) {
    if (isStreaming.value) return
    try {
      const msgs = await getMessages(conversationId)
      messages.value = msgs.map(m => ({
        id: String(m.id),
        role: m.role as 'user' | 'assistant',
        content: m.content,
        citations: m.citations || [],
        agentSteps: m.agentSteps || [],
        isStreaming: false,
        timestamp: new Date(m.timestamp).getTime()
      }))
      currentConversationId.value = conversationId

      // rebuild history for context
      historyMessages.value = msgs
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .slice(-20)
        .map(m => ({ role: m.role, content: m.content }))
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }

  async function removeConversation(conversationId: number) {
    try {
      await deleteConversation(conversationId)
      conversations.value = conversations.value.filter(c => c.id !== conversationId)
      if (currentConversationId.value === conversationId) {
        newConversation()
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  function newConversation() {
    if (isStreaming.value) return
    messages.value = []
    currentConversationId.value = null
    historyMessages.value = []
  }

  function sendMessage(question: string, mode: string = 'rag') {
    if (isStreaming.value) return

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: question,
      citations: [],
      agentSteps: [],
      isStreaming: false,
      timestamp: Date.now()
    }
    messages.value.push(userMsg)

    const assistantMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      citations: [],
      agentSteps: [],
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
              if (!msg.content) msg.content = event.content
              break
            case 'thought':
              msg.agentSteps.push({
                type: 'thought',
                content: event.content
              })
              break
            case 'action':
              msg.agentSteps.push({
                type: 'action',
                content: event.content,
                tool: event.data?.tool,
                args: event.data?.args
              })
              break
            case 'observation':
              msg.agentSteps.push({
                type: 'observation',
                content: event.content
              })
              break
            case 'answer':
              if (msg.content.startsWith('思考中') || msg.content.startsWith('正在')) msg.content = ''
              msg.content += event.content || ''
              break
            case 'citation':
              if (event.data) {
                const citationList = Array.isArray(event.data) ? event.data : [event.data]
                for (const item of citationList) {
                  msg.citations.push({
                    title: item.title || '',
                    chunk: item.chunk || item.content || event.content || '',
                    heading: item.heading,
                    page: item.page
                  })
                }
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
          // Reload conversation list to reflect new/updated conversation
          loadConversations()
        }
      },
      mode,
      currentConversationId.value
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

  return {
    messages, isStreaming, conversations, currentConversationId,
    conversationsLoading, sendMessage, stopStreaming, clearHistory,
    loadConversations, switchConversation, removeConversation, newConversation
  }
})
