import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentApi, DocumentItem } from '@/api/document'
import { ElMessage } from 'element-plus'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<DocumentItem[]>([])
  const total = ref(0)
  const loading = ref(false)

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
    await fetchList()
  }

  return { documents, total, loading, fetchList, upload, deleteDoc, triggerIndex }
})
