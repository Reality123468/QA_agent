<template>
  <div class="audit-layout">
    <AppHeader />
    <div class="audit-body">
      <h3>审计日志</h3>
      <el-table
        :data="logs"
        v-loading="loading"
        stripe
        @expand-change="handleExpand"
        class="audit-table"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="expand-section">
                <h4>问题</h4>
                <p>{{ row.question }}</p>
              </div>
              <div class="expand-section">
                <h4>回答</h4>
                <p>{{ row.answer || '(无)' }}</p>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="userId" label="用户ID" width="80" />
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column label="响应时间" width="100">
          <template #default="{ row }">
            {{ row.responseTime ? row.responseTime + 'ms' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="时间" width="170" />
      </el-table>
      <div class="pagination-wrap" v-if="total > 20">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="20"
          @current-change="fetchPage"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/common/AppHeader.vue'
import { auditApi, AuditLogItem } from '@/api/audit'

const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)

async function fetchPage(page: number = 1) {
  loading.value = true
  try {
    const result = await auditApi.list(page, 20)
    logs.value = result.content
    total.value = result.totalElements
  } finally {
    loading.value = false
  }
}

function handleExpand(_row: any, expandedRows: any[]) {
  // expand logic handled by el-table internally
}

onMounted(() => fetchPage())
</script>

<style scoped>
.audit-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.audit-body {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}
.audit-body h3 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 16px;
}
.audit-table {
  background: #fff;
  border-radius: 8px;
}
.expand-content {
  padding: 12px 40px;
}
.expand-section {
  margin-bottom: 12px;
}
.expand-section h4 {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}
.expand-section p {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
