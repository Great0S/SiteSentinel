"""
Multi-Channel Alerting System for SiteSentinel
Provides comprehensive alerting through multiple channels including 
Slack, Discord, Email, SMS, Microsoft Teams, and Telegram notifications
"""

import logging
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import aiohttp
from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Types of alerts"""
    WEBSITE_DOWN = "WEBSITE_DOWN"
    WEBSITE_UP = "WEBSITE_UP"
    SLOW_RESPONSE = "SLOW_RESPONSE"
    SSL_EXPIRING = "SSL_EXPIRING"
    DNS_ISSUE = "DNS_ISSUE"
    HEALTH_SCORE_LOW = "HEALTH_SCORE_LOW"
    ERROR_THRESHOLD = "ERROR_THRESHOLD"


@dataclass
class AlertMessage:
    """Alert message structure"""
    title: str
    message: str
    severity: AlertSeverity
    alert_type: AlertType
    website_url: str
    timestamp: datetime
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        data['alert_type'] = self.alert_type.value
        return data


class AlertChannel:
    """Base class for alert channels"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert through this channel"""
        raise NotImplementedError

    def format_message(self, alert: AlertMessage) -> str:
        """Format message for this channel"""
        return f"🚨 {alert.title}\n\n{alert.message}\n\nWebsite: {alert.website_url}\nTime: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class SlackChannel(AlertChannel):
    """Slack webhook alerting"""

    def __init__(self, webhook_url: str, channel: str = None, username: str = "SiteSentinel"):
        super().__init__("Slack")
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert to Slack"""
        try:
            # Severity color mapping
            color_map = {
                AlertSeverity.LOW: "#36a64f",      # Green
                AlertSeverity.MEDIUM: "#ff9500",   # Orange
                AlertSeverity.HIGH: "#ff6b35",     # Red-Orange
                AlertSeverity.CRITICAL: "#ff0000"  # Red
            }

            # Severity emoji mapping
            emoji_map = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🚨",
                AlertSeverity.CRITICAL: "🔥"
            }

            # Create Slack attachment
            attachment = {
                "color": color_map.get(alert.severity, "#ff0000"),
                "title": f"{emoji_map.get(alert.severity, '🚨')} {alert.title}",
                "text": alert.message,
                "fields": [
                    {
                        "title": "Website",
                        "value": alert.website_url,
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": alert.severity.value,
                        "short": True
                    },
                    {
                        "title": "Alert Type",
                        "value": alert.alert_type.value.replace('_', ' ').title(),
                        "short": True
                    },
                    {
                        "title": "Time",
                        "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                        "short": True
                    }
                ],
                "footer": "SiteSentinel Monitor",
                "ts": int(alert.timestamp.timestamp())
            }

            # Add additional details if available
            if alert.details:
                for key, value in alert.details.items():
                    if len(attachment["fields"]) < 10:  # Slack limit
                        attachment["fields"].append({
                            "title": key.replace('_', ' ').title(),
                            "value": str(value),
                            "short": True
                        })

            payload = {
                "username": self.username,
                "attachments": [attachment]
            }

            if self.channel:
                payload["channel"] = self.channel

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(
                            f"Slack alert sent successfully for {alert.website_url}")
                        return True
                    else:
                        logger.error(
                            f"Failed to send Slack alert: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False


class DiscordChannel(AlertChannel):
    """Discord webhook alerting"""

    def __init__(self, webhook_url: str, username: str = "SiteSentinel"):
        super().__init__("Discord")
        self.webhook_url = webhook_url
        self.username = username

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert to Discord"""
        try:
            # Severity color mapping (Discord colors are decimal)
            color_map = {
                AlertSeverity.LOW: 3581519,      # Green
                AlertSeverity.MEDIUM: 16744192,  # Orange
                AlertSeverity.HIGH: 16733525,    # Red-Orange
                AlertSeverity.CRITICAL: 16711680  # Red
            }

            # Create Discord embed
            embed = {
                "title": f"🚨 {alert.title}",
                "description": alert.message,
                "color": color_map.get(alert.severity, 16711680),
                "fields": [
                    {
                        "name": "Website",
                        "value": alert.website_url,
                        "inline": True
                    },
                    {
                        "name": "Severity",
                        "value": alert.severity.value,
                        "inline": True
                    },
                    {
                        "name": "Alert Type",
                        "value": alert.alert_type.value.replace('_', ' ').title(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "SiteSentinel Monitor"
                },
                "timestamp": alert.timestamp.isoformat()
            }

            # Add additional details if available
            if alert.details:
                for key, value in alert.details.items():
                    if len(embed["fields"]) < 25:  # Discord limit
                        embed["fields"].append({
                            "name": key.replace('_', ' ').title(),
                            "value": str(value),
                            "inline": True
                        })

            payload = {
                "username": self.username,
                "embeds": [embed]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:  # Discord returns 204 for success
                        logger.info(
                            f"Discord alert sent successfully for {alert.website_url}")
                        return True
                    else:
                        logger.error(
                            f"Failed to send Discord alert: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False


class EmailChannel(AlertChannel):
    """Email alerting via SMTP"""

    def __init__(self, smtp_server: str, smtp_port: int, username: str,
                 password: str, sender_email: str, recipient_emails: List[str],
                 use_tls: bool = True):
        super().__init__("Email")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.recipient_emails = recipient_emails
        self.use_tls = use_tls

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert via email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[SiteSentinel] {alert.severity.value}: {alert.title}"
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)

            # Create HTML content
            html_content = self._create_html_email(alert)
            text_content = self.format_message(alert)

            # Attach parts
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(
                f"Email alert sent successfully for {alert.website_url}")
            return True

        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

    def _create_html_email(self, alert: AlertMessage) -> str:
        """Create HTML email content"""
        # Severity color mapping
        color_map = {
            AlertSeverity.LOW: "#28a745",      # Green
            AlertSeverity.MEDIUM: "#ffc107",   # Yellow
            AlertSeverity.HIGH: "#fd7e14",     # Orange
            AlertSeverity.CRITICAL: "#dc3545"  # Red
        }

        severity_color = color_map.get(alert.severity, "#dc3545")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SiteSentinel Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .detail-row {{ margin: 10px 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }}
                .detail-label {{ font-weight: bold; color: #333; }}
                .detail-value {{ color: #666; margin-top: 5px; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 {alert.title}</h1>
                    <p style="margin: 0; font-size: 18px;">{alert.severity.value} Alert</p>
                </div>
                <div class="content">
                    <p style="font-size: 16px; line-height: 1.5;">{alert.message}</p>
                    
                    <div class="detail-row">
                        <div class="detail-label">Website:</div>
                        <div class="detail-value"><a href="{alert.website_url}" target="_blank">{alert.website_url}</a></div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="detail-label">Alert Type:</div>
                        <div class="detail-value">{alert.alert_type.value.replace('_', ' ').title()}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="detail-label">Time:</div>
                        <div class="detail-value">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
                    </div>
        """

        # Add additional details if available
        if alert.details:
            for key, value in alert.details.items():
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">{key.replace('_', ' ').title()}:</div>
                        <div class="detail-value">{value}</div>
                    </div>
                """

        html += """
                </div>
                <div class="footer">
                    <p>This alert was generated by SiteSentinel Monitor</p>
                    <p>Visit your dashboard for more details</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html


class SMSChannel(AlertChannel):
    """SMS alerting via Twilio"""

    def __init__(self, account_sid: str, auth_token: str, from_number: str,
                 to_numbers: List[str]):
        super().__init__("SMS")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_numbers = to_numbers

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert via SMS"""
        try:
            client = TwilioClient(self.account_sid, self.auth_token)

            # Create short message for SMS
            message_text = f"🚨 SiteSentinel Alert\n\n{alert.title}\n\nWebsite: {alert.website_url}\nSeverity: {alert.severity.value}\nTime: {alert.timestamp.strftime('%m/%d %H:%M')}"

            # Send to all numbers
            success_count = 0
            for number in self.to_numbers:
                try:
                    message = client.messages.create(
                        body=message_text,
                        from_=self.from_number,
                        to=number
                    )
                    logger.info(f"SMS sent to {number}: {message.sid}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send SMS to {number}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            return False


class TeamsChannel(AlertChannel):
    """Microsoft Teams webhook alerting"""

    def __init__(self, webhook_url: str):
        super().__init__("Teams")
        self.webhook_url = webhook_url

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert to Microsoft Teams"""
        try:
            # Create Teams message card
            card = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_theme_color(alert.severity),
                "summary": alert.title,
                "sections": [
                    {
                        "activityTitle": f"🚨 {alert.title}",
                        "activitySubtitle": f"{alert.severity.value} Alert",
                        "activityImage": "https://raw.githubusercontent.com/SiteSentinel/assets/main/logo.png",
                        "facts": [
                            {"name": "Website", "value": alert.website_url},
                            {"name": "Alert Type", "value": alert.alert_type.value.replace(
                                '_', ' ').title()},
                            {"name": "Severity", "value": alert.severity.value},
                            {"name": "Time", "value": alert.timestamp.strftime(
                                '%Y-%m-%d %H:%M:%S UTC')}
                        ],
                        "text": alert.message
                    }
                ],
                "potentialAction": [
                    {
                        "@type": "OpenUri",
                        "name": "View Website",
                        "targets": [
                            {"os": "default", "uri": alert.website_url}
                        ]
                    }
                ]
            }

            # Add additional details if available
            if alert.details:
                for key, value in alert.details.items():
                    if len(card["sections"][0]["facts"]) < 10:  # Reasonable limit
                        card["sections"][0]["facts"].append({
                            "name": key.replace('_', ' ').title(),
                            "value": str(value)
                        })

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=card) as response:
                    if response.status == 200:
                        logger.info(
                            f"Teams alert sent successfully for {alert.website_url}")
                        return True
                    else:
                        logger.error(
                            f"Failed to send Teams alert: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error sending Teams alert: {e}")
            return False

    def _get_theme_color(self, severity: AlertSeverity) -> str:
        """Get Teams theme color for severity"""
        color_map = {
            AlertSeverity.LOW: "00FF00",      # Green
            AlertSeverity.MEDIUM: "FFA500",   # Orange
            AlertSeverity.HIGH: "FF4500",     # Red-Orange
            AlertSeverity.CRITICAL: "FF0000"  # Red
        }
        return color_map.get(severity, "FF0000")


class TelegramChannel(AlertChannel):
    """Telegram bot alerting"""

    def __init__(self, bot_token: str, chat_ids: List[str]):
        super().__init__("Telegram")
        self.bot_token = bot_token
        self.chat_ids = chat_ids

    async def send_alert(self, alert: AlertMessage) -> bool:
        """Send alert to Telegram"""
        try:
            # Create formatted message with emoji
            emoji_map = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🚨",
                AlertSeverity.CRITICAL: "🔥"
            }

            emoji = emoji_map.get(alert.severity, "🚨")
            message_text = f"{emoji} *SiteSentinel Alert*\n\n"
            message_text += f"*{alert.title}*\n\n"
            message_text += f"{alert.message}\n\n"
            message_text += f"🌐 *Website:* {alert.website_url}\n"
            message_text += f"⚡ *Severity:* {alert.severity.value}\n"
            message_text += f"📅 *Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            message_text += f"🏷️ *Type:* {alert.alert_type.value.replace('_', ' ').title()}"

            # Add additional details if available
            if alert.details:
                message_text += "\n\n*Details:*\n"
                for key, value in alert.details.items():
                    message_text += f"• {key.replace('_', ' ').title()}: {value}\n"

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            success_count = 0
            for chat_id in self.chat_ids:
                try:
                    payload = {
                        "chat_id": chat_id,
                        "text": message_text,
                        "parse_mode": "Markdown"
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload) as response:
                            if response.status == 200:
                                logger.info(
                                    f"Telegram alert sent to chat {chat_id}")
                                success_count += 1
                            else:
                                logger.error(
                                    f"Failed to send Telegram alert to {chat_id}: {response.status}")
                except Exception as e:
                    logger.error(
                        f"Error sending Telegram alert to {chat_id}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False


class AlertManager:
    """Main alert management system"""

    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.alert_history: List[AlertMessage] = []
        self.max_history = 1000

        # Load configuration from environment variables
        self._load_configuration()

    def _load_configuration(self):
        """Load alert channel configuration from environment variables"""
        try:
            # Slack configuration
            slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
            if slack_webhook:
                slack_channel = SlackChannel(
                    webhook_url=slack_webhook,
                    channel=os.getenv('SLACK_CHANNEL'),
                    username=os.getenv('SLACK_USERNAME', 'SiteSentinel')
                )
                self.add_channel(slack_channel)
                logger.info("Slack alerting configured")

            # Discord configuration
            discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
            if discord_webhook:
                discord_channel = DiscordChannel(
                    webhook_url=discord_webhook,
                    username=os.getenv('DISCORD_USERNAME', 'SiteSentinel')
                )
                self.add_channel(discord_channel)
                logger.info("Discord alerting configured")

            # Email configuration
            smtp_server = os.getenv('SMTP_SERVER')
            if smtp_server:
                email_channel = EmailChannel(
                    smtp_server=smtp_server,
                    smtp_port=int(os.getenv('SMTP_PORT', '587')),
                    username=os.getenv('SMTP_USERNAME'),
                    password=os.getenv('SMTP_PASSWORD'),
                    sender_email=os.getenv('SENDER_EMAIL'),
                    recipient_emails=os.getenv(
                        'RECIPIENT_EMAILS', '').split(','),
                    use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
                )
                self.add_channel(email_channel)
                logger.info("Email alerting configured")

            # SMS configuration (Twilio)
            twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
            if twilio_sid:
                sms_channel = SMSChannel(
                    account_sid=twilio_sid,
                    auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
                    from_number=os.getenv('TWILIO_FROM_NUMBER'),
                    to_numbers=os.getenv('SMS_TO_NUMBERS', '').split(',')
                )
                self.add_channel(sms_channel)
                logger.info("SMS alerting configured")

            # Teams configuration
            teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
            if teams_webhook:
                teams_channel = TeamsChannel(webhook_url=teams_webhook)
                self.add_channel(teams_channel)
                logger.info("Teams alerting configured")

            # Telegram configuration
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if telegram_token:
                telegram_channel = TelegramChannel(
                    bot_token=telegram_token,
                    chat_ids=os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
                )
                self.add_channel(telegram_channel)
                logger.info("Telegram alerting configured")

        except Exception as e:
            logger.error(f"Error loading alert configuration: {e}")

    def add_channel(self, channel: AlertChannel):
        """Add an alert channel"""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {channel.name}")

    def remove_channel(self, channel_name: str):
        """Remove an alert channel"""
        self.channels = [ch for ch in self.channels if ch.name != channel_name]
        logger.info(f"Removed alert channel: {channel_name}")

    def initialize_channels(self):
        """Reinitialize all channels with current environment variables"""
        # Clear existing channels
        self.channels.clear()
        logger.info("Reinitializing alert channels...")

        # Reload configuration
        self._load_configuration()

        logger.info(f"Reinitialized {len(self.channels)} alert channels")

    async def send_alert(self, alert: AlertMessage) -> Dict[str, bool]:
        """Send alert through all configured channels"""
        results = {}

        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]

        logger.info(
            f"Sending {alert.severity.value} alert: {alert.title} for {alert.website_url}")

        # Send through all enabled channels
        for channel in self.channels:
            if channel.enabled:
                try:
                    success = await channel.send_alert(alert)
                    results[channel.name] = success
                    if success:
                        logger.info(
                            f"Alert sent successfully via {channel.name}")
                    else:
                        logger.error(
                            f"Failed to send alert via {channel.name}")
                except Exception as e:
                    logger.error(
                        f"Error sending alert via {channel.name}: {e}")
                    results[channel.name] = False

        return results

    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured channels"""
        status = {}
        for channel in self.channels:
            status[channel.name] = {
                'enabled': channel.enabled,
                'type': type(channel).__name__
            }
        return status

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        recent = self.alert_history[-limit:] if limit else self.alert_history
        return [alert.to_dict() for alert in reversed(recent)]


# Global alert manager instance
alert_manager = AlertManager()
