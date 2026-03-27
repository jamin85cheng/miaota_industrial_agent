/**
 * 系统配置页面
 */

import React from 'react'
import { Card, Form, Input, Button, Switch, Select, Tabs, message } from 'antd'
import { SaveOutlined } from '@ant-design/icons'

const { TabPane } = Tabs

const Config: React.FC = () => {
  const [form] = Form.useForm()

  const handleSave = () => {
    message.success('配置已保存')
  }

  return (
    <Card title="系统配置">
      <Tabs defaultActiveKey="1">
        <TabPane tab="基础配置" key="1">
          <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
            <Form.Item label="系统名称" name="system_name">
              <Input defaultValue="Miaota Industrial Agent" />
            </Form.Item>
            <Form.Item label="采集间隔(秒)" name="scan_interval">
              <Input type="number" defaultValue={10} />
            </Form.Item>
            <Form.Item label="告警抑制(分钟)" name="alert_suppression">
              <Input type="number" defaultValue={15} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                保存
              </Button>
            </Form.Item>
          </Form>
        </TabPane>

        <TabPane tab="PLC配置" key="2">
          <Form layout="vertical" style={{ maxWidth: 600 }}>
            <Form.Item label="PLC类型">
              <Select defaultValue="s7">
                <Select.Option value="s7">西门子 S7</Select.Option>
                <Select.Option value="modbus">Modbus TCP</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item label="IP地址">
              <Input defaultValue="192.168.1.100" />
            </Form.Item>
            <Form.Item label="端口">
              <Input type="number" defaultValue={102} />
            </Form.Item>
            <Form.Item>
              <Button type="primary">测试连接</Button>
            </Form.Item>
          </Form>
        </TabPane>

        <TabPane tab="通知配置" key="3">
          <Form layout="vertical" style={{ maxWidth: 600 }}>
            <Form.Item label="启用飞书通知">
              <Switch />
            </Form.Item>
            <Form.Item label="飞书Webhook">
              <Input.TextArea placeholder="输入飞书机器人Webhook地址" />
            </Form.Item>
            <Form.Item label="启用邮件通知">
              <Switch />
            </Form.Item>
            <Form.Item label="SMTP服务器">
              <Input placeholder="smtp.example.com" />
            </Form.Item>
          </Form>
        </TabPane>
      </Tabs>
    </Card>
  )
}

export default Config
