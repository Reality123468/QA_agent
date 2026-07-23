<template>
  <div class="agent-thinking" v-if="steps.length > 0">
    <div class="agent-header" @click="expanded = !expanded">
      <el-icon><Cpu /></el-icon>
      <span>Agent 推理过程 ({{ steps.length }} 步)</span>
      <el-icon class="expand-icon" :class="{ expanded }"><ArrowRight /></el-icon>
    </div>
    <div class="agent-steps" v-show="expanded">
      <div
        v-for="(step, idx) in steps"
        :key="idx"
        class="agent-step"
        :class="step.type"
      >
        <div class="step-badge">
          <el-icon v-if="step.type === 'thought'"><Loading /></el-icon>
          <el-icon v-else-if="step.type === 'action'"><Search /></el-icon>
          <el-icon v-else><Document /></el-icon>
        </div>
        <div class="step-body">
          <span class="step-label">{{ stepLabel(step) }}</span>
          <span class="step-content">{{ step.content }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Cpu, ArrowRight, Loading, Search, Document } from '@element-plus/icons-vue'
import type { AgentStep } from '@/stores/chat'

defineProps<{
  steps: AgentStep[]
}>()

const expanded = ref(true)

function stepLabel(step: AgentStep): string {
  switch (step.type) {
    case 'thought': return '思考: '
    case 'action': return step.tool ? `调用 ${step.tool}: ` : '执行: '
    case 'observation': return '结果: '
    default: return ''
  }
}
</script>

<style scoped>
.agent-thinking {
  margin: 8px 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}
.agent-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f5f7fa;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  user-select: none;
}
.agent-header:hover {
  background: #ebeef5;
}
.expand-icon {
  margin-left: auto;
  transition: transform 0.2s;
}
.expand-icon.expanded {
  transform: rotate(90deg);
}
.agent-steps {
  padding: 8px 12px;
}
.agent-step {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #f5f7fa;
}
.agent-step:last-child {
  border-bottom: none;
}
.step-badge {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
}
.step-badge .el-icon {
  font-size: 14px;
}
.agent-step.thought .step-badge {
  background: #e6a23c;
}
.agent-step.action .step-badge {
  background: #409eff;
}
.agent-step.observation .step-badge {
  background: #67c23a;
}
.step-body {
  flex: 1;
  line-height: 1.5;
}
.step-label {
  font-weight: 600;
  color: #606266;
}
.step-content {
  color: #909399;
}
</style>
