<template>
  <el-table :data="documents" v-loading="loading" stripe>
    <el-table-column prop="id" label="ID" width="60" />
    <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
    <el-table-column prop="fileName" label="文件名" min-width="180" show-overflow-tooltip />
    <el-table-column prop="fileType" label="类型" width="70" />
    <el-table-column label="大小" width="90">
      <template #default="{ row }">
        {{ formatSize(row.fileSize) }}
      </template>
    </el-table-column>
    <el-table-column prop="department" label="部门" width="90" />
    <el-table-column label="安全级别" width="90">
      <template #default="{ row }">
        <el-tag
          :type="levelTag(row.securityLevel)"
          size="small"
        >
          {{ row.securityLevel }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="180">
      <template #default="{ row }">
        <div class="status-cell">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
          <span v-if="indexProgress[row.id] && indexProgress[row.id].status === 'INDEXING'" class="progress-msg">
            {{ indexProgress[row.id].message }}
          </span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="160" fixed="right">
      <template #default="{ row }">
        <el-button text type="primary" size="small" @click="$emit('index', row.id)">
          索引
        </el-button>
        <el-popconfirm
          title="确定删除此文档?"
          @confirm="$emit('delete', row.id)"
        >
          <template #reference>
            <el-button text type="danger" size="small">删除</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { DocumentItem } from '@/api/document'

import type { IndexProgress } from '@/stores/document'

defineProps<{
  documents: DocumentItem[]
  loading: boolean
  indexProgress: Record<number, IndexProgress>
}>()

defineEmits<{
  delete: [id: number]
  index: [id: number]
}>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

function levelTag(level: string): string {
  const map: Record<string, string> = { '公开': 'success', '内部': 'warning', '机密': 'danger' }
  return map[level] || 'info'
}

function statusTag(status: string): string {
  const map: Record<string, string> = { 'UPLOADED': 'info', 'INDEXING': 'warning', 'COMPLETED': 'success', 'FAILED': 'danger' }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = { 'UPLOADED': '已上传', 'INDEXING': '索引中', 'COMPLETED': '已完成', 'FAILED': '失败' }
  return map[status] || status
}
</script>

<style scoped>
.status-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.progress-msg {
  font-size: 11px;
  color: #909399;
}
</style>
