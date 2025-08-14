"""
SiteSentinel API Module
Provides REST API endpoints for monitoring, webhook functionality, and alert management
"""

from flask import Blueprint, jsonify, request
import json
import time
import asyncio
from datetime import datetime
from website_monitor.monitor import (
    websites,
    check_websites,
    check_website,
    calculate_health_score
)
from alert_system import alert_manager, AlertMessage, AlertSeverity, AlertType
import threading

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Webhook storage and management
webhooks = {}
webhook_lock = threading.Lock()


@api_bp.route('/websites', methods=['GET'])
def get_all_websites():
    """Get all monitored websites with their status"""
    try:
        website_data = {}
        for url, data in websites.items():
            website_data[url] = {
                **data,
                'health_score': data.get('health_score', {'score': 0, 'grade': 'F'}),
                'ssl': data.get('ssl_info', {}),
                'dns': data.get('dns', {'ip': data.get('ip', 'Unknown')})
            }

        return jsonify({
            'success': True,
            'count': len(website_data),
            'websites': website_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/websites/<path:url>', methods=['GET'])
def get_website(url):
    """Get specific website status"""
    try:
        if url not in websites:
            return jsonify({'success': False, 'error': 'Website not found'}), 404

        data = websites[url]
        return jsonify({
            'success': True,
            'url': url,
            'data': {
                **data,
                'health_score': data.get('health_score', {'score': 0, 'grade': 'F'}),
                'ssl': data.get('ssl_info', {}),
                'dns': data.get('dns', {'ip': data.get('ip', 'Unknown')})
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/websites', methods=['POST'])
def add_website():
    """Add a new website to monitor"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        if url in websites:
            return jsonify({'success': False, 'error': 'Website already exists'}), 409

        # Initialize website data
        websites[url] = {
            'status': 'UNKNOWN',
            'ip': None,
            'status_code': None,
            'response_time': None,
            'error_count': 0,
            'last_check': None,
            'ssl': {},
            'dns': {},
            'health_score': {'score': 0, 'grade': 'F'}
        }

        # Trigger immediate check
        check_website(url)

        return jsonify({
            'success': True,
            'message': f'Website {url} added successfully',
            'url': url,
            'data': websites[url]
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/websites/<path:url>', methods=['DELETE'])
def remove_website(url):
    """Remove website from monitoring"""
    try:
        if url not in websites:
            return jsonify({'success': False, 'error': 'Website not found'}), 404

        del websites[url]
        return jsonify({
            'success': True,
            'message': f'Website {url} removed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/websites/<path:url>/check', methods=['POST'])
def check_website_api(url):
    """Manually trigger check for specific website"""
    try:
        if url not in websites:
            return jsonify({'success': False, 'error': 'Website not found'}), 404

        # Trigger check
        success = check_website(url)

        return jsonify({
            'success': True,
            'url': url,
            'check_successful': success,
            'data': websites[url],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/webhooks', methods=['GET'])
def get_webhooks():
    """Get all registered webhooks"""
    with webhook_lock:
        return jsonify({
            'success': True,
            'webhooks': list(webhooks.keys()),
            'count': len(webhooks)
        })


@api_bp.route('/webhooks', methods=['POST'])
def register_webhook():
    """Register a new webhook"""
    try:
        data = request.get_json()
        webhook_url = data.get('url')
        webhook_name = data.get('name', f'webhook_{int(time.time())}')
        events = data.get('events', ['status_change', 'downtime'])

        if not webhook_url:
            return jsonify({'success': False, 'error': 'Webhook URL is required'}), 400

        with webhook_lock:
            webhooks[webhook_name] = {
                'url': webhook_url,
                'events': events,
                'created': datetime.now().isoformat(),
                'last_triggered': None
            }

        return jsonify({
            'success': True,
            'message': f'Webhook {webhook_name} registered successfully',
            'webhook': webhooks[webhook_name]
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/webhooks/<webhook_name>', methods=['DELETE'])
def unregister_webhook(webhook_name):
    """Unregister a webhook"""
    try:
        with webhook_lock:
            if webhook_name not in webhooks:
                return jsonify({'success': False, 'error': 'Webhook not found'}), 404

            del webhooks[webhook_name]

        return jsonify({
            'success': True,
            'message': f'Webhook {webhook_name} unregistered successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/health', methods=['GET'])
def api_health():
    """API health check endpoint"""
    return jsonify({
        'success': True,
        'service': 'SiteSentinel API',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'monitored_sites': len(websites),
        'active_webhooks': len(webhooks)
    })


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get monitoring statistics"""
    try:
        total_sites = len(websites)
        up_sites = len([url for url, data in websites.items()
                       if data.get('status') == 'UP'])
        down_sites = len([url for url, data in websites.items()
                         if data.get('status') == 'DOWN'])
        unknown_sites = len(
            [url for url, data in websites.items() if data.get('status') == 'UNKNOWN'])

        # Calculate average health score
        health_scores = [data.get('health_score', {}).get(
            'score', 0) for data in websites.values()]
        avg_health_score = sum(health_scores) / \
            len(health_scores) if health_scores else 0

        # SSL statistics
        ssl_valid = len([url for url, data in websites.items()
                        if url.startswith('https://') and data.get('ssl', {}).get('valid')])
        ssl_total = len([url for url in websites.keys()
                        if url.startswith('https://')])

        return jsonify({
            'success': True,
            'stats': {
                'total_sites': total_sites,
                'up_sites': up_sites,
                'down_sites': down_sites,
                'unknown_sites': unknown_sites,
                'uptime_percentage': (up_sites / total_sites * 100) if total_sites > 0 else 0,
                'average_health_score': round(avg_health_score, 2),
                'ssl_coverage': {
                    'valid_certificates': ssl_valid,
                    'total_https_sites': ssl_total,
                    'ssl_percentage': (ssl_valid / ssl_total * 100) if ssl_total > 0 else 0
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def trigger_webhooks(event_type, website_url, website_data):
    """Trigger registered webhooks for specific events"""
    import requests

    with webhook_lock:
        for webhook_name, webhook_info in webhooks.items():
            if event_type in webhook_info['events']:
                try:
                    payload = {
                        'event': event_type,
                        'website': website_url,
                        'data': website_data,
                        'timestamp': datetime.now().isoformat(),
                        'webhook_name': webhook_name
                    }

                    response = requests.post(
                        webhook_info['url'],
                        json=payload,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )

                    webhook_info['last_triggered'] = datetime.now().isoformat()

                    if response.status_code == 200:
                        print(f"Webhook {webhook_name} triggered successfully")
                    else:
                        print(
                            f"Webhook {webhook_name} failed: {response.status_code}")

                except Exception as e:
                    print(f"Error triggering webhook {webhook_name}: {e}")


# Alert Management API Endpoints

@api_bp.route('/alerts/channels', methods=['GET'])
def get_alert_channels():
    """Get status of all alert channels"""
    try:
        return jsonify({
            'success': True,
            'channels': alert_manager.get_channel_status(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/history', methods=['GET'])
def get_alert_history():
    """Get recent alert history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        recent_alerts = alert_manager.get_recent_alerts(limit)

        return jsonify({
            'success': True,
            'count': len(recent_alerts),
            'alerts': recent_alerts,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/test', methods=['POST'])
def send_test_alert():
    """Send a test alert through all configured channels"""
    try:
        data = request.get_json()

        # Create test alert
        test_alert = AlertMessage(
            title=data.get('title', 'SiteSentinel Test Alert'),
            message=data.get(
                'message', 'This is a test alert to verify your notification channels are working correctly.'),
            severity=AlertSeverity(data.get('severity', 'LOW')),
            alert_type=AlertType.ERROR_THRESHOLD,
            website_url=data.get('website_url', 'https://example.com'),
            timestamp=datetime.now(),
            details={
                'test_alert': True,
                'sent_by': 'API',
                'test_time': datetime.now().isoformat()
            }
        )

        # Send alert asynchronously
        async def send_alert():
            return await alert_manager.send_alert(test_alert)

        # Run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(send_alert())

        return jsonify({
            'success': True,
            'message': 'Test alert sent',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/channels/<channel_name>/toggle', methods=['POST'])
def toggle_alert_channel(channel_name):
    """Enable or disable a specific alert channel"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)

        # Find and toggle the channel
        channel_found = False
        for channel in alert_manager.channels:
            if channel.name.lower() == channel_name.lower():
                channel.enabled = enabled
                channel_found = True
                break

        if not channel_found:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404

        return jsonify({
            'success': True,
            'message': f'Channel {channel_name} {"enabled" if enabled else "disabled"}',
            'channel': channel_name,
            'enabled': enabled,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/website/<path:website_url>', methods=['POST'])
def send_website_alert(website_url):
    """Send a custom alert for a specific website"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('title') or not data.get('message'):
            return jsonify({'success': False, 'error': 'Title and message are required'}), 400

        # Create custom alert
        custom_alert = AlertMessage(
            title=data['title'],
            message=data['message'],
            severity=AlertSeverity(data.get('severity', 'MEDIUM')),
            alert_type=AlertType(data.get('alert_type', 'ERROR_THRESHOLD')),
            website_url=website_url,
            timestamp=datetime.now(),
            details=data.get('details', {})
        )

        # Send alert asynchronously
        async def send_alert():
            return await alert_manager.send_alert(custom_alert)

        # Run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(send_alert())

        return jsonify({
            'success': True,
            'message': 'Custom alert sent',
            'website': website_url,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config', methods=['GET'])
def get_alert_config():
    """Get current alert configuration"""
    try:
        import os

        config = {
            'slack': {
                'configured': bool(os.getenv('SLACK_WEBHOOK_URL')),
                'channel': os.getenv('SLACK_CHANNEL', 'Default')
            },
            'discord': {
                'configured': bool(os.getenv('DISCORD_WEBHOOK_URL'))
            },
            'email': {
                'configured': bool(os.getenv('SMTP_SERVER') and os.getenv('SENDER_EMAIL')),
                'server': os.getenv('SMTP_SERVER', 'Not configured'),
                'sender': os.getenv('SENDER_EMAIL', 'Not configured')
            },
            'sms': {
                'configured': bool(os.getenv('TWILIO_ACCOUNT_SID'))
            },
            'teams': {
                'configured': bool(os.getenv('TEAMS_WEBHOOK_URL'))
            },
            'telegram': {
                'configured': bool(os.getenv('TELEGRAM_BOT_TOKEN'))
            }
        }

        return jsonify({
            'success': True,
            'configuration': config,
            'active_channels': len(alert_manager.channels),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/slack', methods=['POST'])
def save_slack_config():
    """Save Slack configuration"""
    try:
        data = request.json
        webhook_url = data.get('webhook_url')
        channel = data.get('channel', '#alerts')

        if not webhook_url:
            return jsonify({'success': False, 'error': 'Webhook URL is required'}), 400

        # Update environment variables (in production, you'd want to update actual config files)
        import os
        os.environ['SLACK_WEBHOOK_URL'] = webhook_url
        os.environ['SLACK_CHANNEL'] = channel

        # Reinitialize alert manager to pick up new config
        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'Slack configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/discord', methods=['POST'])
def save_discord_config():
    """Save Discord configuration"""
    try:
        data = request.json
        webhook_url = data.get('webhook_url')
        username = data.get('username', 'SiteSentinel Bot')

        if not webhook_url:
            return jsonify({'success': False, 'error': 'Webhook URL is required'}), 400

        import os
        os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
        os.environ['DISCORD_USERNAME'] = username

        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'Discord configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/email', methods=['POST'])
def save_email_config():
    """Save Email configuration"""
    try:
        data = request.json
        server = data.get('server')
        port = data.get('port')
        sender = data.get('sender')
        password = data.get('password')
        recipient = data.get('recipient')

        if not all([server, port, sender, password, recipient]):
            return jsonify({'success': False, 'error': 'All email fields are required'}), 400

        import os
        os.environ['SMTP_SERVER'] = server
        os.environ['SMTP_PORT'] = str(port)
        os.environ['SENDER_EMAIL'] = sender
        os.environ['SENDER_PASSWORD'] = password
        os.environ['RECIPIENT_EMAIL'] = recipient

        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'Email configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/sms', methods=['POST'])
def save_sms_config():
    """Save SMS configuration"""
    try:
        data = request.json
        account_sid = data.get('account_sid')
        auth_token = data.get('auth_token')
        from_number = data.get('from_number')
        to_number = data.get('to_number')

        if not all([account_sid, auth_token, from_number, to_number]):
            return jsonify({'success': False, 'error': 'All SMS fields are required'}), 400

        import os
        os.environ['TWILIO_ACCOUNT_SID'] = account_sid
        os.environ['TWILIO_AUTH_TOKEN'] = auth_token
        os.environ['TWILIO_FROM_NUMBER'] = from_number
        os.environ['TWILIO_TO_NUMBER'] = to_number

        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'SMS configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/teams', methods=['POST'])
def save_teams_config():
    """Save Teams configuration"""
    try:
        data = request.json
        webhook_url = data.get('webhook_url')

        if not webhook_url:
            return jsonify({'success': False, 'error': 'Webhook URL is required'}), 400

        import os
        os.environ['TEAMS_WEBHOOK_URL'] = webhook_url

        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'Teams configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/config/telegram', methods=['POST'])
def save_telegram_config():
    """Save Telegram configuration"""
    try:
        data = request.json
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')

        if not all([bot_token, chat_id]):
            return jsonify({'success': False, 'error': 'Bot token and chat ID are required'}), 400

        import os
        os.environ['TELEGRAM_BOT_TOKEN'] = bot_token
        os.environ['TELEGRAM_CHAT_ID'] = chat_id

        alert_manager.initialize_channels()

        return jsonify({
            'success': True,
            'message': 'Telegram configuration saved successfully',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
