/**
 * 认证状态管理
 * 
 * 使用 Zustand 进行状态管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  user_id: string
  username: string
  email: string
  role: string
}

interface AuthState {
  // 状态
  isAuthenticated: boolean
  token: string | null
  user: User | null
  
  // 方法
  login: (token: string, user: User) => void
  logout: () => void
  updateUser: (user: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // 初始状态
      isAuthenticated: false,
      token: null,
      user: null,

      // 登录
      login: (token, user) => {
        set({
          isAuthenticated: true,
          token,
          user,
        })
      },

      // 登出
      logout: () => {
        set({
          isAuthenticated: false,
          token: null,
          user: null,
        })
      },

      // 更新用户信息
      updateUser: (userData) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }))
      },
    }),
    {
      name: 'auth-storage', // localStorage 键名
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        token: state.token,
        user: state.user,
      }),
    }
  )
)
