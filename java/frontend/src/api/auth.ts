import api from './index'

export interface LoginResponse {
  token: string
  username: string
  role: string
  department: string
}

export interface RegisterParams {
  username: string
  password: string
  email: string
  department: string
}

export const authApi = {
  login(username: string, password: string) {
    return api.post('/api/auth/login', { username, password })
      .then(res => res.data.data as LoginResponse)
  },
  register(params: RegisterParams) {
    return api.post('/api/auth/register', params)
      .then(res => res.data)
  }
}
