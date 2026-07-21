<template>
  <div class="chat-input-area">
    <el-input
      v-model="inputText"
      type="textarea"
      :rows="3"
      placeholder="输入您的问题，按 Enter 发送，Shift+Enter 换行"
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
    />
    <el-button
      type="primary"
      :disabled="!inputText.trim() || disabled"
      :loading="disabled"
      @click="handleSend"
    >
      发送
    </el-button>
    <el-button
      v-if="disabled"
      type="warning"
      @click="$emit('stop')"
    >
      停止
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{
  send: [text: string]
  stop: []
}>()

const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
