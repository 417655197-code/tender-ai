"""
招标信息 AI 分析模块
使用 Kimimi API 进行分析
"""

import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Kimimi API 配置（硅基流动或其他国内API）
KIMIMI_API_KEY = os.environ.get("KIMIMI_API_KEY", "")
KIMIMI_API_BASE = os.environ.get("KIMIMI_API_BASE", "https://api.siliconflow.cn/v1")

SYSTEM_PROMPT = """你是一个专业的招投标顾问。请分析以下招标信息，给出专业的投资建议。

请按以下格式输出：
## 招标概要
[一句话描述这个招标]

## 投资价值评估
- 预算金额：[分析预算是否合理]
- 竞争程度：[预估竞争激烈程度]
- 甲方信誉：[分析甲方背景]

## 关键时间节点
- 报名截止：[从信息中提取]
- 开标时间：[从信息中提取]

## 投标建议
1. [优点]
2. [风险点]
3. [建议]

## 适合参与的企业类型
[什么样的企业适合投这个标]
"""


class TenderAnalyzer:
    """招标信息AI分析器"""

    def __init__(self, api_key: str = "", api_base: str = ""):
        self.api_key = api_key or KIMIMI_API_KEY
        self.api_base = api_base or KIMIMI_API_BASE

    def analyze(self, tender: Dict) -> str:
        """分析单条招标信息"""
        if not self.api_key:
            logger.warning("未配置API Key，返回默认分析")
            return self._default_analysis(tender)

        prompt = self._build_prompt(tender)
        # TODO: 调用API
        return prompt

    def analyze_batch(self, tenders: List[Dict]) -> List[Dict]:
        """批量分析招标信息"""
        results = []
        for tender in tenders:
            analysis = self.analyze(tender)
            tender['analysis'] = analysis
            results.append(tender)
        return results

    def _build_prompt(self, tender: Dict) -> str:
        """构建分析提示词"""
        return f"""## 招标信息
标题：{tender.get('title', '')}
来源：{tender.get('source', '')}
发布日期：{tender.get('publish_date', '')}
预算金额：{tender.get('amount', '未公开')}
地区：{tender.get('region', '')}
行业：{tender.get('industry', '')}
截止日期：{tender.get('deadline', '未公开')}
URL：{tender.get('url', '')}

{SYSTEM_PROMPT}"""

    def _default_analysis(self, tender: Dict) -> str:
        """默认分析（无API时使用）"""
        return f"""## 招标概要
{tender.get('title', '')}

## 投资价值评估
- 预算金额：{tender.get('amount', '待确认')}
- 地区：{tender.get('region', '')}
- 行业：{tender.get('industry', '')}

## 关键时间节点
- 截止日期：{tender.get('deadline', '待确认')}

## 投标建议
请登录查看完整信息或联系客服获取详细分析。
"""


def generate_daily_report(tenders: List[Dict], date: str = None) -> str:
    """生成每日招标简报"""
    if not date:
        date = datetime.now().strftime("%Y年%m月%d日")

    if not tenders:
        return f"""## 📋 {date} 招标简报

今日暂无新增招标信息

---
由 TenderAI 自动生成
"""

    report = f"""## 📋 {date} 招标简报

今日共获取 **{len(tenders)}** 条招标信息

"""

    # 按金额排序，取前5
    sorted_tenders = sorted(
        [t for t in tenders if t.get('amount')],
        key=lambda x: float(x.get('amount', '0').replace('万', '')),
        reverse=True
    )[:5]

    for i, t in enumerate(sorted_tenders, 1):
        report += f"""
### {i}. {t.get('title', '')}
- 💰 预算：{t.get('amount', '待确认')}
- 🏢 来源：{t.get('source', '')}
- 📍 地区：{t.get('region', '')}
- ⏰ 截止：{t.get('deadline', '待确认')}
- 🔗 [查看详情]({t.get('url', '')})
"""

    report += f"""
---
💡 共 {len(tenders)} 条招标，查看全部请登录系统

🤖 由 TenderAI 自动生成
"""

    return report


if __name__ == "__main__":
    # 测试
    from crawler import demo_data

    analyzer = TenderAnalyzer()
    tenders = demo_data()

    print("=== 批量分析测试 ===")
    results = analyzer.analyze_batch(tenders[:3])

    print("\n=== 生成日报测试 ===")
    report = generate_daily_report(tenders)
    print(report)
