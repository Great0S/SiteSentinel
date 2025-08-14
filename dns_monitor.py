"""
DNS Monitoring Module for SiteSentinel
Provides comprehensive DNS monitoring including record checking, change detection,
resolution timing, and security monitoring
"""

import dns.resolver
import dns.exception
import socket
import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class DNSMonitor:
    """Advanced DNS monitoring with record checking, change detection, and security analysis"""

    def __init__(self):
        # DNS record types to monitor
        self.record_types = ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'NS', 'SOA']

        # DNS resolvers for redundancy
        self.resolvers = [
            '8.8.8.8',      # Google
            '1.1.1.1',      # Cloudflare
            '208.67.222.222',  # OpenDNS
            '9.9.9.9'       # Quad9
        ]

        # DNS security checks
        self.security_checks = {
            'dnssec': True,
            'caa': True,
            'spf': True,
            'dmarc': True,
            'dkim': True
        }

    def monitor_domain(self, url: str) -> Dict:
        """
        Comprehensive DNS monitoring for a domain

        Args:
            url: The URL to monitor DNS for

        Returns:
            Dict containing DNS monitoring results
        """
        try:
            # Extract domain from URL
            domain = self._extract_domain(url)
            if not domain:
                return self._create_error_result("Invalid URL provided")

            logger.info(f"Starting DNS monitoring for domain: {domain}")

            # Perform DNS checks
            start_time = time.time()

            dns_results = {
                'domain': domain,
                'checked_at': datetime.now().isoformat(),
                'records': {},
                'resolution_timing': {},
                'security': {},
                'health_score': 0,
                'status': 'UNKNOWN',
                'issues': [],
                'recommendations': []
            }

            # Check DNS records
            dns_results['records'] = self._check_dns_records(domain)

            # Measure resolution timing
            dns_results['resolution_timing'] = self._measure_resolution_timing(
                domain)

            # Security monitoring
            dns_results['security'] = self._check_dns_security(domain)

            # Calculate health score
            dns_results['health_score'] = self._calculate_dns_health_score(
                dns_results)

            # Determine overall status
            dns_results['status'] = self._determine_dns_status(dns_results)

            # Generate issues and recommendations
            dns_results['issues'] = self._identify_dns_issues(dns_results)
            dns_results['recommendations'] = self._generate_dns_recommendations(
                dns_results)

            total_time = time.time() - start_time
            dns_results['total_check_time'] = round(total_time * 1000, 2)

            logger.info(
                f"DNS monitoring completed for {domain} in {total_time:.2f}s")
            return dns_results

        except Exception as e:
            logger.error(f"Error monitoring DNS for {url}: {e}")
            return self._create_error_result(str(e))

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {e}")
            return ""

    def _check_dns_records(self, domain: str) -> Dict:
        """Check various DNS record types"""
        records = {}

        for record_type in self.record_types:
            try:
                resolver = dns.resolver.Resolver()
                # Use primary resolver
                resolver.nameservers = [self.resolvers[0]]

                start_time = time.time()
                answers = resolver.resolve(domain, record_type)
                resolution_time = time.time() - start_time

                record_data = []
                for answer in answers:
                    if record_type == 'MX':
                        record_data.append({
                            'priority': answer.preference,
                            'exchange': str(answer.exchange),
                            'ttl': answers.rrset.ttl
                        })
                    elif record_type == 'SOA':
                        record_data.append({
                            'mname': str(answer.mname),
                            'rname': str(answer.rname),
                            'serial': answer.serial,
                            'refresh': answer.refresh,
                            'retry': answer.retry,
                            'expire': answer.expire,
                            'minimum': answer.minimum,
                            'ttl': answers.rrset.ttl
                        })
                    else:
                        record_data.append({
                            'value': str(answer),
                            'ttl': answers.rrset.ttl
                        })

                records[record_type] = {
                    'exists': True,
                    'count': len(record_data),
                    'records': record_data,
                    'resolution_time_ms': round(resolution_time * 1000, 2)
                }

            except dns.resolver.NXDOMAIN:
                records[record_type] = {
                    'exists': False,
                    'error': 'NXDOMAIN - Domain does not exist'
                }
            except dns.resolver.NoAnswer:
                records[record_type] = {
                    'exists': False,
                    'error': f'No {record_type} records found'
                }
            except dns.exception.Timeout:
                records[record_type] = {
                    'exists': False,
                    'error': 'DNS query timeout'
                }
            except Exception as e:
                records[record_type] = {
                    'exists': False,
                    'error': f'DNS query failed: {str(e)}'
                }

        return records

    def _measure_resolution_timing(self, domain: str) -> Dict:
        """Measure DNS resolution timing across multiple resolvers"""
        timing_results = {}

        for resolver_ip in self.resolvers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [resolver_ip]
                resolver.timeout = 5.0

                start_time = time.time()
                resolver.resolve(domain, 'A')
                resolution_time = time.time() - start_time

                timing_results[resolver_ip] = {
                    'time_ms': round(resolution_time * 1000, 2),
                    'status': 'SUCCESS'
                }

            except Exception as e:
                timing_results[resolver_ip] = {
                    'time_ms': 0,
                    'status': 'FAILED',
                    'error': str(e)
                }

        # Calculate statistics
        successful_times = [result['time_ms'] for result in timing_results.values()
                            if result['status'] == 'SUCCESS']

        if successful_times:
            timing_results['statistics'] = {
                'min_time_ms': min(successful_times),
                'max_time_ms': max(successful_times),
                'avg_time_ms': round(sum(successful_times) / len(successful_times), 2),
                'success_rate': len(successful_times) / len(self.resolvers) * 100
            }
        else:
            timing_results['statistics'] = {
                'min_time_ms': 0,
                'max_time_ms': 0,
                'avg_time_ms': 0,
                'success_rate': 0
            }

        return timing_results

    def _check_dns_security(self, domain: str) -> Dict:
        """Check DNS security configurations"""
        security_results = {}

        # Check for DNSSEC
        security_results['dnssec'] = self._check_dnssec(domain)

        # Check CAA records
        security_results['caa'] = self._check_caa_records(domain)

        # Check SPF records
        security_results['spf'] = self._check_spf_records(domain)

        # Check DMARC records
        security_results['dmarc'] = self._check_dmarc_records(domain)

        # Check for common DNS vulnerabilities
        security_results['vulnerabilities'] = self._check_dns_vulnerabilities(
            domain)

        return security_results

    def _check_dnssec(self, domain: str) -> Dict:
        """Check DNSSEC status"""
        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, dns.flags.DO, 4096)

            # Try to get DNSKEY record
            answers = resolver.resolve(domain, 'DNSKEY')

            return {
                'enabled': True,
                'keys_found': len(answers),
                'status': 'SECURED'
            }

        except dns.resolver.NoAnswer:
            return {
                'enabled': False,
                'status': 'NOT_SECURED',
                'recommendation': 'Enable DNSSEC for enhanced security'
            }
        except Exception as e:
            return {
                'enabled': False,
                'status': 'UNKNOWN',
                'error': str(e)
            }

    def _check_caa_records(self, domain: str) -> Dict:
        """Check CAA (Certificate Authority Authorization) records"""
        try:
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, 'CAA')

            caa_records = []
            for answer in answers:
                caa_records.append({
                    'flags': answer.flags,
                    'tag': answer.tag.decode(),
                    'value': answer.value.decode()
                })

            return {
                'configured': True,
                'records': caa_records,
                'count': len(caa_records),
                'status': 'PROTECTED'
            }

        except dns.resolver.NoAnswer:
            return {
                'configured': False,
                'status': 'NOT_CONFIGURED',
                'recommendation': 'Configure CAA records to control certificate issuance'
            }
        except Exception as e:
            return {
                'configured': False,
                'status': 'UNKNOWN',
                'error': str(e)
            }

    def _check_spf_records(self, domain: str) -> Dict:
        """Check SPF (Sender Policy Framework) records"""
        try:
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, 'TXT')

            spf_records = []
            for answer in answers:
                txt_value = str(answer).strip('"')
                if txt_value.startswith('v=spf1'):
                    spf_records.append(txt_value)

            if spf_records:
                return {
                    'configured': True,
                    'records': spf_records,
                    'count': len(spf_records),
                    'status': 'CONFIGURED'
                }
            else:
                return {
                    'configured': False,
                    'status': 'NOT_CONFIGURED',
                    'recommendation': 'Configure SPF records to prevent email spoofing'
                }

        except Exception as e:
            return {
                'configured': False,
                'status': 'UNKNOWN',
                'error': str(e)
            }

    def _check_dmarc_records(self, domain: str) -> Dict:
        """Check DMARC records"""
        try:
            dmarc_domain = f"_dmarc.{domain}"
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(dmarc_domain, 'TXT')

            dmarc_records = []
            for answer in answers:
                txt_value = str(answer).strip('"')
                if txt_value.startswith('v=DMARC1'):
                    dmarc_records.append(txt_value)

            if dmarc_records:
                return {
                    'configured': True,
                    'records': dmarc_records,
                    'count': len(dmarc_records),
                    'status': 'CONFIGURED'
                }
            else:
                return {
                    'configured': False,
                    'status': 'NOT_CONFIGURED',
                    'recommendation': 'Configure DMARC for email authentication'
                }

        except Exception as e:
            return {
                'configured': False,
                'status': 'UNKNOWN',
                'error': str(e)
            }

    def _check_dns_vulnerabilities(self, domain: str) -> List[Dict]:
        """Check for common DNS vulnerabilities"""
        vulnerabilities = []

        # Check for DNS cache poisoning susceptibility
        # Check for zone transfer vulnerabilities
        # Check for wildcard DNS issues

        # For now, return basic checks
        return vulnerabilities

    def _calculate_dns_health_score(self, dns_results: Dict) -> float:
        """Calculate DNS health score (0-100)"""
        score = 0
        max_score = 100

        # Record availability (40 points)
        essential_records = ['A', 'NS', 'SOA']
        available_records = sum(1 for record in essential_records
                                if dns_results['records'].get(record, {}).get('exists', False))
        score += (available_records / len(essential_records)) * 40

        # Resolution timing (25 points)
        timing_stats = dns_results['resolution_timing'].get('statistics', {})
        avg_time = timing_stats.get('avg_time_ms', 1000)
        if avg_time < 50:
            score += 25
        elif avg_time < 100:
            score += 20
        elif avg_time < 200:
            score += 15
        elif avg_time < 500:
            score += 10
        else:
            score += 5

        # Security configuration (25 points)
        security = dns_results['security']
        if security.get('dnssec', {}).get('enabled', False):
            score += 10
        if security.get('caa', {}).get('configured', False):
            score += 5
        if security.get('spf', {}).get('configured', False):
            score += 5
        if security.get('dmarc', {}).get('configured', False):
            score += 5

        # Resolver success rate (10 points)
        success_rate = timing_stats.get('success_rate', 0)
        score += (success_rate / 100) * 10

        return round(min(score, max_score), 1)

    def _determine_dns_status(self, dns_results: Dict) -> str:
        """Determine overall DNS status"""
        health_score = dns_results['health_score']

        if health_score >= 90:
            return 'EXCELLENT'
        elif health_score >= 80:
            return 'GOOD'
        elif health_score >= 70:
            return 'FAIR'
        elif health_score >= 60:
            return 'POOR'
        else:
            return 'CRITICAL'

    def _identify_dns_issues(self, dns_results: Dict) -> List[str]:
        """Identify DNS issues"""
        issues = []

        # Check for missing essential records
        essential_records = ['A', 'NS', 'SOA']
        for record in essential_records:
            if not dns_results['records'].get(record, {}).get('exists', False):
                issues.append(f"Missing {record} record")

        # Check for slow resolution
        timing_stats = dns_results['resolution_timing'].get('statistics', {})
        if timing_stats.get('avg_time_ms', 0) > 500:
            issues.append("Slow DNS resolution times")

        # Check for low success rate
        if timing_stats.get('success_rate', 0) < 80:
            issues.append("Low DNS resolver success rate")

        # Check for missing security configurations
        security = dns_results['security']
        if not security.get('dnssec', {}).get('enabled', False):
            issues.append("DNSSEC not enabled")

        if not security.get('spf', {}).get('configured', False):
            issues.append("SPF records not configured")

        return issues

    def _generate_dns_recommendations(self, dns_results: Dict) -> List[Dict]:
        """Generate DNS optimization recommendations"""
        recommendations = []

        # Security recommendations
        security = dns_results['security']
        if not security.get('dnssec', {}).get('enabled', False):
            recommendations.append({
                'category': 'security',
                'priority': 'HIGH',
                'title': 'Enable DNSSEC',
                'description': 'DNSSEC provides authentication for DNS responses',
                'details': 'Contact your DNS provider to enable DNSSEC for enhanced security'
            })

        if not security.get('caa', {}).get('configured', False):
            recommendations.append({
                'category': 'security',
                'priority': 'MEDIUM',
                'title': 'Configure CAA Records',
                'description': 'CAA records control which CAs can issue certificates',
                'details': 'Add CAA records to prevent unauthorized certificate issuance'
            })

        # Performance recommendations
        timing_stats = dns_results['resolution_timing'].get('statistics', {})
        if timing_stats.get('avg_time_ms', 0) > 200:
            recommendations.append({
                'category': 'performance',
                'priority': 'MEDIUM',
                'title': 'Optimize DNS Performance',
                'description': 'DNS resolution is slower than optimal',
                'details': 'Consider using a faster DNS provider or optimizing TTL values'
            })

        return recommendations

    def _create_error_result(self, error_message: str) -> Dict:
        """Create error result structure"""
        return {
            'domain': 'UNKNOWN',
            'checked_at': datetime.now().isoformat(),
            'status': 'ERROR',
            'error': error_message,
            'health_score': 0,
            'records': {},
            'resolution_timing': {},
            'security': {},
            'issues': [error_message],
            'recommendations': []
        }

    def detect_dns_changes(self, domain: str, previous_results: Dict) -> Dict:
        """Detect changes in DNS configuration"""
        current_results = self.monitor_domain(domain)

        if not previous_results or 'records' not in previous_results:
            return {
                'changes_detected': False,
                'message': 'No previous results to compare'
            }

        changes = []

        # Compare DNS records
        for record_type in self.record_types:
            current_record = current_results['records'].get(record_type, {})
            previous_record = previous_results['records'].get(record_type, {})

            if current_record.get('exists') != previous_record.get('exists'):
                if current_record.get('exists'):
                    changes.append(f"{record_type} record added")
                else:
                    changes.append(f"{record_type} record removed")

            elif current_record.get('exists') and previous_record.get('exists'):
                # Check for content changes
                current_hash = self._hash_record_content(
                    current_record.get('records', []))
                previous_hash = self._hash_record_content(
                    previous_record.get('records', []))

                if current_hash != previous_hash:
                    changes.append(f"{record_type} record content changed")

        return {
            'changes_detected': len(changes) > 0,
            'changes': changes,
            'total_changes': len(changes),
            'checked_at': datetime.now().isoformat()
        }

    def _hash_record_content(self, records: List) -> str:
        """Create hash of record content for change detection"""
        try:
            content = json.dumps(records, sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""


# Global DNS monitor instance
dns_monitor = DNSMonitor()
