<template>
  <div class="citation-card">
    <div class="citation-header">
      <el-icon><Document /></el-icon>
      <span class="citation-title">{{ citation.title }}</span>
    </div>
    <div class="citation-chunk">{{ citation.chunk }}</div>
  </div>
</template>

<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
import type { Citation } from '@/stores/chat'

defineProps<{
  citation: Citation
}>()
</script>

<style scoped>
.citation-card {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  font-size: 13px;
}
.citation-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  margin-bottom: 4px;
}
.citation-title {
  font-weight: 600;
}
.citation-chunk {
  color: #606266;
  line-height: 1.5;
}
</style>
