<template>
  <div class="audit-layout">
    <AppHeader />
    <div class="audit-body">
      <div class="toolbar">
        <h3>审计日志</h3>
        <el-button
          v-if="selectedIds.length > 0"
          type="danger"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedIds.length }})
        </el-button>
      </div>

      <el-table
        ref="tableRef"
        :data="logs"
        v-loading="loading"
        stripe
        @expand-change="handleExpand"
        @selection-change="handleSelectionChange"
        class="audit-table"
      >
        <el-table-column type="selection" width="50" />
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
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              title="确定删除该日志？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button type="danger" size="small" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
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
import { ElMessage, ElMessageBox } from 'element-plus'

const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)
const selectedIds = ref<number[]>([])
const currentPage = ref(1)

async function fetchPage(page: number = 1) {
  currentPage.value = page
  loading.value = true
  try {
    const result = await auditApi.list(page, 20)
    logs.value = result.content
    total.value = result.totalElements
  } finally {
    loading.value = false
  }
}

function handleExpand(_row: any, _expandedRows: any[]) {}

function handleSelectionChange(rows: AuditLogItem[]) {
  selectedIds.value = rows.map(r => r.id)
}

async function handleDelete(id: number) {
  try {
    await auditApi.delete(id)
    ElMessage.success('删除成功')
    fetchPage(currentPage.value)
  } catch {
    // error already shown by interceptor
  }
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedIds.value.length} 条日志？此操作不可恢复。`,
      '批量删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await auditApi.batchDelete(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    fetchPage(currentPage.value)
  } catch {
    // user cancelled or error
  }
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
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar h3 {
  font-size: 18px;
  color: #303133;
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
