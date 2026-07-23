<template>
  <div class="conversation-list">
    <div class="conv-header">
      <el-button type="primary" size="small" :icon="Plus" @click="chat.newConversation()">
        新对话
      </el-button>
    </div>
    <div class="conv-items" v-loading="chat.conversationsLoading">
      <div
        v-for="conv in chat.conversations"
        :key="conv.id"
        class="conv-item"
        :class="{ active: conv.id === chat.currentConversationId }"
        @click="chat.switchConversation(conv.id)"
      >
        <div class="conv-title">{{ conv.title }}</div>
        <div class="conv-meta">
          <span>{{ conv.messageCount }} 条消息</span>
          <el-button
            type="danger"
            size="small"
            :icon="Delete"
            text
            circle
            @click.stop="handleDelete(conv.id)"
          />
        </div>
      </div>
      <el-empty v-if="!chat.conversationsLoading && chat.conversations.length === 0"
        description="暂无历史会话" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Delete } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { ElMessageBox } from 'element-plus'

const chat = useChatStore()

async function handleDelete(conversationId: number) {
  try {
    await ElMessageBox.confirm('确定要删除该会话吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await chat.removeConversation(conversationId)
  } catch {
    // user cancelled
  }
}
</script>

<style scoped>
.conversation-list {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e4e7ed;
  background: #fafafa;
}
.conv-header {
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
}
.conv-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.conv-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.conv-item:hover {
  background: #ebeef5;
}
.conv-item.active {
  background: #d9ecff;
}
.conv-title {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}
.conv-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}
</style>
