<template>
  <div class="documents-layout">
    <AppHeader />
    <div class="documents-body">
      <div class="toolbar">
        <h3>文档管理</h3>
        <el-button type="primary" @click="uploadVisible = true">
          <el-icon><Plus /></el-icon>
          上传文档
        </el-button>
      </div>

      <!-- Index progress alerts -->
      <div v-for="(p, docId) in store.indexProgress" :key="docId" class="progress-item">
        <el-alert
          :title="`文档 #${docId}`"
          :description="p.message"
          :type="p.status === 'COMPLETED' ? 'success' : p.status === 'FAILED' ? 'error' : 'info'"
          :closable="p.status === 'COMPLETED' || p.status === 'FAILED'"
          show-icon
          @close="delete store.indexProgress[docId]"
        />
      </div>

      <div class="table-wrap">
        <DocumentTable
          :documents="store.documents"
          :loading="store.loading"
          :indexProgress="store.indexProgress"
          @delete="handleDelete"
          @index="store.triggerIndex"
        />
      </div>
      <div class="pagination-wrap" v-if="store.total > 20">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="store.total"
          :page-size="20"
          @current-change="store.fetchList"
        />
      </div>
    </div>
    <UploadDialog v-model="uploadVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import AppHeader from '@/components/common/AppHeader.vue'
import DocumentTable from '@/components/document/DocumentTable.vue'
import UploadDialog from '@/components/document/UploadDialog.vue'
import { useDocumentStore } from '@/stores/document'

const store = useDocumentStore()
const uploadVisible = ref(false)

onMounted(() => {
  store.fetchList()
  store.connectWebSocket()
})

onUnmounted(() => {
  store.disconnectWebSocket()
})

async function handleDelete(id: number) {
  try {
    await store.deleteDoc(id)
  } catch { /* error already shown by store */ }
}
</script>

<style scoped>
.documents-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.documents-body {
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
.progress-item {
  margin-bottom: 8px;
}
.table-wrap {
  background: #fff;
  border-radius: 8px;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
