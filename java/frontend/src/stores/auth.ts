import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, LoginResponse } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<LoginResponse | null>(
    JSON.parse(localStorage.getItem('userInfo') || 'null')
  )

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'ROLE_ADMIN')
  const isHr = computed(() => userInfo.value?.role === 'ROLE_HR')
  const isLeader = computed(() => userInfo.value?.role === 'ROLE_LEADER')
  const isEmployee = computed(() => userInfo.value?.role === 'ROLE_EMPLOYEE')
  const canManageDocuments = computed(() => !isEmployee.value)

  async function login(username: string, password: string) {
    const data = await authApi.login(username, password)
    token.value = data.token
    userInfo.value = data
    localStorage.setItem('token', data.token)
    localStorage.setItem('userInfo', JSON.stringify(data))
  }

  async function register(username: string, password: string, email: string, department: string, position: string) {
    await authApi.register({ username, password, email, department, position })
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return { token, userInfo, isAuthenticated, isAdmin, isHr, isLeader, isEmployee, canManageDocuments, login, register, logout }
})
