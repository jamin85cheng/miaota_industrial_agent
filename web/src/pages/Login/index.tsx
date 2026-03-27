/**
 * 登录页面
 */

import React, { useState } from 'react'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuthStore } from '../../stores/auth'
import './style.css'

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true)
    
    try {
      // TODO: 调用真实登录 API
      // const response = await api.post('/auth/login', values)
      
      // 模拟登录
      await new Promise((resolve) => setTimeout(resolve, 1000))
      
      if (values.username === 'admin' && values.password === 'admin123') {
        login('mock_token', {
          user_id: 'user_001',
          username: values.username,
          email: 'admin@miaota.ai',
          role: 'admin',
        })
        message.success('登录成功')
      } else {
        message.error('用户名或密码错误')
      }
    } catch (error) {
      message.error('登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <Card className="login-card">
          <div className="login-header">
            <div className="login-logo">🦞</div>
            <h1 className="login-title">Miaota Industrial Agent</h1>
            <p className="login-subtitle">工业智能监控与诊断系统</p>
          </div>

          <Form
            name="login"
            onFinish={handleSubmit}
            autoComplete="off"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <div className="login-tips">
            <p>默认账号：admin / admin123</p>
            <p>操作员：operator / operator123</p>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default Login
