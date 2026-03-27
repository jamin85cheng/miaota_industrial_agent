/**
 * 监控大屏页面
 * 
 * 作者: Frontend Team
 * 职责: 实时数据展示、设备状态、告警列表
 */

import React, { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Badge, Table, Tag } from 'antd'
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  DashboardOutlined,
  BellOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import './style.css'

// 设备状态卡片
const DeviceCard: React.FC<{ device: any }> = ({ device }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
      case 'warning':
        return <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 24 }} />
      case 'offline':
        return <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 24 }} />
      default:
        return null
    }
  }

  return (
    <Card className="device-card" size="small">
      <div className="device-card-content">
        {getStatusIcon(device.status)}
        <div className="device-info">
          <div className="device-name">{device.name}</div>
          <div className="device-tags">{device.tagCount} 个点位</div>
        </div>
      </div>
    </Card>
  )
}

// 实时趋势图
const TrendChart: React.FC = () => {
  const option = {
    title: { text: '实时趋势', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '溶解氧',
        type: 'line',
        smooth: true,
        data: [3.2, 3.8, 4.1, 3.9, 4.2, 3.7, 3.5],
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24,144,255,0.3)' },
              { offset: 1, color: 'rgba(24,144,255,0.05)' },
            ],
          },
        },
      },
      {
        name: 'pH值',
        type: 'line',
        smooth: true,
        data: [7.2, 7.1, 7.3, 7.2, 7.4, 7.1, 7.2],
        itemStyle: { color: '#52c41a' },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 300 }} />
}

// 告警表格
const AlertTable: React.FC = () => {
  const columns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
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
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 150,
    },
  ]

  const data = [
    {
      key: '1',
      severity: 'critical',
      name: '缺氧异常',
      message: '溶解氧浓度低于 2.0 mg/L',
      time: '2024-01-15 14:32:10',
    },
    {
      key: '2',
      severity: 'warning',
      name: 'pH异常',
      message: 'pH值偏离正常范围',
      time: '2024-01-15 14:28:05',
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={data}
      size="small"
      pagination={false}
      scroll={{ y: 200 }}
    />
  )
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    devices: { total: 15, online: 14, offline: 1 },
    tags: 128,
    alerts: 3,
    dataPoints: 1105920,
  })

  const devices = [
    { id: '1', name: '1#曝气池', status: 'online', tagCount: 8 },
    { id: '2', name: '2#曝气池', status: 'online', tagCount: 8 },
    { id: '3', name: '3#曝气池', status: 'online', tagCount: 8 },
    { id: '4', name: '1#提升泵', status: 'warning', tagCount: 4 },
    { id: '5', name: '2#提升泵', status: 'online', tagCount: 4 },
    { id: '6', name: '鼓风机', status: 'offline', tagCount: 6 },
  ]

  return (
    <div className="dashboard-page">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="设备总数"
              value={stats.devices.total}
              prefix={<DashboardOutlined />}
              suffix={
                <span style={{ fontSize: 14, color: '#52c41a' }}>
                  ({stats.devices.online} 在线)
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="监控点位"
              value={stats.tags}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活动告警"
              value={stats.alerts}
              prefix={<BellOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="24小时数据量"
              value={stats.dataPoints}
              suffix="条"
            />
          </Card>
        </Col>
      </Row>

      {/* 设备状态 + 趋势图 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="设备状态" className="dashboard-card">
            <div className="device-grid">
              {devices.map((device) => (
                <DeviceCard key={device.id} device={device} />
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="实时趋势" className="dashboard-card">
            <TrendChart />
          </Card>
        </Col>
      </Row>

      {/* 最近告警 */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card title="最近告警" className="dashboard-card">
            <AlertTable />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
