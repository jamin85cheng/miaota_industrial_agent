# Miaota Industrial Agent - 部署指南

> **版本**: v1.0.0-beta1  
> **更新日期**: 2026-03-26

---

## 目录

1. [部署要求](#1-部署要求)
2. [快速部署](#2-快速部署)
3. [生产部署](#3-生产部署)
4. [配置说明](#4-配置说明)
5. [监控与维护](#5-监控与维护)
6. [故障排除](#6-故障排除)

---

## 1. 部署要求

### 1.1 系统要求

#### 硬件要求

| 环境 | CPU | 内存 | 磁盘 | 网络 |
|------|-----|------|------|------|
| **最小配置** | 4核 | 8GB | 50GB SSD | 100Mbps |
| **推荐配置** | 8核+ | 16GB+ | 100GB+ SSD | 1000Mbps |
| **生产配置** | 16核+ | 32GB+ | 500GB+ SSD | 1000Mbps |

#### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 运行时环境 |
| Docker | 20.10+ | 容器化部署 |
| Docker Compose | 2.0+ | 编排工具 |
| InfluxDB | 2.6+ | 时序数据库 |
| Redis | 6.0+ | 缓存服务 |

### 1.2 操作系统支持

- ✅ Ubuntu 20.04 LTS / 22.04 LTS
- ✅ CentOS 7 / 8
- ✅ Debian 11 / 12
- ✅ Windows Server 2019+
- ✅ macOS (开发环境)

---

## 2. 快速部署

### 2.1 Docker Compose 部署 (推荐)

#### 步骤1: 下载项目

```bash
git clone https://github.com/your-org/miaota-industrial-agent.git
cd miaota-industrial-agent
```

#### 步骤2: 配置环境

```bash
# 复制配置文件
cp config/settings.yaml.example config/settings.yaml

# 编辑配置
vim config/settings.yaml
```

#### 步骤3: 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

#### 步骤4: 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# API测试
curl http://localhost:8000/api/v1/system/status
```

### 2.2 手动部署

#### 步骤1: 安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# CentOS
sudo yum install -y python3 python3-pip
```

#### 步骤2: 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 步骤3: 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 步骤4: 配置数据库

```bash
# 启动InfluxDB
docker run -d \
  --name influxdb \
  -p 8086:8086 \
  -v influxdb-data:/var/lib/influxdb2 \
  influxdb:2.6

# 启动Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:6-alpine
```

#### 步骤5: 初始化配置

```bash
# 创建目录
mkdir -p data/db data/knowledge_base data/reports logs

# 复制配置
cp config/settings.yaml.example config/settings.yaml
```

#### 步骤6: 启动服务

```bash
# 开发模式
python src/main.py

# 生产模式 (使用Gunicorn)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app --bind 0.0.0.0:8000
```

---

## 3. 生产部署

### 3.1 高可用架构

```
                    ┌─────────────┐
                    │   Nginx     │
                    │   (LB)      │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
     ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
     │  App #1   │   │  App #2   │   │  App #3   │
     │  :8000    │   │  :8001    │   │  :8002    │
     └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
┌────▼────┐          ┌─────▼─────┐         ┌────▼────┐
│InfluxDB │          │  Redis    │         │ChromaDB │
│Cluster  │          │ Cluster   │         │         │
└─────────┘          └───────────┘         └─────────┘
```

### 3.2 Kubernetes 部署

#### 创建命名空间

```bash
kubectl create namespace miaota
```

#### 部署配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: miaota-app
  namespace: miaota
spec:
  replicas: 3
  selector:
    matchLabels:
      app: miaota
  template:
    metadata:
      labels:
        app: miaota
    spec:
      containers:
      - name: app
        image: miaota/industrial-agent:v1.0.0-beta1
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: INFLUXDB_URL
          value: "http://influxdb:8086"
        - name: REDIS_URL
          value: "redis://redis:6379"
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: miaota-config
---
apiVersion: v1
kind: Service
metadata:
  name: miaota-service
  namespace: miaota
spec:
  selector:
    app: miaota
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 部署命令

```bash
# 应用配置
kubectl apply -f k8s/

# 查看状态
kubectl get pods -n miaota

# 查看日志
kubectl logs -f deployment/miaota-app -n miaota
```

### 3.3 Nginx 反向代理配置

```nginx
# /etc/nginx/conf.d/miaota.conf
upstream miaota_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    keepalive 32;
}

server {
    listen 80;
    server_name miaota.example.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name miaota.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 静态文件
    location /static {
        alias /app/static;
        expires 30d;
    }
    
    # API代理
    location / {
        proxy_pass http://miaota_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 3.4 数据库配置

#### InfluxDB 集群

```yaml
# docker-compose.influxdb-cluster.yml
version: '3.8'
services:
  influxdb-meta-1:
    image: influxdb:2.6-meta
    environment:
      - INFLUXDB_META_DIR=/var/lib/influxdb/meta
      
  influxdb-data-1:
    image: influxdb:2.6-data
    environment:
      - INFLUXDB_DATA_DIR=/var/lib/influxdb/data
      - INFLUXDB_META_SERVERS=influxdb-meta-1:8091
```

#### Redis 集群

```bash
# 创建Redis集群
docker run --rm -it redis:6-alpine \
  redis-cli --cluster create \
  172.18.0.2:6379 172.18.0.3:6379 172.18.0.4:6379 \
  --cluster-replicas 1
```

---

## 4. 配置说明

### 4.1 主要配置文件

#### settings.yaml

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  debug: false

# 数据库配置
database:
  influxdb:
    url: "http://localhost:8086"
    token: "your-token"
    org: "miaota"
    bucket: "industrial_data"
  
  sqlite:
    path: "data/db/miaota.db"
  
  redis:
    host: "localhost"
    port: 6379
    db: 0
  
  chromadb:
    path: "data/chroma"

# PLC配置
plc:
  - name: "S7-1200-1"
    type: "s7"
    host: "192.168.1.10"
    port: 102
    rack: 0
    slot: 1
    reconnect_interval: 10
    
  - name: "Modbus-TCP-1"
    type: "modbus"
    host: "192.168.1.20"
    port: 502
    unit_id: 1

# 采集配置
collection:
  interval: 5  # 秒
  batch_size: 100
  buffer_size: 10000

# AI模型配置
models:
  llm:
    provider: "qwen"  # qwen/openai/chatglm
    api_key: "your-api-key"
    model: "qwen-turbo"
    temperature: 0.7
  
  anomaly_detection:
    algorithm: "isolation_forest"
    contamination: 0.05
  
  forecasting:
    default_model: "prophet"
    auto_select: true

# 通知配置
notification:
  channels:
    feishu:
      enabled: true
      webhook_url: "https://open.feishu.cn/..."
    
    dingtalk:
      enabled: false
      webhook_url: ""
    
    sms:
      enabled: false
      provider: "aliyun"
      access_key: ""
      secret_key: ""

# 安全配置
security:
  jwt_secret: "your-secret-key"
  token_expire_hours: 24
  password_min_length: 8
  max_login_attempts: 5

# 日志配置
logging:
  level: "INFO"
  format: "json"
  output: "file"
  max_size: "100MB"
  max_backup: 10
```

### 4.2 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MIAOTA_ENV` | 运行环境 | `production` |
| `MIAOTA_CONFIG` | 配置文件路径 | `config/settings.yaml` |
| `INFLUXDB_URL` | InfluxDB地址 | `http://localhost:8086` |
| `INFLUXDB_TOKEN` | InfluxDB Token | - |
| `REDIS_URL` | Redis地址 | `redis://localhost:6379` |
| `LLM_API_KEY` | LLM API密钥 | - |
| `JWT_SECRET` | JWT密钥 | - |

---

## 5. 监控与维护

### 5.1 系统监控

#### 使用 Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
```

#### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `up` | 服务存活 | =0 告警 |
| `http_requests_total` | HTTP请求数 | - |
| `http_request_duration_seconds` | 请求延迟 | >2s 告警 |
| `plc_connection_status` | PLC连接状态 | =0 告警 |
| `data_collection_rate` | 采集速率 | 下降50% 告警 |

### 5.2 日志管理

#### 日志轮转配置

```yaml
# config/logging.yaml
logging:
  version: 1
  handlers:
    file:
      class: logging.handlers.RotatingFileHandler
      filename: logs/app.log
      maxBytes: 104857600  # 100MB
      backupCount: 10
    
    error_file:
      class: logging.handlers.RotatingFileHandler
      filename: logs/error.log
      maxBytes: 104857600
      backupCount: 10
      level: ERROR
```

#### 日志收集 (使用 ELK)

```yaml
# docker-compose.elk.yml
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"
  
  logstash:
    image: logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  
  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
```

### 5.3 备份策略

#### 自动备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份InfluxDB
docker exec influxdb influx backup /backup/influxdb
docker cp influxdb:/backup/influxdb $BACKUP_DIR/

# 备份SQLite
cp data/db/miaota.db $BACKUP_DIR/

# 备份配置
tar czvf $BACKUP_DIR/config.tar.gz config/

# 备份知识库
tar czvf $BACKUP_DIR/knowledge.tar.gz data/knowledge_base/

# 上传到远程 (可选)
# aws s3 sync $BACKUP_DIR s3://your-bucket/backups/

# 清理旧备份 (保留7天)
find /backup -type d -mtime +7 -exec rm -rf {} \;

echo "备份完成: $BACKUP_DIR"
```

#### Cron定时任务

```bash
# 每天凌晨2点备份
0 2 * * * /app/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## 6. 故障排除

### 6.1 服务无法启动

**症状**: `docker-compose up` 失败

**排查步骤**:
1. 检查端口占用: `netstat -tlnp | grep 8000`
2. 检查配置文件: `python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"`
3. 检查日志: `docker-compose logs app`

### 6.2 数据库连接失败

**症状**: 无法写入数据

**排查步骤**:
1. 检查InfluxDB状态: `docker ps | grep influxdb`
2. 测试连接: `curl http://localhost:8086/health`
3. 检查Token: `docker logs influxdb | grep "Token"`

### 6.3 PLC采集失败

**症状**: 数据采集状态为"离线"

**排查步骤**:
1. 网络连通性: `ping <PLC_IP>`
2. 端口开放: `telnet <PLC_IP> 102`
3. 查看日志: `tail -f logs/collector.log`

### 6.4 性能问题

**症状**: 系统响应慢

**优化建议**:
1. 增加内存: `docker update --memory=8g miaota-app`
2. 启用缓存: 配置Redis
3. 数据库优化: 创建索引
4. 增加工作进程: `workers: 8`

---

## 附录

### A. 常用命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新镜像
docker-compose pull && docker-compose up -d

# 进入容器
docker exec -it miaota-app bash

# 查看资源使用
docker stats
```

### B. 端口列表

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | 应用服务 | Web/API |
| 8086 | InfluxDB | 时序数据库 |
| 6379 | Redis | 缓存服务 |
| 8000 | ChromaDB | 向量数据库 |
| 9090 | Prometheus | 监控系统 |
| 3000 | Grafana | 可视化 |

---

**文档版本**: v1.0.0-beta1  
**最后更新**: 2026-03-26
