/**
 * Miaota Industrial Agent - 主应用组件
 * 
 * 作者: Frontend Team
 * 职责: 路由配置、全局布局
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout, theme } from 'antd'
import { useState } from 'react'

// 布局组件
import MainLayout from './components/Layout/MainLayout'

// 页面组件
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'
import Diagnosis from './pages/Diagnosis'
import Rules from './pages/Rules'
import Config from './pages/Config'

// 状态管理
import { useAuthStore } from './stores/auth'

const { Content } = Layout

function App() {
  const { isAuthenticated } = useAuthStore()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  // 未登录时显示登录页
  if (!isAuthenticated) {
    return <Login />
  }

  return (
    <BrowserRouter>
      <MainLayout>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/diagnosis" element={<Diagnosis />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/config" element={<Config />} />
          </Routes>
        </Content>
      </MainLayout>
    </BrowserRouter>
  )
}

export default App
