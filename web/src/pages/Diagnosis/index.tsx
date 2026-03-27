/**
 * 智能诊断页面
 */

import React, { useState } from 'react'
import { Card, Input, Button, List, Avatar, Tag, Typography, Space } from 'antd'
import {
  RobotOutlined,
  UserOutlined,
  MedicineBoxOutlined,
  FileTextOutlined,
} from '@ant-design/icons'

const { Text, Paragraph } = Typography
const { TextArea } = Input

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const Diagnosis: React.FC = () => {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: '您好！我是工业智能诊断助手。请描述您遇到的故障现象，我将为您分析可能的原因并提供解决方案。',
      timestamp: '2024-01-15 14:30:00',
    },
  ])
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // TODO: 调用诊断 API
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // 模拟回复
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `根据您的描述，我分析可能的原因如下：

**根本原因**: 曝气量不足导致溶解氧偏低

**可能原因**:
1. 曝气盘堵塞
2. 风机故障或效率下降
3. DO传感器漂移

**建议操作**:
1. 检查并清洗曝气盘
2. 检查风机运行状态，清洗滤网
3. 校准DO传感器

**备件需求**: 曝气盘、风机滤网

**置信度**: 85%`,
      timestamp: new Date().toLocaleString(),
    }
    setMessages((prev) => [...prev, assistantMessage])
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 200px)' }}>
      {/* 左侧对话区域 */}
      <Card
        title={
          <span>
            <RobotOutlined /> 智能诊断
          </span>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
      >
        {/* 消息列表 */}
        <List
          style={{ flex: 1, overflow: 'auto', padding: 16 }}
          dataSource={messages}
          renderItem={(msg) => (
            <List.Item
              style={{
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                padding: '8px 0',
              }}
            >
              <Space align="start">
                {msg.role === 'assistant' && (
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                )}
                <div
                  style={{
                    maxWidth: 500,
                    padding: 12,
                    borderRadius: 8,
                    backgroundColor: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                    color: msg.role === 'user' ? '#fff' : 'inherit',
                  }}
                >
                  <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 12, opacity: 0.7 }}>
                    {msg.timestamp}
                  </Text>
                </div>
                {msg.role === 'user' && (
                  <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#52c41a' }} />
                )}
              </Space>
            </List.Item>
          )}
        />

        {/* 输入区域 */}
        <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
          <Space style={{ width: '100%' }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="描述故障现象..."
              autoSize={{ minRows: 2, maxRows: 4 }}
              style={{ width: 400 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <Button
              type="primary"
              onClick={handleSend}
              loading={loading}
            >
              发送
            </Button>
          </Space>
        </div>
      </Card>

      {/* 右侧历史记录 */}
      <Card
        title={
          <span>
            <FileTextOutlined /> 诊断历史
          </span>
        }
        style={{ width: 300 }}
      >
        <List
          size="small"
          dataSource={[
            { id: '1', title: '溶解氧偏低诊断', date: '2024-01-15', status: '已解决' },
            { id: '2', title: 'pH异常分析', date: '2024-01-14', status: '处理中' },
          ]}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={item.title}
                description={
                  <Space>
                    <Text type="secondary">{item.date}</Text>
                    <Tag color={item.status === '已解决' ? 'success' : 'processing'}>
                      {item.status}
                    </Tag>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}

export default Diagnosis
