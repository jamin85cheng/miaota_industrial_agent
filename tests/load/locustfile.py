"""
压力测试脚本

使用Locust进行API压力测试
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import json
import random
import time
from datetime import datetime, timedelta


class IndustrialUser(HttpUser):
    """工业监控系统用户"""
    
    wait_time = between(1, 5)  # 请求间隔1-5秒
    
    def on_start(self):
        """用户开始时执行"""
        # 登录获取token
        self.login()
        self.devices = []
        self.load_devices()
    
    def login(self):
        """用户登录"""
        response = self.client.post(
            "/auth/login",
            json={
                "username": "operator",
                "password": "operator123"
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    def load_devices(self):
        """加载设备列表"""
        if not self.token:
            return
        
        response = self.client.get("/devices?limit=100", headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            self.devices = [d["id"] for d in data.get("devices", [])]
    
    @task(10)
    def get_health(self):
        """健康检查 - 最高频"""
        self.client.get("/health")
    
    @task(8)
    def get_devices(self):
        """获取设备列表"""
        if not self.token:
            return
        
        params = {
            "skip": random.randint(0, 50),
            "limit": random.randint(10, 50)
        }
        self.client.get("/devices", params=params, headers=self.headers)
    
    @task(6)
    def get_device_detail(self):
        """获取设备详情"""
        if not self.devices:
            return
        
        device_id = random.choice(self.devices)
        self.client.get(f"/devices/{device_id}", headers=self.headers)
    
    @task(5)
    def query_data(self):
        """查询历史数据"""
        if not self.token:
            return
        
        # 随机时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=random.randint(1, 24))
        
        payload = {
            "tags": ["temperature", "pressure"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "aggregation": random.choice(["raw", "mean", "max"]),
            "interval": random.choice(["5m", "1h"])
        }
        
        self.client.post("/collection/data/query", json=payload, headers=self.headers)
    
    @task(5)
    def get_latest_data(self):
        """获取最新数据"""
        if not self.token:
            return
        
        tags = random.sample(["temperature", "pressure", "flow", "ph"], k=random.randint(1, 4))
        self.client.get(f"/collection/data/latest?tags={','.join(tags)}", headers=self.headers)
    
    @task(4)
    def get_alerts(self):
        """获取告警列表"""
        if not self.token:
            return
        
        params = {
            "status": random.choice(["active", "acknowledged", None]),
            "severity": random.choice(["critical", "warning", "info", None]),
            "limit": random.randint(10, 100)
        }
        # 移除None值
        params = {k: v for k, v in params.items() if v is not None}
        
        self.client.get("/alerts", params=params, headers=self.headers)
    
    @task(3)
    def get_collection_status(self):
        """获取采集状态"""
        if not self.token:
            return
        
        self.client.get("/collection/status", headers=self.headers)
    
    @task(2)
    def analyze_anomaly(self):
        """异常检测分析"""
        if not self.token:
            return
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=6)
        
        payload = {
            "tag": "temperature",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "sensitivity": random.uniform(0.8, 0.99)
        }
        
        self.client.post("/analysis/anomaly", json=payload, headers=self.headers)
    
    @task(2)
    def search_knowledge(self):
        """搜索知识库"""
        if not self.token:
            return
        
        queries = ["温度异常", "压力过高", "泵故障", "污泥膨胀", "溶解氧低"]
        payload = {
            "query": random.choice(queries),
            "limit": random.randint(3, 10)
        }
        
        self.client.post("/knowledge/search", json=payload, headers=self.headers)
    
    @task(1)
    def diagnose(self):
        """智能诊断"""
        if not self.token:
            return
        
        symptoms = [
            "曝气池溶解氧持续偏低",
            "出水COD超标",
            "二沉池污泥上浮",
            "风机噪音异常"
        ]
        
        payload = {
            "symptoms": random.choice(symptoms),
            "device_id": random.choice(self.devices) if self.devices else None,
            "tags": {
                "temperature": random.uniform(20, 50),
                "pressure": random.uniform(1, 10)
            }
        }
        
        self.client.post("/knowledge/diagnose", json=payload, headers=self.headers)


class AdminUser(HttpUser):
    """管理员用户 - 执行管理操作"""
    
    wait_time = between(5, 15)
    weight = 1  # 管理员用户较少
    
    def on_start(self):
        self.login()
    
    def login(self):
        response = self.client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(3)
    def create_device(self):
        """创建设备"""
        if not self.token:
            return
        
        import uuid
        device_id = f"DEV_{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            "name": f"Test Device {device_id}",
            "type": random.choice(["s7", "modbus"]),
            "host": f"192.168.1.{random.randint(10, 200)}",
            "port": random.choice([102, 502]),
            "rack": 0,
            "slot": 1,
            "tags": [
                {"name": "temp", "address": "DB1.DBD0", "type": "float"},
                {"name": "pressure", "address": "DB1.DBD4", "type": "float"}
            ]
        }
        
        self.client.post("/devices", json=payload, headers=self.headers)
    
    @task(2)
    def get_all_alerts(self):
        """获取所有告警"""
        if not self.token:
            return
        
        self.client.get("/alerts?limit=1000", headers=self.headers)
    
    @task(1)
    def create_alert_rule(self):
        """创建告警规则"""
        if not self.token:
            return
        
        import uuid
        rule_id = f"RULE_{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            "rule_id": rule_id,
            "name": f"Test Rule {rule_id}",
            "enabled": True,
            "condition": {
                "type": "threshold",
                "tag": "temperature",
                "operator": ">",
                "value": random.uniform(50, 100)
            },
            "severity": random.choice(["critical", "warning", "info"]),
            "message": "Test alert message",
            "suppression_window_minutes": 30
        }
        
        self.client.post("/alerts/rules", json=payload, headers=self.headers)


# 事件监听
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """记录每个请求"""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始"""
    print("=" * 50)
    print("压力测试开始")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束"""
    print("=" * 50)
    print("压力测试结束")
    print("=" * 50)
    
    if isinstance(environment.runner, MasterRunner):
        # 主节点输出统计
        stats = environment.runner.stats
        print(f"\n总请求数: {stats.total.num_requests}")
        print(f"失败数: {stats.total.num_failures}")
        print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
        print(f"RPS: {stats.total.total_rps:.2f}")
