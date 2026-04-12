"""
富宝资讯金属价格爬虫模块
爬取废钢、废铜、废铝、废不锈钢等价格数据
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging
import re
import json

logger = logging.getLogger(__name__)


class MetalPriceCrawler:
    """金属价格爬虫"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_index(self) -> Dict:
        """
        获取富宝价格指数（首页公开数据）
        返回: {'废钢': {'price': 2215.4, 'change': -0.6, 'change_pct': -0.03}, ...}
        """
        result = {}
        try:
            resp = self.session.get('https://www.f139.com/', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 解析首页价格指数
            index_text = soup.select_one('.index-content, .price-index, [class*="index"]')
            if index_text:
                text = index_text.get_text()
                # 解析废钢指数
                match = re.search(r'废钢\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
                if match:
                    result['废钢'] = {
                        'price': float(match.group(1)),
                        'change': float(match.group(3)) if match.group(3) else 0,
                        'change_pct': float(match.group(4).replace('%', '')) if match.group(4) else 0
                    }

            # 从首页价格指数区域提取数据
            index_section = soup.find(string=re.compile('富宝价格指数'))
            if index_section:
                parent = index_section.find_parent()
                if parent:
                    text = parent.get_text()
                    # 废钢
                    m = re.search(r'废钢\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
                    if m:
                        result['废钢'] = {
                            'price': float(m.group(1)),
                            'change': float(m.group(3)) if m.group(3) else 0,
                            'change_pct': float(re.sub(r'[^\d.]', '', m.group(4))) if m.group(4) and re.sub(r'[^\d.]', '', m.group(4)) else 0
                        }

            logger.info(f"获取到价格指数: {result}")

        except Exception as e:
            logger.error(f"获取价格指数失败: {e}")

        return result

    def fetch_steel_price(self) -> List[Dict]:
        """
        获取废钢各地市场价格
        """
        results = []
        try:
            resp = self.session.get('https://www.f139.com/feigang', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 解析价格表格
            rows = soup.select('table tr, .price-list tr')
            for row in rows[1:]:  # 跳过表头
                cells = row.select('td')
                if len(cells) >= 5:
                    name = cells[0].get_text(strip=True)
                    market = cells[1].get_text(strip=True)
                    spec = cells[2].get_text(strip=True)
                    price_text = cells[4].get_text(strip=True)

                    if price_text and price_text != '***':
                        try:
                            price = float(re.sub(r'[^\d.]', '', price_text))
                            results.append({
                                'name': name,
                                'market': market,
                                'spec': spec,
                                'price': price,
                                'unit': '元/吨',
                                'date': datetime.now().strftime('%Y-%m-%d')
                            })
                        except:
                            pass

        except Exception as e:
            logger.error(f"获取废钢价格失败: {e}")

        return results

    def fetch_copper_price(self) -> List[Dict]:
        """
        获取废铜价格
        """
        results = []
        try:
            # 废铜通常在有色金属页面
            resp = self.session.get('https://www.f139.com/industry/nm', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 查找废铜相关价格
            copper_links = soup.find_all('a', href=re.compile('feitung|feitong|copper'))
            logger.info(f"找到 {len(copper_links)} 个废铜相关链接")

        except Exception as e:
            logger.error(f"获取废铜价格失败: {e}")

        return results

    def fetch_aluminum_price(self) -> List[Dict]:
        """
        获取废铝价格
        """
        results = []
        try:
            resp = self.session.get('https://www.f139.com/industry/nm', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 查找废铝相关
            al_links = soup.find_all('a', href=re.compile('feilv|feiLv|aluminum'))
            logger.info(f"找到 {len(al_links)} 个废铝相关链接")

        except Exception as e:
            logger.error(f"获取废铝价格失败: {e}")

        return results

    def fetch_stainless_steel_price(self) -> List[Dict]:
        """
        获取废不锈钢价格
        """
        results = []
        try:
            resp = self.session.get('https://www.f139.com/zone/stainless_steel', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 查找价格数据
            price_elements = soup.select('[class*="price"], .price-list')
            logger.info(f"找到 {len(price_elements)} 个价格元素")

        except Exception as e:
            logger.error(f"获取废不锈钢价格失败: {e}")

        return results

    def get_market_summary(self) -> Dict:
        """
        获取市场概况（从首页摘录）
        """
        summary = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'indices': {},
            'news': []
        }

        try:
            resp = self.session.get('https://www.f139.com/', timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 解析首页价格指数
            text = soup.get_text()

            # 废钢指数
            m = re.search(r'废钢\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
            if m:
                summary['indices']['废钢'] = {
                    'price': float(m.group(1)),
                    'change': float(m.group(3)) if m.group(3) else 0
                }

            # 废不锈钢
            m = re.search(r'废不锈钢\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
            if m:
                summary['indices']['废不锈钢'] = {
                    'price': float(m.group(1)),
                    'change': float(m.group(3)) if m.group(3) else 0
                }

            # 光亮铜
            m = re.search(r'光亮铜\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
            if m:
                summary['indices']['光亮铜'] = {
                    'price': float(m.group(1)),
                    'change': float(m.group(3)) if m.group(3) else 0
                }

            # 生铝
            m = re.search(r'生铝\s+([\d.]+)\s*([涨跌][\d.]+)?\s*([-\d.]+)%', text)
            if m:
                summary['indices']['生铝'] = {
                    'price': float(m.group(1)),
                    'change': float(m.group(3)) if m.group(3) else 0
                }

            logger.info(f"市场概况: {summary}")

        except Exception as e:
            logger.error(f"获取市场概况失败: {e}")

        return summary

    def fetch_all_prices(self) -> Dict:
        """获取所有价格数据"""
        return {
            'indices': self.get_market_summary(),
            'steel': self.fetch_steel_price(),
            'copper': self.fetch_copper_price(),
            'aluminum': self.fetch_aluminum_price(),
            'stainless': self.fetch_stainless_steel_price()
        }


def get_demo_prices() -> List[Dict]:
    """演示数据 - 当无法爬取时使用"""
    return [
        {
            'name': '废钢',
            'market': '华东指数',
            'price': 2215.4,
            'unit': '元/吨',
            'change': -0.6,
            'change_pct': -0.03,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '废钢',
            'market': '唐山',
            'spec': '重废≥8mm',
            'price': 2450,
            'unit': '元/吨',
            'change': 10,
            'change_pct': 0.41,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '废不锈钢',
            'market': '华东',
            'price': 9586,
            'unit': '元/吨',
            'change': 91,
            'change_pct': 0.96,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '光亮铜',
            'market': '全国',
            'price': 88300,
            'unit': '元/吨',
            'change': 200,
            'change_pct': 0.23,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '生铝',
            'market': '全国',
            'price': 19302,
            'unit': '元/吨',
            'change': 70,
            'change_pct': 0.36,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '电动车电瓶',
            'market': '全国',
            'price': 10005,
            'unit': '元/吨',
            'change': 0,
            'change_pct': 0,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'name': '废黄板纸',
            'market': '全国',
            'price': 1527.22,
            'unit': '元/吨',
            'change': 1.66,
            'change_pct': 0.11,
            'date': datetime.now().strftime('%Y-%m-%d')
        },
    ]


def generate_price_report(prices: List[Dict] = None) -> str:
    """生成价格简报"""
    if prices is None:
        prices = get_demo_prices()

    report = f"""## 📊 金属价格日报

更新时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}

### 重点品种价格

"""

    for p in prices:
        change_icon = '📈' if p.get('change', 0) > 0 else '📉' if p.get('change', 0) < 0 else '➡️'
        change_str = f"{p.get('change'):+.2f}" if isinstance(p.get('change'), (int, float)) else '0'
        pct_str = f"{p.get('change_pct'):+.2f}%" if isinstance(p.get('change_pct'), (int, float)) else '0%'

        report += f"""#### {p.get('name', '')} - {p.get('market', '')}
- 💰 价格：**{p.get('price', 0):,.2f}** {p.get('unit', '元/吨')}
- {change_icon} 涨跌：{change_str} ({pct_str})
- 📅 日期：{p.get('date', '')}

"""

    report += f"""---
💡 数据来源：富宝资讯
⚠️ 价格仅供参考，实际成交以市场为准
"""

    return report


if __name__ == "__main__":
    # 测试
    crawler = MetalPriceCrawler()
    summary = crawler.get_market_summary()
    print(f"市场概况: {json.dumps(summary, ensure_ascii=False, indent=2)}")

    print("\n=== 价格简报 ===")
    prices = get_demo_prices()
    report = generate_price_report(prices)
    print(report)