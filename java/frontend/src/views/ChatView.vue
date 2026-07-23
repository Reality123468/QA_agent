<template>
  <div class="chat-layout">
    <AppHeader />
    <div class="chat-body">
      <MessageList :messages="chat.messages" />
      <div class="mode-bar">
        <el-radio-group v-model="mode" size="small" :disabled="chat.isStreaming">
          <el-radio-button value="agent">Agent 推理</el-radio-button>
          <el-radio-button value="rag">RAG 检索</el-radio-button>
          <el-radio-button value="search-only">仅搜索</el-radio-button>
        </el-radio-group>
      </div>
      <ChatInput
        :disabled="chat.isStreaming"
        @send="(text) => chat.sendMessage(text, mode)"
        @stop="chat.stopStreaming"
      />
    </div>
    <div class="status-bar">
      {{ chat.isStreaming ? '正在生成...' : '就绪' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppHeader from '@/components/common/AppHeader.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
const mode = ref<string>('rag')
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
.mode-bar {
  padding: 8px 24px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
}
.status-bar {
  padding: 4px 24px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
</style>
