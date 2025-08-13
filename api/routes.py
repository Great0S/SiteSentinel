"""
SiteSentinel API Module
Provides REST API endpoints for monitoring and webhook functionality
"""

from flask import Blueprint, jsonify, request
import json
import time
from datetime import datetime
from website_monitor.monitor import websites, check_website, calculate_health_score
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
                'ssl': data.get('ssl', {}),
                'dns': data.get('dns', {})
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
                'ssl': data.get('ssl', {}),
                'dns': data.get('dns', {})
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
