"""
招标信息爬虫模块
支持多数据源抓取
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class TenderCrawler:
    """招标信息爬虫"""

    def __init__(self, config: Dict):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_ccgp(self, keywords: List[str], days: int = 7) -> List[Dict]:
        """
        中国政府采购网 (ccgp.gov.cn)
        """
        results = []
        base_url = "https://www.ccgp.gov.cn"

        try:
            # 搜索页面
            url = f"{base_url}/search/search.html"
            params = {
                'keyword': ' '.join(keywords),
                'channel': 'cggg',
                'searchfield': 'title',
                'timer': days
            }

            resp = self.session.get(url, params=params, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            items = soup.select('.list .item')
            for item in items[:20]:  # 取前20条
                title_elem = item.select_one('.title a')
                if not title_elem:
                    continue

                tender = {
                    'title': title_elem.get_text(strip=True),
                    'url': title_elem.get('href', ''),
                    'source': '中国政府采购网',
                    'publish_date': item.select_one('.date').get_text(strip=True) if item.select_one('.date') else '',
                    'amount': self._extract_amount(item.get_text()),
                    'deadline': '',
                    'region': '全国',
                    'industry': ' | '.join(keywords)
                }
                results.append(tender)

        except Exception as e:
            logger.error(f"CCGP crawl error: {e}")

        return results

    def fetch_zjzfcg(self, keywords: List[str], days: int = 7) -> List[Dict]:
        """
        浙江省政府采购网
        """
        results = []
        # TODO: 接入浙江省政府采购网API或页面
        logger.info("浙江省政府采购网接入...")
        return results

    def fetch_wzcgg(self, keywords: List[str], days: int = 7) -> List[Dict]:
        """
        温州市政府采购
        """
        results = []
        # TODO: 接入温州市公共资源交易网
        logger.info("温州市公共资源交易网接入...")
        return results

    def _extract_amount(self, text: str) -> Optional[str]:
        """从文本中提取金额"""
        import re
        patterns = [
            r'(\d+\.?\d*)\s*[万亿元]',
            r'预算[金额：:]\s*(\d+\.?\d*)\s*[万亿元]',
            r'最高限价[：:]\s*(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}万"
        return None

    def fetch_all(self, keywords: List[str], days: int = 7) -> List[Dict]:
        """并行抓取所有数据源"""
        all_results = []
        sources = [
            ('ccgp', self.fetch_ccgp),
            ('zjzfcg', self.fetch_zjzfcg),
            ('wzcgg', self.fetch_wzcgg),
        ]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func, keywords, days): name for name, func in sources}
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"Source {futures[future]} error: {e}")

        # 按日期排序
        all_results.sort(key=lambda x: x.get('publish_date', ''), reverse=True)
        return all_results


def demo_data() -> List[Dict]:
    """演示数据 - 拆迁拆除相关招标"""
    return [
        {
            'title': '温州市鹿城区2024年城中村改造项目第三方拆除工程招标公告',
            'url': 'https://example.com/tender/1',
            'source': '温州市公共资源交易网',
            'publish_date': '2024-04-10',
            'amount': '4800万',
            'deadline': '2024-05-08',
            'region': '温州市鹿城区',
            'industry': '城中村改造',
            'summary': '涉及鹿城区3个村约1200户，拆除面积约15万平方米...'
        },
        {
            'title': '龙湾区某工业园房屋征收拆除工程',
            'url': 'https://example.com/tender/2',
            'source': '温州市龙湾区人民政府',
            'publish_date': '2024-04-09',
            'amount': '2200万',
            'deadline': '2024-04-30',
            'region': '温州市龙湾区',
            'industry': '房屋征收拆除',
            'summary': '工业园内15栋厂房拆除，含废墟清运和土地平整...'
        },
        {
            'title': '瓯海区违法建筑强制拆除服务采购项目',
            'url': 'https://example.com/tender/3',
            'source': '浙江省政府采购网',
            'publish_date': '2024-04-08',
            'amount': '680万',
            'deadline': '2024-05-01',
            'region': '温州市瓯海区',
            'industry': '违建拆除',
            'summary': '对瓯海区内违法建筑进行拆除，涉及违建点位约80处...'
        },
        {
            'title': '温州高铁新城棚户区改造房屋拆除工程',
            'url': 'https://example.com/tender/4',
            'source': '温州市公共资源交易网',
            'publish_date': '2024-04-07',
            'amount': '3500万',
            'deadline': '2024-05-15',
            'region': '温州市瓯海区',
            'industry': '棚户区改造',
            'summary': '高铁新城棚改项目，涉及居民约800户，拆除面积约9万平方米...'
        },
        {
            'title': '浙江省某市2024年度征收拆除评估服务入围招标',
            'url': 'https://example.com/tender/5',
            'source': '浙江省政府采购网',
            'publish_date': '2024-04-06',
            'amount': '1200万',
            'deadline': '2024-04-28',
            'region': '浙江省',
            'industry': '征收拆除评估',
            'summary': '入围3-5家拆除评估机构，服务期2年...'
        },
        {
            'title': '乐清市某镇农村宅基地房屋拆迁项目',
            'url': 'https://example.com/tender/6',
            'source': '乐清市人民政府',
            'publish_date': '2024-04-05',
            'amount': '5600万',
            'deadline': '2024-05-10',
            'region': '温州市乐清市',
            'industry': '宅基地拆迁',
            'summary': '涉及某镇5个村约1500户农户房屋拆迁，含安置补偿...'
        },
        {
            'title': '温州市区建筑垃圾（废墟）清运处置服务项目',
            'url': 'https://example.com/tender/7',
            'source': '温州市环卫局',
            'publish_date': '2024-04-04',
            'amount': '850万',
            'deadline': '2024-04-25',
            'region': '温州市',
            'industry': '废墟清运',
            'summary': '市区拆迁项目产生的建筑垃圾清运处置，年清运量约50万吨...'
        },
        {
            'title': '瑞安市旧城改造房屋征收拆除工程（二期）',
            'url': 'https://example.com/tender/8',
            'source': '瑞安市公共资源交易中心',
            'publish_date': '2024-04-03',
            'amount': '2800万',
            'deadline': '2024-05-05',
            'region': '温州市瑞安市',
            'industry': '旧城改造',
            'summary': '瑞安旧城核心区改造二期，涉及居民约600户...'
        },
    ]


if __name__ == "__main__":
    # 测试
    crawler = TenderCrawler({})
    data = demo_data()
    print(f"获取到 {len(data)} 条招标信息")
    for item in data[:2]:
        print(f"- {item['title']} ({item['amount']})")
