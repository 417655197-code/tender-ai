"""
招标推送通知模块
支持邮件、微信、钉钉通知
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知"""

    def __init__(self, config: Dict):
        self.smtp_host = config.get('smtp_host', 'smtp.163.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user', '')
        self.smtp_password = config.get('smtp_password', '')
        self.from_name = config.get('from_name', 'TenderAI')

    def send(self, to_email: str, subject: str, content: str) -> bool:
        """发送邮件"""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("邮件配置不完整，跳过发送")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.smtp_user}>"
            msg['To'] = to_email

            # HTML邮件内容
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #1890ff; color: white; padding: 20px; text-align: center;">
                    <h2>📋 TenderAI 招标简报</h2>
                    <p>{datetime.now().strftime('%Y年%m月%d日')}</p>
                </div>
                <div style="padding: 20px; background: #f8f8f8;">
                    {content}
                </div>
                <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
                    <p>由 TenderAI 自动生成 | 退订请联系管理员</p>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(content, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            # 发送
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, [to_email], msg.as_string())
            server.quit()

            logger.info(f"邮件已发送至 {to_email}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def send_daily_report(self, to_email: str, tenders: List[Dict], report_content: str) -> bool:
        """发送每日简报"""
        subject = f"📋 {datetime.now().strftime('%Y年%m月%d日')} 招标简报 - {len(tenders)}条新招标"
        return self.send(to_email, subject, report_content)


class WeChatNotifier:
    """微信通知（通过企业微信/钉钉 webhook）"""

    def __init__(self, config: Dict):
        self.webhook_url = config.get('wechat_webhook', '')
        self.enabled = bool(self.webhook_url)

    def send(self, content: str) -> bool:
        """发送微信消息"""
        if not self.enabled:
            logger.info("微信webhook未配置，跳过")
            return False

        try:
            import requests

            # 构造消息（markdown格式）
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }

            resp = requests.post(self.webhook_url, json=data, timeout=10)
            result = resp.json()

            if result.get('errcode') == 0:
                logger.info("微信消息发送成功")
                return True
            else:
                logger.error(f"微信发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"微信发送异常: {e}")
            return False


class TenderNotifier:
    """招标通知综合管理"""

    def __init__(self, config: Dict):
        self.email = EmailNotifier(config.get('email', {}))
        self.wechat = WeChatNotifier(config.get('wechat', {}))
        self.subscribers = config.get('subscribers', [])

    def notify(self, tenders: List[Dict], report_content: str) -> Dict:
        """向所有订阅者发送通知"""
        results = {
            'email': {'success': 0, 'failed': 0},
            'wechat': {'success': 0, 'failed': 0}
        }

        # 发送邮件
        for subscriber in self.subscribers:
            email = subscriber.get('email')
            if email and self.email.send_daily_report(email, tenders, report_content):
                results['email']['success'] += 1
            else:
                results['email']['failed'] += 1

        # 发送微信
        if self.wechat.enabled:
            if self.wechat.send(report_content):
                results['wechat']['success'] = len(self.subscribers)
            else:
                results['wechat']['failed'] = len(self.subscribers)

        return results


def demo_notify():
    """演示：发送测试通知"""
    from analyzer import generate_daily_report, demo_data

    config = {
        'email': {
            'smtp_host': 'smtp.163.com',
            'smtp_user': 'your_email@163.com',
            'smtp_password': 'your_password'
        },
        'subscribers': [
            {'email': 'test@example.com', 'name': '测试用户'}
        ]
    }

    notifier = TenderNotifier(config)
    tenders = demo_data()
    report = generate_daily_report(tenders)

    print("=== 通知演示 ===")
    print(f"简报内容预览：\n{report[:500]}...")
    print(f"\n将发送给 {len(config['subscribers'])} 位订阅者")


if __name__ == "__main__":
    demo_notify()
