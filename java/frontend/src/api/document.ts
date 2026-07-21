import api from './index'

export interface DocumentItem {
  id: number
  title: string
  fileName: string
  filePath: string
  fileSize: number
  fileType: string
  department: string
  securityLevel: string
  status: string
  uploadByName: string
  createdAt: string
}

export interface PageResult<T> {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

export const documentApi = {
  list(page: number = 1, size: number = 20) {
    return api.get('/api/documents', { params: { page, size } })
      .then(res => res.data.data as PageResult<DocumentItem>)
  },
  getById(id: number) {
    return api.get(`/api/documents/${id}`)
      .then(res => res.data.data as DocumentItem)
  },
  upload(file: File, title: string, department: string, securityLevel: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('title', title)
    form.append('department', department)
    form.append('securityLevel', securityLevel)
    return api.post('/api/documents/upload', form)
      .then(res => res.data.data as DocumentItem)
  },
  delete(id: number) {
    return api.delete(`/api/documents/${id}`).then(res => res.data)
  },
  triggerIndex(id: number) {
    return api.post(`/api/documents/${id}/index`).then(res => res.data)
  },
  getStatus(id: number) {
    return api.get(`/api/documents/status/${id}`).then(res => res.data.data as string)
  }
}
