import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration class for Site Sentinel application"""

    # Flask settings
    DEBUG: bool = True
    HOST: str = '0.0.0.0'
    PORT: int = 5000
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # Monitoring settings
    CHECK_INTERVAL: int = int(os.getenv('CHECK_INTERVAL', 300))  # 5 minutes
    ERROR_THRESHOLD: int = int(os.getenv('ERROR_THRESHOLD', 3))
    RETRY_COUNT: int = int(os.getenv('RETRY_COUNT', 3))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', 10))
    SCREENSHOT_CACHE_DURATION: int = int(
        os.getenv('SCREENSHOT_CACHE_DURATION', 3600))  # 1 hour

    # Email settings
    EMAIL_SERVER: str = os.getenv('EMAIL_SERVER', '')
    EMAIL_PORT: int = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_SENDER: str = os.getenv('EMAIL_SENDER', '')
    EMAIL_PASSWORD: str = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_RECEIVER: str = os.getenv('EMAIL_RECEIVER', '')
    EMAIL_USE_TLS: bool = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'

    # File paths
    EXCEL_FILE: str = os.getenv('EXCEL_FILE', 'domainler.xlsx')
    METADATA_FILE: str = os.getenv('METADATA_FILE', 'metadata.json')
    SCREENSHOTS_DIR: str = os.getenv('SCREENSHOTS_DIR', 'screenshots')

    # PDF settings
    WKHTMLTOPDF_PATH: str = os.getenv(
        'WKHTMLTOPDF_PATH', 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE', None)

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.CHECK_INTERVAL < 60:
            raise ValueError("CHECK_INTERVAL must be at least 60 seconds")
        if self.ERROR_THRESHOLD < 1:
            raise ValueError("ERROR_THRESHOLD must be at least 1")
        if self.RETRY_COUNT < 1:
            raise ValueError("RETRY_COUNT must be at least 1")


# Global configuration instance
config = Config()
