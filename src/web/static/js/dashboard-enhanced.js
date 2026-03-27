/**
 * 增强版监控大屏JavaScript
 * 
 * 包含更多可视化图表和交互功能
 */

class DashboardManager {
    constructor() {
        this.charts = {};
        this.data = {
            realtime: [],
            historical: [],
            alerts: [],
            devices: []
        };
        this.websocket = null;
        this.updateInterval = null;
        this.metrics = {
            temperature: { unit: '°C', min: 0, max: 100 },
            pressure: { unit: 'bar', min: 0, max: 20 },
            flow: { unit: 'm³/h', min: 0, max: 500 }
        };
    }

    init() {
        this.initCharts();
        this.initWebSocket();
        this.initEventListeners();
        this.startAutoUpdate();
        this.loadInitialData();
    }

    initCharts() {
        // 实时趋势图
        this.charts.realtime = echarts.init(document.getElementById('chart-realtime'));
        
        // 历史趋势图
        this.charts.historical = echarts.init(document.getElementById('chart-historical'));
        
        // 设备状态分布
        this.charts.deviceStatus = echarts.init(document.getElementById('chart-device-status'));
        
        // 告警统计
        this.charts.alertStats = echarts.init(document.getElementById('chart-alert-stats'));
        
        // 热力图
        this.charts.heatmap = echarts.init(document.getElementById('chart-heatmap'));
        
        // 仪表盘
        this.charts.gauge = echarts.init(document.getElementById('chart-gauge'));

        this.renderRealtimeChart();
        this.renderHistoricalChart();
        this.renderDeviceStatusChart();
        this.renderAlertStatsChart();
        this.renderHeatmapChart();
        this.renderGaugeChart();

        // 响应式
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => chart.resize());
        });
    }

    renderRealtimeChart() {
        const option = {
            backgroundColor: 'transparent',
            title: { text: '实时数据', left: 'center', textStyle: { color: '#fff', fontSize: 14 } },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#fff' }
            },
            legend: {
                data: ['温度', '压力', '流量'],
                bottom: 0,
                textStyle: { color: '#94a3b8' }
            },
            grid: { left: 50, right: 30, top: 50, bottom: 50 },
            xAxis: {
                type: 'time',
                splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.1)' } },
                axisLabel: { color: '#94a3b8' }
            },
            yAxis: {
                type: 'value',
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
                axisLabel: { color: '#94a3b8' }
            },
            series: [
                {
                    name: '温度',
                    type: 'line',
                    smooth: true,
                    data: [],
                    lineStyle: { color: '#ef4444', width: 2 },
                    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                        { offset: 0, color: 'rgba(239, 68, 68, 0.3)' },
                        { offset: 1, color: 'rgba(239, 68, 68, 0.0)' }
                    ]}}
                },
                {
                    name: '压力',
                    type: 'line',
                    smooth: true,
                    data: [],
                    lineStyle: { color: '#3b82f6', width: 2 },
                    yAxisIndex: 0
                },
                {
                    name: '流量',
                    type: 'line',
                    smooth: true,
                    data: [],
                    lineStyle: { color: '#10b981', width: 2 },
                    yAxisIndex: 0
                }
            ]
        };
        this.charts.realtime.setOption(option);
    }

    renderHistoricalChart() {
        const option = {
            backgroundColor: 'transparent',
            title: { text: '历史趋势 (7天)', left: 'center', textStyle: { color: '#fff', fontSize: 14 } },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                textStyle: { color: '#fff' }
            },
            legend: {
                data: ['平均值', '最大值', '最小值'],
                bottom: 0,
                textStyle: { color: '#94a3b8' }
            },
            grid: { left: 50, right: 30, top: 50, bottom: 50 },
            xAxis: {
                type: 'category',
                data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                axisLabel: { color: '#94a3b8' }
            },
            yAxis: {
                type: 'value',
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
                axisLabel: { color: '#94a3b8' }
            },
            series: [
                {
                    name: '平均值',
                    type: 'line',
                    data: [32, 35, 38, 36, 34, 33, 31],
                    smooth: true,
                    lineStyle: { color: '#3b82f6', width: 2 }
                },
                {
                    name: '最大值',
                    type: 'line',
                    data: [45, 48, 52, 50, 47, 46, 44],
                    smooth: true,
                    lineStyle: { color: '#ef4444', width: 2 }
                },
                {
                    name: '最小值',
                    type: 'line',
                    data: [22, 24, 26, 25, 23, 22, 21],
                    smooth: true,
                    lineStyle: { color: '#10b981', width: 2 }
                }
            ]
        };
        this.charts.historical.setOption(option);
    }

    renderDeviceStatusChart() {
        const option = {
            backgroundColor: 'transparent',
            title: { text: '设备状态', left: 'center', textStyle: { color: '#fff', fontSize: 14 } },
            tooltip: { trigger: 'item', backgroundColor: 'rgba(15, 23, 42, 0.9)', textStyle: { color: '#fff' } },
            legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { color: '#94a3b8' } },
            series: [{
                name: '设备状态',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#1e293b',
                    borderWidth: 2
                },
                label: { show: false },
                emphasis: {
                    label: { show: true, fontSize: 16, fontWeight: 'bold', color: '#fff' }
                },
                data: [
                    { value: 12, name: '在线', itemStyle: { color: '#10b981' } },
                    { value: 3, name: '离线', itemStyle: { color: '#64748b' } },
                    { value: 2, name: '告警', itemStyle: { color: '#f59e0b' } },
                    { value: 1, name: '故障', itemStyle: { color: '#ef4444' } }
                ]
            }]
        };
        this.charts.deviceStatus.setOption(option);
    }

    renderAlertStatsChart() {
        const option = {
            backgroundColor: 'transparent',
            title: { text: '告警统计', left: 'center', textStyle: { color: '#fff', fontSize: 14 } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: 'rgba(15, 23, 42, 0.9)', textStyle: { color: '#fff' } },
            grid: { left: 50, right: 20, top: 50, bottom: 30 },
            xAxis: {
                type: 'category',
                data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                axisLabel: { color: '#94a3b8' }
            },
            yAxis: {
                type: 'value',
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
                axisLabel: { color: '#94a3b8' }
            },
            series: [{
                name: '告警数',
                type: 'bar',
                barWidth: '60%',
                data: [2, 1, 5, 3, 4, 2],
                itemStyle: {
                    color: {
                        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: '#f59e0b' },
                            { offset: 1, color: '#ef4444' }
                        ]
                    },
                    borderRadius: [4, 4, 0, 0]
                }
            }]
        };
        this.charts.alertStats.setOption(option);
    }

    renderHeatmapChart() {
        // 生成热力图数据
        const hours = ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
                       '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'];
        const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        
        const data = [];
        for (let i = 0; i < 7; i++) {
            for (let j = 0; j < 24; j++) {
                data.push([j, i, Math.floor(Math.random() * 10)]);
            }
        }

        const option = {
            backgroundColor: 'transparent',
            title: { text: '活跃度热力图', left: 'center', textStyle: { color: '#fff', fontSize: 14 } },
            tooltip: { position: 'top', backgroundColor: 'rgba(15, 23, 42, 0.9)', textStyle: { color: '#fff' } },
            grid: { height: '70%', top: '15%' },
            xAxis: {
                type: 'category',
                data: hours,
                splitArea: { show: true },
                axisLabel: { color: '#94a3b8', fontSize: 10 }
            },
            yAxis: {
                type: 'category',
                data: days,
                splitArea: { show: true },
                axisLabel: { color: '#94a3b8' }
            },
            visualMap: {
                min: 0,
                max: 10,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: '0%',
                inRange: {
                    color: ['#1e293b', '#3b82f6', '#f59e0b', '#ef4444']
                },
                textStyle: { color: '#94a3b8' }
            },
            series: [{
                name: '告警数',
                type: 'heatmap',
                data: data,
                label: { show: false },
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
                }
            }]
        };
        this.charts.heatmap.setOption(option);
    }

    renderGaugeChart() {
        const option = {
            backgroundColor: 'transparent',
            series: [
                {
                    type: 'gauge',
                    center: ['25%', '55%'],
                    radius: '70%',
                    startAngle: 90,
                    endAngle: -270,
                    pointer: { show: false },
                    progress: {
                        show: true,
                        overlap: false,
                        roundCap: true,
                        clip: false,
                        itemStyle: { borderWidth: 1, borderColor: '#464646' }
                    },
                    axisLine: { lineStyle: { width: 8 } },
                    splitLine: { show: false },
                    axisTick: { show: false },
                    axisLabel: { show: false },
                    data: [{
                        value: 85,
                        name: 'CPU',
                        title: { offsetCenter: ['0%', '-20%'], color: '#94a3b8' },
                        detail: { offsetCenter: ['0%', '10%'], valueAnimation: true, formatter: '{value}%', color: '#fff', fontSize: 20 }
                    }],
                    detail: { width: 40, height: 14, fontSize: 14, color: 'auto' },
                    itemStyle: { color: '#3b82f6' }
                },
                {
                    type: 'gauge',
                    center: ['75%', '55%'],
                    radius: '70%',
                    startAngle: 90,
                    endAngle: -270,
                    pointer: { show: false },
                    progress: {
                        show: true,
                        overlap: false,
                        roundCap: true,
                        clip: false,
                        itemStyle: { borderWidth: 1, borderColor: '#464646' }
                    },
                    axisLine: { lineStyle: { width: 8 } },
                    splitLine: { show: false },
                    axisTick: { show: false },
                    axisLabel: { show: false },
                    data: [{
                        value: 62,
                        name: '内存',
                        title: { offsetCenter: ['0%', '-20%'], color: '#94a3b8' },
                        detail: { offsetCenter: ['0%', '10%'], valueAnimation: true, formatter: '{value}%', color: '#fff', fontSize: 20 }
                    }],
                    detail: { width: 40, height: 14, fontSize: 14, color: 'auto' },
                    itemStyle: { color: '#10b981' }
                }
            ]
        };
        this.charts.gauge.setOption(option);
    }

    initWebSocket() {
        // 实际项目中连接WebSocket
        // this.websocket = new WebSocket('ws://localhost:8000/ws/realtime');
        // this.websocket.onmessage = (event) => this.handleWebSocketMessage(event);
    }

    initEventListeners() {
        // 设备筛选
        document.getElementById('device-filter')?.addEventListener('change', (e) => {
            this.filterByDevice(e.target.value);
        });

        // 时间范围选择
        document.getElementById('time-range')?.addEventListener('change', (e) => {
            this.changeTimeRange(e.target.value);
        });

        // 刷新按钮
        document.getElementById('btn-refresh')?.addEventListener('click', () => {
            this.refreshAll();
        });

        // 全屏切换
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
            this.toggleFullscreen();
        });

        // 告警处理
        document.querySelectorAll('.alert-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleAlertAction(e.target.dataset.action, e.target.dataset.id);
            });
        });
    }

    startAutoUpdate() {
        // 每5秒更新一次数据
        this.updateInterval = setInterval(() => {
            this.updateRealtimeData();
            this.updateMetrics();
        }, 5000);
    }

    loadInitialData() {
        this.updateMetrics();
        this.updateDeviceList();
        this.updateAlertList();
    }

    updateRealtimeData() {
        // 模拟实时数据更新
        const now = new Date();
        const temperature = 30 + Math.random() * 10;
        const pressure = 5 + Math.random() * 3;
        const flow = 200 + Math.random() * 100;

        // 更新图表数据
        const option = this.charts.realtime.getOption();
        
        // 添加新数据点
        ['温度', '压力', '流量'].forEach((name, index) => {
            const series = option.series[index];
            if (series.data.length > 100) {
                series.data.shift();
            }
            const value = index === 0 ? temperature : index === 1 ? pressure : flow;
            series.data.push([now.toISOString(), value.toFixed(2)]);
        });

        this.charts.realtime.setOption(option);
    }

    updateMetrics() {
        // 更新关键指标
        const metrics = {
            online_rate: (95 + Math.random() * 5).toFixed(1),
            today_alerts: Math.floor(Math.random() * 20),
            data_points: (1.2 + Math.random() * 0.1).toFixed(1),
            anomalies: Math.floor(Math.random() * 5)
        };

        Object.entries(metrics).forEach(([key, value]) => {
            const el = document.getElementById(`metric-${key}`);
            if (el) {
                el.textContent = value + (key === 'online_rate' ? '%' : key === 'data_points' ? 'M' : '');
            }
        });
    }

    updateDeviceList() {
        // 更新设备列表
        const devices = [
            { id: 'DEV001', name: 'PLC-001', status: 'online', lastSeen: '刚刚' },
            { id: 'DEV002', name: 'PLC-002', status: 'online', lastSeen: '1分钟前' },
            { id: 'DEV003', name: 'PLC-003', status: 'warning', lastSeen: '5分钟前' }
        ];

        const container = document.getElementById('device-list');
        if (container) {
            container.innerHTML = devices.map(d => `
                <div class="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                    <div class="flex items-center space-x-3">
                        <div class="w-2 h-2 rounded-full ${this.getStatusColor(d.status)}"></div>
                        <span class="font-medium">${d.name}</span>
                    </div>
                    <span class="text-xs text-slate-400">${d.lastSeen}</span>
                </div>
            `).join('');
        }
    }

    updateAlertList() {
        // 更新告警列表
        const alerts = [
            { id: 1, level: 'critical', message: '温度过高', time: '2分钟前' },
            { id: 2, level: 'warning', message: '压力异常', time: '5分钟前' }
        ];

        const container = document.getElementById('alert-list');
        if (container) {
            container.innerHTML = alerts.map(a => `
                <div class="alert-item ${this.getAlertClass(a.level)} border rounded-lg p-3">
                    <div class="flex items-start space-x-3">
                        <i class="fas ${this.getAlertIcon(a.level)} mt-1"></i>
                        <div class="flex-1">
                            <p class="font-medium text-sm">${a.message}</p>
                            <p class="text-xs opacity-70 mt-1">${a.time}</p>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }

    getStatusColor(status) {
        const colors = { online: 'bg-green-500', offline: 'bg-gray-500', warning: 'bg-yellow-500', error: 'bg-red-500' };
        return colors[status] || 'bg-gray-500';
    }

    getAlertClass(level) {
        const classes = {
            critical: 'bg-red-500/20 border-red-500 text-red-400',
            warning: 'bg-yellow-500/20 border-yellow-500 text-yellow-400',
            info: 'bg-blue-500/20 border-blue-500 text-blue-400'
        };
        return classes[level] || classes.info;
    }

    getAlertIcon(level) {
        const icons = {
            critical: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[level] || icons.info;
    }

    filterByDevice(deviceId) {
        console.log('筛选设备:', deviceId);
        this.refreshAll();
    }

    changeTimeRange(range) {
        console.log('切换时间范围:', range);
        // 重新加载历史数据
        this.renderHistoricalChart();
    }

    refreshAll() {
        this.loadInitialData();
        this.updateRealtimeData();
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    handleAlertAction(action, alertId) {
        console.log('处理告警:', action, alertId);
        // 调用API处理告警
    }

    destroy() {
        // 清理资源
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.websocket) {
            this.websocket.close();
        }
        Object.values(this.charts).forEach(chart => chart.dispose());
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();
    window.dashboard.init();
});
