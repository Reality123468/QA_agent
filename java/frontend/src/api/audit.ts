import api from './index'
import type { PageResult } from './document'

export interface AuditLogItem {
  id: number
  userId: number
  question: string
  answer: string
  toolsCalled: string | null
  responseTime: number | null
  tokenUsage: string | null
  createdAt: string
}

export const auditApi = {
  list(page: number = 1, size: number = 20, userId?: number) {
    return api.get('/api/audit/logs', { params: { page, size, userId } })
      .then(res => res.data.data as PageResult<AuditLogItem>)
  },
  delete(id: number) {
    return api.delete(`/api/audit/logs/${id}`).then(res => res.data)
  },
  batchDelete(ids: number[]) {
    return api.delete('/api/audit/logs/batch', { data: ids }).then(res => res.data)
  }
}
