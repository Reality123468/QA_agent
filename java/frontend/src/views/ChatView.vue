<template>
  <div class="chat-layout">
    <AppHeader />
    <div class="chat-body">
      <MessageList :messages="chat.messages" />
      <ChatInput
        :disabled="chat.isStreaming"
        @send="chat.sendMessage"
        @stop="chat.stopStreaming"
      />
    </div>
    <div class="status-bar">
      {{ chat.isStreaming ? '正在生成...' : '就绪' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
</script>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.status-bar {
  padding: 4px 24px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
</style>
