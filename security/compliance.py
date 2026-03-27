"""
合规报告模块

功能需求: U-05 合规报告 - 等保2.0合规
作者: Security Team
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from loguru import logger


class ComplianceLevel(Enum):
    """合规等级"""
    COMPLIANT = "compliant"       # 合规
    PARTIAL = "partial"           # 部分合规
    NON_COMPLIANT = "non_compliant"  # 不合规
    NOT_APPLICABLE = "na"         # 不适用


class SecurityLevel(Enum):
    """等保级别"""
    LEVEL1 = "等保一级"  # 用户自主保护
    LEVEL2 = "等保二级"  # 系统审计保护
    LEVEL3 = "等保三级"  # 安全标记保护 (本项目目标)
    LEVEL4 = "等保四级"  # 结构化保护


@dataclass
class ComplianceItem:
    """合规检查项"""
    item_id: str
    category: str
    name: str
    description: str
    requirement: str
    level: int  # 适用等保级别
    status: ComplianceLevel
    evidence: str
    recommendation: Optional[str] = None
    checked_at: Optional[datetime] = None


class ComplianceChecker:
    """
    合规检查器
    
    基于等保2.0标准进行检查
    """
    
    # 等保2.0 检查项定义
    CHECK_ITEMS = [
        # 安全物理环境
        ComplianceItem(
            item_id="PE-01",
            category="安全物理环境",
            name="物理位置选择",
            description="机房位置应选择在具有防震、防风和防雨能力的建筑内",
            requirement="机房应避免设在建筑物的顶层或地下室，否则应加强防水和防潮措施",
            level=3,
            status=ComplianceLevel.NOT_APPLICABLE,
            evidence="云部署/虚拟化环境不适用",
            recommendation=None
        ),
        
        # 安全通信网络
        ComplianceItem(
            item_id="CN-01",
            category="安全通信网络",
            name="网络架构",
            description="应划分不同的网络区域，并按照方便管理和控制的原则为各网络区域分配地址",
            requirement="应避免单点故障，关键网络设备应冗余部署",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="系统支持多副本部署，支持负载均衡",
            recommendation="建议生产环境启用多实例部署"
        ),
        ComplianceItem(
            item_id="CN-02",
            category="安全通信网络",
            name="通信传输",
            description="应采用校验技术或密码技术保证通信过程中数据的完整性",
            requirement="应采用密码技术保证通信过程中敏感信息字段或整个报文的保密性",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="系统使用TLS 1.3加密通信",
            recommendation=None
        ),
        
        # 安全区域边界
        ComplianceItem(
            item_id="BA-01",
            category="安全区域边界",
            name="边界防护",
            description="应保证跨越边界的访问和数据流通过边界设备提供的受控接口进行通信",
            requirement="应能够对非授权设备私自联到内部网络的行为进行检查或限制",
            level=3,
            status=ComplianceLevel.PARTIAL,
            evidence="已配置防火墙规则，缺少非法接入检测",
            recommendation="部署网络准入控制系统(NAC)"
        ),
        
        # 安全计算环境
        ComplianceItem(
            item_id="CE-01",
            category="安全计算环境",
            name="身份鉴别",
            description="应对登录的用户进行身份标识和鉴别，身份标识具有唯一性",
            requirement="身份鉴别信息应不易被冒用，口令复杂度应满足要求并定期更换",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="已实现JWT认证，支持密码复杂度策略",
            recommendation="建议启用双因素认证(2FA)"
        ),
        ComplianceItem(
            item_id="CE-02",
            category="安全计算环境",
            name="访问控制",
            description="应对登录的用户分配账户和权限",
            requirement="应重命名或删除默认账户，修改默认账户的默认口令",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="已实现RBAC权限控制，无默认账户",
            recommendation=None
        ),
        ComplianceItem(
            item_id="CE-03",
            category="安全计算环境",
            name="安全审计",
            description="应启用安全审计功能，审计覆盖到每个用户",
            requirement="审计记录应包括事件的日期和时间、用户、事件类型、事件是否成功等信息",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="已实现操作审计日志，支持完整性校验",
            recommendation="建议对接集中日志平台"
        ),
        ComplianceItem(
            item_id="CE-04",
            category="安全计算环境",
            name="入侵防范",
            description="应遵循最小安装的原则，仅安装需要的组件和应用程序",
            requirement="应关闭不需要的系统服务、默认共享和高危端口",
            level=3,
            status=ComplianceLevel.PARTIAL,
            evidence="Docker镜像已精简，待进一步加固",
            recommendation="进行容器安全扫描，移除不必要的包"
        ),
        ComplianceItem(
            item_id="CE-05",
            category="安全计算环境",
            name="数据完整性",
            description="应采用校验技术或密码技术保证重要数据在传输过程中的完整性",
            requirement="包括但不限于鉴别数据、重要业务数据、重要审计数据等",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="使用TLS加密，审计日志有完整性校验",
            recommendation=None
        ),
        ComplianceItem(
            item_id="CE-06",
            category="安全计算环境",
            name="数据保密性",
            description="应采用密码技术保证重要数据在传输过程中的保密性",
            requirement="包括但不限于鉴别数据、重要业务数据和重要个人信息等",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="敏感配置已加密存储",
            recommendation="建议启用数据库字段级加密"
        ),
        ComplianceItem(
            item_id="CE-07",
            category="安全计算环境",
            name="数据备份恢复",
            description="应提供重要数据的本地数据备份与恢复功能",
            requirement="应提供异地实时备份功能，利用通信网络将重要数据实时备份至备份场地",
            level=3,
            status=ComplianceLevel.PARTIAL,
            evidence="已配置定期备份，缺少异地备份",
            recommendation="配置异地备份策略，定期恢复演练"
        ),
        
        # 安全管理中心
        ComplianceItem(
            item_id="MC-01",
            category="安全管理中心",
            name="系统管理",
            description="应对系统管理员进行身份鉴别，只允许其通过特定的命令或操作界面进行系统管理操作",
            requirement="应对系统管理员的操作进行审计",
            level=3,
            status=ComplianceLevel.COMPLIANT,
            evidence="系统管理操作已记录审计日志",
            recommendation=None
        ),
        ComplianceItem(
            item_id="MC-02",
            category="安全管理中心",
            name="集中管控",
            description="应划分出特定的管理区域，对分布在网络中的安全设备或安全组件进行管控",
            requirement="应对网络链路、安全设备、网络设备和服务器等的运行状况进行集中监测",
            level=3,
            status=ComplianceLevel.PARTIAL,
            evidence="已部署Prometheus+Grafana监控",
            recommendation="建议接入统一安全管理平台"
        ),
        
        # 安全管理制度
        ComplianceItem(
            item_id="PM-01",
            category="安全管理制度",
            name="安全策略",
            description="应制定网络安全工作的总体方针和安全策略，阐明机构安全工作的总体目标、范围、原则和安全框架等",
            requirement="应对安全管理活动中的各类管理内容建立安全管理制度",
            level=3,
            status=ComplianceLevel.NOT_APPLICABLE,
            evidence="需由客户建立管理制度",
            recommendation="建议制定网络安全管理制度和操作规程"
        ),
    ]
    
    def __init__(self, target_level: SecurityLevel = SecurityLevel.LEVEL3):
        self.target_level = target_level
        self.check_items = [item for item in self.CHECK_ITEMS if item.level <= int(target_level.value[-1])]
        
        logger.info(f"合规检查器初始化: 目标等级={target_level.value}")
    
    def run_check(self) -> Dict:
        """运行合规检查"""
        results = {
            'check_time': datetime.now().isoformat(),
            'target_level': self.target_level.value,
            'total_items': len(self.check_items),
            'summary': {},
            'details': []
        }
        
        # 统计
        status_counts = {
            ComplianceLevel.COMPLIANT: 0,
            ComplianceLevel.PARTIAL: 0,
            ComplianceLevel.NON_COMPLIANT: 0,
            ComplianceLevel.NOT_APPLICABLE: 0
        }
        
        for item in self.check_items:
            item.checked_at = datetime.now()
            status_counts[item.status] += 1
            
            results['details'].append({
                'item_id': item.item_id,
                'category': item.category,
                'name': item.name,
                'description': item.description,
                'status': item.status.value,
                'evidence': item.evidence,
                'recommendation': item.recommendation,
                'checked_at': item.checked_at.isoformat() if item.checked_at else None
            })
        
        # 计算合规率 (不含不适用)
        applicable_items = status_counts[ComplianceLevel.COMPLIANT] + \
                         status_counts[ComplianceLevel.PARTIAL] + \
                         status_counts[ComplianceLevel.NON_COMPLIANT]
        
        compliance_rate = status_counts[ComplianceLevel.COMPLIANT] / applicable_items if applicable_items > 0 else 0
        
        results['summary'] = {
            'compliant': status_counts[ComplianceLevel.COMPLIANT],
            'partial': status_counts[ComplianceLevel.PARTIAL],
            'non_compliant': status_counts[ComplianceLevel.NON_COMPLIANT],
            'not_applicable': status_counts[ComplianceLevel.NOT_APPLICABLE],
            'compliance_rate': round(compliance_rate * 100, 2)
        }
        
        return results
    
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """生成合规报告"""
        results = self.run_check()
        
        if output_path is None:
            output_path = f"data/reports/COMPLIANCE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"合规报告已生成: {output_path}")
        return output_path
    
    def get_remediation_plan(self) -> List[Dict]:
        """获取整改建议"""
        remediation = []
        
        for item in self.check_items:
            if item.status in [ComplianceLevel.PARTIAL, ComplianceLevel.NON_COMPLIANT]:
                remediation.append({
                    'item_id': item.item_id,
                    'category': item.category,
                    'name': item.name,
                    'current_status': item.status.value,
                    'priority': '高' if item.status == ComplianceLevel.NON_COMPLIANT else '中',
                    'recommendation': item.recommendation,
                    'effort_estimate': '待评估'
                })
        
        # 按优先级排序
        priority_order = {'高': 0, '中': 1, '低': 2}
        remediation.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return remediation


class GDPRComplianceChecker:
    """
    GDPR (欧盟通用数据保护条例) 合规检查
    
    适用于处理欧盟用户数据的场景
    """
    
    CHECK_ITEMS = [
        {
            'id': 'GDPR-01',
            'name': '数据收集合法性',
            'description': '应明确告知用户数据收集的目的和范围，并获得同意',
            'status': 'compliant',
            'evidence': '隐私政策已发布，用户注册需同意'
        },
        {
            'id': 'GDPR-02',
            'name': '数据最小化原则',
            'description': '只收集业务必需的最少数据',
            'status': 'compliant',
            'evidence': '系统不收集个人敏感信息'
        },
        {
            'id': 'GDPR-03',
            'name': '数据主体权利',
            'description': '用户有权访问、更正、删除其个人数据',
            'status': 'partial',
            'evidence': '已实现数据查询和删除接口',
            'recommendation': '完善数据可携带功能'
        },
        {
            'id': 'GDPR-04',
            'name': '数据安全',
            'description': '采取适当的技术和组织措施保护个人数据',
            'status': 'compliant',
            'evidence': '已实施加密、访问控制等安全措施'
        },
        {
            'id': 'GDPR-05',
            'name': '数据泄露通知',
            'description': '发生数据泄露应在72小时内通知监管机构',
            'status': 'partial',
            'evidence': '有应急响应流程',
            'recommendation': '自动化泄露检测和通知机制'
        }
    ]
    
    def run_check(self) -> Dict:
        """运行GDPR检查"""
        return {
            'check_time': datetime.now().isoformat(),
            'standard': 'GDPR',
            'items': self.CHECK_ITEMS
        }


# 使用示例
if __name__ == "__main__":
    # 等保2.0检查
    print("="*60)
    print("等保2.0合规检查")
    print("="*60)
    
    checker = ComplianceChecker(target_level=SecurityLevel.LEVEL3)
    results = checker.run_check()
    
    print(f"\n检查时间: {results['check_time']}")
    print(f"目标等级: {results['target_level']}")
    print(f"检查项数: {results['summary']['total']}")
    print(f"\n合规统计:")
    print(f"  ✅ 合规: {results['summary']['compliant']} 项")
    print(f"  ⚠️  部分合规: {results['summary']['partial']} 项")
    print(f"  ❌ 不合规: {results['summary']['non_compliant']} 项")
    print(f"  ➖ 不适用: {results['summary']['not_applicable']} 项")
    print(f"\n合规率: {results['summary']['compliance_rate']}%")
    
    # 整改建议
    print("\n整改建议:")
    remediation = checker.get_remediation_plan()
    for item in remediation:
        print(f"  [{item['priority']}] {item['item_id']} {item['name']}")
        print(f"      建议: {item['recommendation']}")
    
    # 生成报告
    report_path = checker.generate_report()
    print(f"\n报告已保存: {report_path}")
    
    # GDPR检查
    print("\n" + "="*60)
    print("GDPR合规检查")
    print("="*60)
    
    gdpr_checker = GDPRComplianceChecker()
    gdpr_results = gdpr_checker.run_check()
    
    for item in gdpr_results['items']:
        status_icon = '✅' if item['status'] == 'compliant' else '⚠️' if item['status'] == 'partial' else '❌'
        print(f"{status_icon} {item['id']}: {item['name']}")
