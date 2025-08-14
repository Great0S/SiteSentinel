"""
Test script for SiteSentinel Multi-Channel Alert System
Run this script to test the alert functionality
"""

from alert_system import alert_manager, AlertMessage, AlertSeverity, AlertType
import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_alert_system():
    """Test the multi-channel alert system"""
    print("🚨 Testing SiteSentinel Alert System")
    print("=" * 50)

    # Check configured channels
    print(f"📡 Configured channels: {len(alert_manager.channels)}")
    for channel in alert_manager.channels:
        print(
            f"   - {channel.name}: {'Enabled' if channel.enabled else 'Disabled'}")

    if len(alert_manager.channels) == 0:
        print("\n❌ No alert channels configured!")
        print("📋 To configure alert channels, set environment variables:")
        print("   - SLACK_WEBHOOK_URL for Slack")
        print("   - DISCORD_WEBHOOK_URL for Discord")
        print("   - SMTP_SERVER + SENDER_EMAIL for Email")
        print("   - TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN for SMS")
        print("   - TEAMS_WEBHOOK_URL for Microsoft Teams")
        print("   - TELEGRAM_BOT_TOKEN for Telegram")
        print("\n📖 Check .env.example for detailed configuration instructions")
        return

    print(
        f"\n📤 Sending test alert to {len(alert_manager.channels)} channels...")

    # Create test alert
    test_alert = AlertMessage(
        title="🧪 SiteSentinel Test Alert",
        message="This is a test alert to verify your notification channels are working correctly. If you receive this message, your alert system is properly configured!",
        severity=AlertSeverity.MEDIUM,
        alert_type=AlertType.ERROR_THRESHOLD,
        website_url="https://example.com",
        timestamp=datetime.now(),
        details={
            'test_alert': True,
            'system': 'SiteSentinel',
            'version': '1.3.0',
            'test_time': datetime.now().isoformat(),
            'configured_channels': len(alert_manager.channels)
        }
    )

    # Send test alert
    try:
        results = await alert_manager.send_alert(test_alert)

        print("\n📊 Alert Results:")
        print("-" * 30)

        success_count = 0
        for channel_name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"   {channel_name}: {status}")
            if success:
                success_count += 1

        print(
            f"\n📈 Summary: {success_count}/{len(results)} channels successful")

        if success_count > 0:
            print(
                "🎉 Alert system is working! Check your configured channels for the test message.")
        else:
            print(
                "⚠️  No alerts were sent successfully. Check your configuration and network connectivity.")

    except Exception as e:
        print(f"❌ Error testing alert system: {e}")


def main():
    """Main function"""
    print("SiteSentinel Alert System Test")
    print("===============================\n")

    # Check if environment variables are set
    env_vars = [
        'SLACK_WEBHOOK_URL',
        'DISCORD_WEBHOOK_URL',
        'SMTP_SERVER',
        'TWILIO_ACCOUNT_SID',
        'TEAMS_WEBHOOK_URL',
        'TELEGRAM_BOT_TOKEN'
    ]

    configured_vars = [var for var in env_vars if os.getenv(var)]

    print(f"🔧 Environment check:")
    print(
        f"   - {len(configured_vars)}/{len(env_vars)} alert channels have environment variables set")

    if len(configured_vars) == 0:
        print("\n⚠️  No alert channels are configured via environment variables.")
        print("   The alert system will initialize but no channels will be available.")

    print("\n🚀 Starting alert test...\n")

    # Run the async test
    try:
        asyncio.run(test_alert_system())
    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    main()
