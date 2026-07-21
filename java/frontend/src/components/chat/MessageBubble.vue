<template>
  <div class="message-row" :class="message.role">
    <div class="message-bubble" :class="message.role">
      <div class="message-content" v-html="renderedContent"></div>
      <div v-if="message.isStreaming" class="typing-cursor">|</div>
      <CitationCard
        v-for="(c, idx) in message.citations"
        :key="idx"
        :citation="c"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { ChatMessage } from '@/stores/chat'
import CitationCard from './CitationCard.vue'

const props = defineProps<{
  message: ChatMessage
}>()

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  if (props.message.role === 'user') return escapeHtml(props.message.content)
  try {
    return marked.parse(props.message.content) as string
  } catch {
    return escapeHtml(props.message.content)
  }
})

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.message-row {
  display: flex;
  margin-bottom: 16px;
}
.message-row.user {
  justify-content: flex-end;
}
.message-row.assistant {
  justify-content: flex-start;
}
.message-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
}
.message-bubble.user {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message-bubble.assistant {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}
.message-content :deep(pre) {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
.message-content :deep(code) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}
.message-content :deep(p) {
  margin: 4px 0;
}
.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.typing-cursor {
  display: inline;
  animation: blink 1s infinite;
  color: #409eff;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
