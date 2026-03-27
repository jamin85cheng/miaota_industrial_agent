"""
输入验证模块单元测试

安全工程师编写 - 验证安全防护能力
"""

import pytest
from security.input_validator import (
    InputValidator, 
    ValidationError, 
    RateLimiter
)


class TestInputValidator:
    """输入验证器测试"""
    
    def test_validate_measurement_valid(self):
        """测试有效的测量名称"""
        assert InputValidator.validate_measurement("temperature") == "temperature"
        assert InputValidator.validate_measurement("temp_sensor_1") == "temp_sensor_1"
        assert InputValidator.validate_measurement("_private") == "_private"
    
    def test_validate_measurement_invalid(self):
        """测试无效的测量名称"""
        with pytest.raises(ValidationError):
            InputValidator.validate_measurement("123invalid")  # 数字开头
        
        with pytest.raises(ValidationError):
            InputValidator.validate_measurement("invalid-char")  # 非法字符
        
        with pytest.raises(ValidationError):
            InputValidator.validate_measurement("")  # 空字符串
    
    def test_validate_measurement_sql_injection(self):
        """测试SQL注入防护"""
        # 尝试SQL注入
        with pytest.raises(ValidationError):
            InputValidator.validate_measurement("table'; DROP TABLE users; --")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_measurement("users; DELETE FROM passwords")
    
    def test_validate_tags_valid(self):
        """测试有效的标签"""
        tags = {"device": "PLC_001", "location": "车间A"}
        result = InputValidator.validate_tags(tags)
        assert result["device"] == "PLC_001"
        assert result["location"] == "车间A"
    
    def test_validate_tags_xss_protection(self):
        """测试XSS防护"""
        tags = {"input": "<script>alert('xss')</script>"}
        result = InputValidator.validate_tags(tags)
        # HTML应该被转义
        assert "<script>" not in result["input"]
        assert "&lt;script&gt;" in result["input"]
    
    def test_validate_tags_dangerous_chars(self):
        """测试危险字符检测"""
        with pytest.raises(ValidationError):
            InputValidator.validate_tags({"key": "value; DROP TABLE"})
    
    def test_validate_fields_type_conversion(self):
        """测试字段类型转换"""
        fields = {
            "value": 42,
            "enabled": True,
            "name": "test"
        }
        result = InputValidator.validate_fields(fields)
        assert result["value"] == 42
        assert result["enabled"] == True
        assert result["name"] == "test"
    
    def test_validate_timestamp_iso(self):
        """测试ISO格式时间戳"""
        ts_str = "2024-01-15T08:30:00Z"
        result = InputValidator.validate_timestamp(ts_str)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_validate_timestamp_unix(self):
        """测试Unix时间戳"""
        ts = 1705315800  # 2024-01-15 08:10:00 UTC
        result = InputValidator.validate_timestamp(ts)
        assert result.year == 2024


class TestRateLimiter:
    """速率限制器测试"""
    
    def test_rate_limit_basic(self):
        """测试基本速率限制"""
        limiter = RateLimiter(max_requests=3, window_seconds=1)
        
        # 前3次应该允许
        assert limiter.is_allowed("client_1") == True
        assert limiter.is_allowed("client_1") == True
        assert limiter.is_allowed("client_1") == True
        
        # 第4次应该拒绝
        assert limiter.is_allowed("client_1") == False
    
    def test_rate_limit_different_clients(self):
        """测试不同客户端独立限制"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # client_1达到限制
        assert limiter.is_allowed("client_1") == True
        assert limiter.is_allowed("client_1") == True
        assert limiter.is_allowed("client_1") == False
        
        # client_2不受影响
        assert limiter.is_allowed("client_2") == True
        assert limiter.is_allowed("client_2") == True
    
    def test_rate_limit_window_reset(self):
        """测试时间窗口重置"""
        import time
        
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        
        # 第一次允许
        assert limiter.is_allowed("client") == True
        # 第二次拒绝
        assert limiter.is_allowed("client") == False
        
        # 等待窗口重置
        time.sleep(0.15)
        
        # 应该再次允许
        assert limiter.is_allowed("client") == True
    
    def test_get_remaining(self):
        """测试获取剩余次数"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        assert limiter.get_remaining("client") == 5
        
        limiter.is_allowed("client")
        assert limiter.get_remaining("client") == 4
        
        limiter.is_allowed("client")
        limiter.is_allowed("client")
        assert limiter.get_remaining("client") == 2
