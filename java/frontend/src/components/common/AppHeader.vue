<template>
  <el-header class="app-header">
    <div class="header-left">
      <h2>企业智能问答系统</h2>
    </div>
    <div class="header-right">
      <el-menu
        mode="horizontal"
        :default-active="currentRoute"
        router
        :ellipsis="false"
      >
        <el-menu-item index="/chat">智能问答</el-menu-item>
        <el-menu-item index="/documents">文档管理</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/audit">审计日志</el-menu-item>
      </el-menu>
      <el-dropdown class="user-dropdown">
        <span class="user-info">
          <el-icon><UserFilled /></el-icon>
          {{ auth.userInfo?.username }}
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ auth.userInfo?.department }} · {{ auth.userInfo?.role }}
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentRoute = computed(() => route.path)

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}
.header-left h2 {
  font-size: 18px;
  color: #303133;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-right .el-menu {
  border-bottom: none;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
}
</style>
