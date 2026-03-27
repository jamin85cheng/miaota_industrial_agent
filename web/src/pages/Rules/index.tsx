/**
 * 规则管理页面
 */

import React, { useState } from 'react'
import { Card, Table, Button, Tag, Space, Modal, Form, Input, Select, Switch } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'

const Rules: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [form] = Form.useForm()

  const columns = [
    {
      title: '规则ID',
      dataIndex: 'rule_id',
      key: 'rule_id',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colors: any = {
          critical: 'red',
          warning: 'orange',
          info: 'blue',
        }
        return <Tag color={colors[severity]}>{severity}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Switch checked={enabled} size="small" />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="text" icon={<EditOutlined />} />
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Space>
      ),
    },
  ]

  const data = [
    {
      key: '1',
      rule_id: 'RULE_001',
      name: '缺氧异常',
      description: '溶解氧浓度低于 2.0 mg/L',
      severity: 'critical',
      enabled: true,
    },
    {
      key: '2',
      rule_id: 'RULE_002',
      name: 'pH异常',
      description: 'pH值偏离正常范围 6.5-8.5',
      severity: 'warning',
      enabled: true,
    },
  ]

  const handleAdd = () => {
    setIsModalVisible(true)
  }

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      console.log(values)
      setIsModalVisible(false)
      form.resetFields()
    })
  }

  return (
    <div>
      <Card
        title="规则管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建规则
          </Button>
        }
      >
        <Table columns={columns} dataSource={data} />
      </Card>

      <Modal
        title="新建规则"
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea />
          </Form.Item>
          <Form.Item
            name="severity"
            label="级别"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="critical">紧急</Select.Option>
              <Select.Option value="warning">警告</Select.Option>
              <Select.Option value="info">提示</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Rules
