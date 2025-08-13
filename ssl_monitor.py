"""
SSL Certificate Monitoring Module for SiteSentinel
Provides comprehensive SSL certificate checking and validation
"""

import ssl
import socket
import datetime
import logging
from urllib.parse import urlparse
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SSLMonitor:
    """SSL Certificate monitoring and analysis"""
    
    @staticmethod
    def check_ssl_certificate(url: str) -> Dict:
        """
        Check SSL certificate for a given URL
        
        Args:
            url (str): Website URL to check SSL certificate
            
        Returns:
            Dict: SSL certificate information and grading
        """
        try:
            # Parse URL to get hostname
            parsed = urlparse(url)
            hostname = parsed.netloc or parsed.path.split('/')[0]
            
            # Remove port if present
            if ':' in hostname:
                hostname = hostname.split(':')[0]
            
            # Remove www. prefix if present
            if hostname.startswith('www.'):
                hostname = hostname[4:]
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect and get certificate
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse certificate information
                    ssl_info = SSLMonitor._parse_certificate(cert, hostname)
                    
                    logger.info(f"SSL check successful for {url}: Grade {ssl_info['grade']}")
                    return ssl_info
                    
        except socket.timeout:
            logger.error(f"SSL check timeout for {url}")
            return SSLMonitor._create_error_response("Connection timeout")
            
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for {url}: {e}")
            return SSLMonitor._create_error_response(f"DNS resolution failed: {e}")
            
        except ssl.SSLError as e:
            logger.error(f"SSL error for {url}: {e}")
            return SSLMonitor._create_error_response(f"SSL error: {e}")
            
        except ConnectionRefusedError:
            logger.error(f"Connection refused for {url}")
            return SSLMonitor._create_error_response("Connection refused (port 443 closed)")
            
        except Exception as e:
            logger.error(f"Unexpected SSL check error for {url}: {e}")
            return SSLMonitor._create_error_response(f"Unexpected error: {e}")
    
    @staticmethod
    def _parse_certificate(cert: Dict, hostname: str) -> Dict:
        """Parse SSL certificate and calculate grade"""
        try:
            # Parse expiration date
            expiry_date = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            current_date = datetime.datetime.now()
            days_until_expiry = (expiry_date - current_date).days
            
            # Parse issuer and subject
            issuer = dict(x[0] for x in cert.get('issuer', []))
            subject = dict(x[0] for x in cert.get('subject', []))
            
            # Calculate SSL grade
            grade = SSLMonitor._calculate_ssl_grade(cert, days_until_expiry)
            
            # Determine status
            if days_until_expiry < 0:
                status = "EXPIRED"
                alert_level = "CRITICAL"
            elif days_until_expiry <= 7:
                status = "EXPIRING_SOON"
                alert_level = "HIGH"
            elif days_until_expiry <= 30:
                status = "EXPIRING"
                alert_level = "MEDIUM"
            else:
                status = "VALID"
                alert_level = "LOW"
            
            return {
                'valid': True,
                'status': status,
                'alert_level': alert_level,
                'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
                'days_until_expiry': days_until_expiry,
                'issuer': issuer.get('organizationName', 'Unknown'),
                'issuer_cn': issuer.get('commonName', 'Unknown'),
                'subject': subject.get('commonName', hostname),
                'grade': grade,
                'serial_number': cert.get('serialNumber', 'Unknown'),
                'version': cert.get('version', 'Unknown'),
                'signature_algorithm': cert.get('signatureAlgorithm', 'Unknown'),
                'checked_at': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing certificate: {e}")
            return SSLMonitor._create_error_response(f"Certificate parsing error: {e}")
    
    @staticmethod
    def _calculate_ssl_grade(cert: Dict, days_until_expiry: int) -> str:
        """Calculate SSL certificate grade based on various factors"""
        score = 100  # Start with perfect score
        
        # Expiration penalty
        if days_until_expiry < 0:
            score = 0  # Expired certificate
        elif days_until_expiry <= 7:
            score -= 50  # Critical
        elif days_until_expiry <= 30:
            score -= 20  # Warning
        elif days_until_expiry <= 90:
            score -= 10  # Notice
        
        # Check signature algorithm
        sig_alg = cert.get('signatureAlgorithm', '').lower()
        if 'sha1' in sig_alg:
            score -= 30  # SHA1 is weak
        elif 'md5' in sig_alg:
            score -= 50  # MD5 is very weak
        
        # Check key size (if available)
        # This would require more complex parsing
        
        # Convert score to grade
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
    
    @staticmethod
    def _create_error_response(error_message: str) -> Dict:
        """Create standardized error response"""
        return {
            'valid': False,
            'status': 'ERROR',
            'alert_level': 'HIGH',
            'error': error_message,
            'grade': 'F',
            'checked_at': datetime.datetime.now().isoformat()
        }

    @staticmethod
    def get_ssl_alerts(ssl_info: Dict) -> Optional[Dict]:
        """Generate SSL-related alerts based on certificate status"""
        if not ssl_info.get('valid'):
            return {
                'type': 'ssl_error',
                'severity': 'high',
                'message': f"SSL certificate error: {ssl_info.get('error', 'Unknown error')}",
                'action_required': True
            }
        
        days_until_expiry = ssl_info.get('days_until_expiry', 0)
        status = ssl_info.get('status', 'UNKNOWN')
        
        if status == 'EXPIRED':
            return {
                'type': 'ssl_expired',
                'severity': 'critical',
                'message': f"SSL certificate has EXPIRED {abs(days_until_expiry)} days ago",
                'action_required': True
            }
        elif status == 'EXPIRING_SOON':
            return {
                'type': 'ssl_expiring_soon',
                'severity': 'high', 
                'message': f"SSL certificate expires in {days_until_expiry} days",
                'action_required': True
            }
        elif status == 'EXPIRING':
            return {
                'type': 'ssl_expiring',
                'severity': 'medium',
                'message': f"SSL certificate expires in {days_until_expiry} days",
                'action_required': False
            }
        
        return None
