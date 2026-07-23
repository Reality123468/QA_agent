import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentApi, DocumentItem } from '@/api/document'
import { ElMessage } from 'element-plus'

export interface IndexProgress {
  docId: number
  status: string
  message: string
}

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<DocumentItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const indexProgress = ref<Record<number, IndexProgress>>({})
  let ws: WebSocket | null = null

  async function fetchList(page: number = 1, size: number = 20) {
    loading.value = true
    try {
      const result = await documentApi.list(page, size)
      documents.value = result.content
      total.value = result.totalElements
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File, title: string, department: string, securityLevel: string) {
    await documentApi.upload(file, title, department, securityLevel)
    ElMessage.success('上传成功')
    await fetchList()
  }

  async function deleteDoc(id: number) {
    await documentApi.delete(id)
    ElMessage.success('已删除')
    await fetchList()
  }

  async function triggerIndex(id: number) {
    await documentApi.triggerIndex(id)
    ElMessage.success('索引任务已触发')
  }

  function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/index-progress`

    ws = new WebSocket(url)

    ws.onmessage = (event) => {
      try {
        const data: IndexProgress = JSON.parse(event.data)
        indexProgress.value[data.docId] = data
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          ElMessage.info(`文档 #${data.docId}: ${data.message}`)
          fetchList()
        }
      } catch {
        // skip unparseable messages
      }
    }

    ws.onclose = () => {
      ws = null
      // Reconnect after 3 seconds
      setTimeout(() => connectWebSocket(), 3000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnectWebSocket() {
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
  }

  return {
    documents, total, loading, indexProgress,
    fetchList, upload, deleteDoc, triggerIndex,
    connectWebSocket, disconnectWebSocket
  }
})
