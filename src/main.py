"""
TenderAI + MetalPrice 主程序
拆迁废金属综合工具 - 招标查询 + 金属价格监控
"""

import argparse
import logging
import json
import sys
from datetime import datetime
from typing import List, Dict

from crawler import TenderCrawler, demo_data as tender_demo_data
from baidu_search import BaiduSearchCrawler, crawl_tenders
from analyzer import TenderAnalyzer, generate_daily_report
from notifier import TenderNotifier
from metal_price_crawler import MetalPriceCrawler, get_demo_prices, generate_price_report

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tender_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TenderMetalApp:
    """招标+金属价格综合程序"""

    def __init__(self, config_path: str = "config/config.json"):
        self.config = self._load_config(config_path)
        self.crawler = TenderCrawler(self.config.get('tender', {}))
        self.analyzer = TenderAnalyzer(
            api_key=self.config.get('api_key', ''),
            api_base=self.config.get('api_base', '')
        )
        self.notifier = TenderNotifier(self.config)
        self.price_crawler = MetalPriceCrawler()

    def _load_config(self, path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {path}，使用默认配置")
            return self._default_config()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'tender': {
                'keywords': ['拆迁', '拆除', '房屋拆迁', '旧城改造', '棚户区改造'],
                'regions': ['温州市', '浙江省', '全国'],
                'days': 7
            },
            'metal_price': {
                'keywords': ['废钢', '废铜', '废铝', '废不锈钢']
            },
            'subscribers': [
                {'email': 'test@example.com', 'name': '测试用户'}
            ]
        }

    def run(self, mode: str = 'demo') -> None:
        """
        运行程序

        Args:
            mode: 
                'demo' - 演示模式（招标+价格）
                'tender' - 只查招标
                'price' - 只查价格
                'daily' - 每日定时任务（招标+价格）
        """
        logger.info(f"TenderMetalApp 启动，模式: {mode}")

        if mode == 'demo':
            self._run_demo()
        elif mode == 'tender':
            self._run_tender()
        elif mode == 'price':
            self._run_price()
        elif mode == 'daily':
            self._run_daily()
        else:
            logger.error(f"未知模式: {mode}")
            sys.exit(1)

    def _run_demo(self):
        """演示模式"""
        logger.info("=== 演示模式 ===")

        # 1. 获取招标演示数据
        tenders = tender_demo_data()
        logger.info(f"获取到 {len(tenders)} 条招标演示数据")

        # 2. 获取价格演示数据
        prices = get_demo_prices()
        logger.info(f"获取到 {len(prices)} 条价格数据")

        # 3. 生成综合报告
        report = self._generate_combined_report(tenders, prices)

        print("\n" + "="*60)
        print("📋 拆迁废金属综合简报（演示）")
        print("="*60)
        print(report)

        # 4. 保存报告
        with open(f'data/report_{datetime.now().strftime("%Y%m%d")}.md', 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info("综合报告已保存")

    def _run_tender(self):
        """只查招标"""
        logger.info("=== 招标查询模式 ===")

        tender_config = self.config.get('tender', {})
        keywords = tender_config.get('keywords', [])
        days = tender_config.get('days', 7)

        # 先尝试百度搜索（更稳定）
        logger.info("尝试百度搜索...")
        tenders = crawl_tenders(keywords)

        # 如果百度没结果，尝试原来的爬虫
        if not tenders:
            tenders = self.crawler.fetch_all(keywords, days)

        # 如果还是没结果，使用演示数据
        if not tenders:
            logger.warning("未获取到真实数据，使用演示数据")
            tenders = tender_demo_data()

        logger.info(f"获取到 {len(tenders)} 条招标")

        # AI分析
        tenders = self.analyzer.analyze_batch(tenders)

        # 生成报告
        report = generate_daily_report(tenders)

        # 发送通知
        results = self.notifier.notify(tenders, report)
        logger.info(f"通知结果: {results}")

        # 保存数据
        self._save_tenders(tenders)

    def _run_price(self):
        """只查价格"""
        logger.info("=== 价格查询模式 ===")

        # 尝试爬取真实价格
        summary = self.price_crawler.get_market_summary()
        
        if summary.get('indices'):
            prices = []
            for name, data in summary['indices'].items():
                prices.append({
                    'name': name,
                    'market': '全国',
                    'price': data.get('price', 0),
                    'change': data.get('change', 0),
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        else:
            # 使用演示数据
            prices = get_demo_prices()
            logger.info("使用演示价格数据")

        # 生成价格报告
        report = generate_price_report(prices)
        print("\n" + "="*60)
        print("📊 金属价格日报")
        print("="*60)
        print(report)

        # 保存价格数据
        self._save_prices(prices)

    def _run_daily(self):
        """每日定时任务 - 招标+价格"""
        logger.info("=== 每日定时任务 ===")

        # 1. 处理招标
        self._run_tender()

        # 2. 处理价格
        self._run_price()

    def _generate_combined_report(self, tenders: List[Dict], prices: List[Dict]) -> str:
        """生成综合简报"""
        date_str = datetime.now().strftime("%Y年%m月%d日")

        report = f"""## 📋 {date_str} 拆迁废金属综合简报

---

### 🏗️ 招标信息

今日共获取 **{len(tenders)}** 条招标信息

"""

        # 按金额排序，取前5
        sorted_tenders = sorted(
            [t for t in tenders if t.get('amount')],
            key=lambda x: float(x.get('amount', '0').replace('万', '')),
            reverse=True
        )[:5]

        for i, t in enumerate(sorted_tenders, 1):
            report += f"""#### {i}. {t.get('title', '')}
- 💰 预算：{t.get('amount', '待确认')}
- 🏢 来源：{t.get('source', '')}
- 📍 地区：{t.get('region', '')}
- ⏰ 截止：{t.get('deadline', '待确认')}

"""

        report += f"""---

### 📊 金属价格

"""

        for p in prices:
            change_icon = '📈' if p.get('change', 0) > 0 else '📉' if p.get('change', 0) < 0 else '➡️'
            change_str = f"{p.get('change'):+.2f}" if isinstance(p.get('change'), (int, float)) else '0'
            pct_str = f"{p.get('change_pct'):+.2f}%" if isinstance(p.get('change_pct'), (int, float)) else ''

            report += f"""#### {p.get('name', '')} - {p.get('market', '')}
- 💰 价格：**{p.get('price', 0):,.2f}** {p.get('unit', '元/吨')}
- {change_icon} 涨跌：{change_str} {pct_str}

"""

        report += f"""---

### 💡 生意提示

查招标 → 中标做拆除 → 产出废钢/废铜/废铝 → 富宝查价卖出

---
🤖 由 TenderAI + MetalPrice 自动生成
"""

        return report

    def _save_tenders(self, tenders: List[Dict]):
        """保存招标数据"""
        filename = f"data/tenders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tenders, f, ensure_ascii=False, indent=2)
        logger.info(f"招标数据已保存: {filename}")

    def _save_prices(self, prices: List[Dict]):
        """保存价格数据"""
        filename = f"data/prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)
        logger.info(f"价格数据已保存: {filename}")

    def add_subscriber(self, email: str, name: str = ''):
        """添加订阅者"""
        subscriber = {'email': email, 'name': name}
        if subscriber not in self.config['subscribers']:
            self.config['subscribers'].append(subscriber)
            logger.info(f"添加订阅者: {email}")


def main():
    parser = argparse.ArgumentParser(description='TenderAI + MetalPrice - 拆迁废金属综合工具')
    parser.add_argument('--config', '-c', default='config/config.json', help='配置文件路径')
    parser.add_argument('--mode', '-m', choices=['demo', 'tender', 'price', 'daily'],
                        default='demo', help='运行模式')
    parser.add_argument('--keywords', '-k', nargs='+', help='搜索关键词（招标）')
    parser.add_argument('--report', '-r', action='store_true', help='只生成报告')

    args = parser.parse_args()

    # 创建目录
    import os
    for dir in ['config', 'data', 'logs']:
        os.makedirs(dir, exist_ok=True)

    # 运行
    app = TenderMetalApp(args.config)

    if args.keywords:
        app.config['tender']['keywords'] = args.keywords

    app.run(mode=args.mode)


if __name__ == "__main__":
    main()
