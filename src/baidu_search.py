"""
百度搜索招标信息爬虫
"""

import requests
import urllib3
import ssl
import re
from bs4 import BeautifulSoup
from typing import List, Dict
import logging

# 跳过 SSL 验证
urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)


class BaiduSearchCrawler:
    """通过百度搜索获取招标信息"""

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def search(self, keywords: List[str], num: int = 10) -> List[Dict]:
        """搜索招标信息"""
        results = []
        keyword = ' '.join(keywords)

        try:
            # 百度搜索
            url = 'https://www.baidu.com/s'
            params = {
                'wd': f'{keyword} 招标 公告 拆除 拆迁',
                'rn': num,
                'ie': 'utf-8'
            }

            resp = self.session.get(url, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 解析搜索结果
            for item in soup.select('div.result'):
                try:
                    title_elem = item.select_one('h3 a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')

                    # 跳过新闻和帖子
                    skip_patterns = ['网易', '搜狐', '腾讯', '凤凰网', '新浪', '头条', '百家号', '澎湃']
                    if any(p in title for p in skip_patterns):
                        continue

                    # 提取摘要
                    abstract = ''
                    abs_elem = item.select_one('div.span-desc')
                    if abs_elem:
                        abstract = abs_elem.get_text(strip=True)

                    # 提取金额
                    amount = self._extract_amount(title + abstract)

                    # 提取日期
                    date = ''
                    date_elem = item.select_one('div span.newTimeFactor_before_abs')
                    if date_elem:
                        date = date_elem.get_text(strip=True)

                    # 过滤：只保留包含招标相关关键词的结果
                    tender_keywords = ['招标', '采购', '公告', '投标', '拆除', '拆迁', '改造', '工程']
                    if not any(k in title for k in tender_keywords):
                        continue

                    result = {
                        'title': title,
                        'url': url_link,
                        'source': '百度搜索',
                        'publish_date': date,
                        'amount': amount,
                        'deadline': '',
                        'region': self._extract_region(title),
                        'industry': ' | '.join(keywords),
                        'abstract': abstract[:200]
                    }
                    results.append(result)

                except Exception as e:
                    continue

            logger.info(f"百度搜索到 {len(results)} 条结果")

        except Exception as e:
            logger.error(f"百度搜索失败: {e}")

        return results

    def _extract_amount(self, text: str) -> str:
        """提取金额"""
        patterns = [
            r'(\d+\.?\d*)\s*[亿万]',
            r'预算[金额：:]\s*(\d+\.?\d*)\s*[万]',
            r'最高限价[：:]\s*(\d+\.?\d*)',
            r'招标控制价[：:]\s*(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}万"
        return ''

    def _extract_region(self, text: str) -> str:
        """提取地区"""
        regions = ['温州市', '龙湾区', '瓯海区', '鹿城区', '瑞安市', '乐清市', '永嘉县',
                    '杭州市', '宁波市', '嘉兴市', '湖州市', '绍兴市', '金华市',
                    '衢州市', '舟山市', '台州市', '丽水市', '浙江省', '全国',
                    '北京', '上海', '广州', '深圳', '成都', '武汉', '西安']
        for region in regions:
            if region in text:
                return region
        return '全国'


def crawl_tenders(keywords: List[str] = None) -> List[Dict]:
    """爬取招标信息"""
    if keywords is None:
        keywords = ['拆迁', '拆除', '房屋拆迁', '旧城改造', '棚户区改造']

    crawler = BaiduSearchCrawler()
    return crawler.search(keywords, num=10)


if __name__ == '__main__':
    results = crawl_tenders()
    print(f"\n搜索到 {len(results)} 条招标信息:\n")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r['title']}")
        print(f"   金额: {r['amount'] or '待确认'} | 地区: {r['region']}")
        print()
