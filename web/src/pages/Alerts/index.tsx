/**
 * 告警中心页面
 */

import React from 'react'
import { Card, Table, Tag, Button, Badge, Space } from 'antd'
import { CheckCircleOutlined, BellOutlined } from '@ant-design/icons'

const Alerts: React.FC = () => {
  const columns = [
    {
      title: '告警ID',
      dataIndex: 'alert_id',
      key: 'alert_id',
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
        const labels: any = {
          critical: '紧急',
          warning: '警告',
          info: '提示',
        }
        return <Tag color={colors[severity]}>{labels[severity]}</Tag>
      },
    },
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
    },
    {
      title: '状态',
      dataIndex: 'acknowledged',
      key: 'acknowledged',
      render: (ack: boolean) => (
        ack ? (
          <Tag color="success">已确认</Tag>
        ) : (
          <Badge status="processing" text="未确认" />
        )
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          {!record.acknowledged && (
            <Button type="primary" size="small" icon={<CheckCircleOutlined />}>
              确认
            </Button>
          )}
          <Button size="small">详情</Button>
        </Space>
      ),
    },
  ]

  const data = [
    {
      key: '1',
      alert_id: 'ALERT_001',
      severity: 'critical',
      rule_name: '缺氧异常',
      description: '溶解氧浓度低于 2.0 mg/L',
      timestamp: '2024-01-15 14:32:10',
      acknowledged: false,
    },
    {
      key: '2',
      alert_id: 'ALERT_002',
      severity: 'warning',
      rule_name: 'pH异常',
      description: 'pH值偏离正常范围',
      timestamp: '2024-01-15 14:28:05',
      acknowledged: true,
    },
  ]

  return (
    <div>
      <Card
        title={
          <span>
            <BellOutlined /> 告警列表
          </span>
        }
        extra={
          <Space>
            <Button>全部确认</Button>
            <Button type="primary">导出报表</Button>
          </Space>
        }
      >
        <Table columns={columns} dataSource={data} />
      </Card>
    </div>
  )
}

export default Alerts
