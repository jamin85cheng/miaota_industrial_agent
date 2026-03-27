/**
 * 主布局组件
 */

import React, { useState } from 'react'
import { Layout, Menu, theme, Badge, Avatar, Dropdown } from 'antd'
import {
  DashboardOutlined,
  AlertOutlined,
  RobotOutlined,
  FileTextOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'

const { Header, Sider } = Layout

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const {
    token: { colorBgContainer },
  } = theme.useToken()

  // 菜单项
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '监控大屏',
    },
    {
      key: '/alerts',
      icon: <AlertOutlined />,
      label: (
        <span>
          告警中心
          <Badge count={3} size="small" style={{ marginLeft: 8 }} />
        </span>
      ),
    },
    {
      key: '/diagnosis',
      icon: <RobotOutlined />,
      label: '智能诊断',
    },
    {
      key: '/rules',
      icon: <FileTextOutlined />,
      label: '规则管理',
    },
    {
      key: '/config',
      icon: <SettingOutlined />,
      label: '系统配置',
    },
  ]

  // 用户菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout()
    } else if (key === 'profile') {
      // TODO: 打开个人中心
    } else {
      navigate(key)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.1)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: collapsed ? 14 : 18,
              fontWeight: 'bold',
              color: '#1890ff',
            }}
          >
            {collapsed ? '🦞' : '🦞 Miaota IA'}
          </h1>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>

      <Layout>
        {/* 顶部栏 */}
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 500 }}>
            工业智能监控与诊断系统
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* 通知图标 */}
            <Badge count={5} size="small">
              <BellOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
            </Badge>

            {/* 用户下拉菜单 */}
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleMenuClick }}
              placement="bottomRight"
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{user?.username || '用户'}</span>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 内容区域 */}
        {children}
      </Layout>
    </Layout>
  )
}

export default MainLayout
