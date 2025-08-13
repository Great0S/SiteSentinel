"""
Enhanced AI Health Scoring System for SiteSentinel
Provides intelligent health scoring based on multiple metrics with trend analysis,
adaptive thresholds, and advanced performance assessment
"""

import logging
import statistics
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class EnhancedHealthScorer:
    """Advanced AI-powered health scoring system for websites"""

    # Performance baselines and thresholds
    RESPONSE_TIME_THRESHOLDS = {
        'excellent': 200,    # <200ms
        'good': 500,         # 200-500ms
        'fair': 1000,        # 500ms-1s
        'poor': 2000,        # 1-2s
        'critical': 5000     # >5s
    }

    # Security scoring weights
    SECURITY_WEIGHTS = {
        'ssl_grade': 0.4,
        'certificate_validity': 0.3,
        'protocol_version': 0.2,
        'cipher_strength': 0.1
    }

    # Adaptive scoring factors
    TREND_WEIGHT = 0.3  # 30% weight for trends
    CONSISTENCY_WEIGHT = 0.2  # 20% weight for consistency

    def __init__(self):
        # Historical data storage (in production, this would be database-backed)
        self.historical_data = {}
        self.performance_baselines = {}

    @classmethod
    def calculate_health_score(cls, website_data: Dict, historical_data: List[Dict] = None) -> Dict:
        """
        Calculate comprehensive health score with enhanced analytics

        Args:
            website_data (Dict): Current website monitoring data
            historical_data (List[Dict]): Historical monitoring data for trend analysis

        Returns:
            Dict: Enhanced health score with detailed analysis
        """
        try:
            scorer = cls()

            # Calculate base component scores
            response_score = scorer._score_response_time_enhanced(
                website_data, historical_data)
            status_score = scorer._score_status_code_enhanced(
                website_data, historical_data)
            error_score = scorer._score_error_count_enhanced(
                website_data, historical_data)
            ssl_score = scorer._score_ssl_security_enhanced(website_data)
            uptime_score = scorer._score_uptime_enhanced(
                website_data, historical_data)

            # New enhanced scoring components
            performance_score = scorer._score_performance_consistency(
                website_data, historical_data)
            security_score = scorer._score_security_comprehensive(website_data)
            trend_score = scorer._score_performance_trends(historical_data)

            # Calculate adaptive weights based on website type and performance
            weights = scorer._calculate_adaptive_weights(
                website_data, historical_data)

            # Calculate weighted total score with enhanced components
            # First calculate the maximum possible weighted score
            max_possible_weighted = (
                30 * weights['response_time'] +     # Max response time score
                30 * weights['status_code'] +       # Max status code score
                20 * weights['error_count'] +       # Max error count score
                15 * weights['ssl_security'] +      # Max SSL security score
                10 * weights['uptime'] +            # Max uptime score
                10 * weights['performance'] +       # Max performance score
                10 * weights['security'] +          # Max security score
                10 * weights['trends']              # Max trends score
            )

            # Calculate actual weighted score
            actual_weighted = (
                response_score * weights['response_time'] +
                status_score * weights['status_code'] +
                error_score * weights['error_count'] +
                ssl_score * weights['ssl_security'] +
                uptime_score * weights['uptime'] +
                performance_score * weights['performance'] +
                security_score * weights['security'] +
                trend_score * weights['trends']
            )

            # Normalize to 0-100 scale
            total_score = (actual_weighted / max_possible_weighted) * \
                100 if max_possible_weighted > 0 else 0

            # Apply consistency bonus/penalty
            consistency_factor = scorer._calculate_consistency_factor(
                historical_data)
            total_score *= consistency_factor

            # Ensure score stays within bounds
            total_score = max(0, min(100, total_score))

            # Convert to letter grade with enhanced grading
            grade = scorer._score_to_grade_enhanced(total_score)

            # Determine health status with more granular categories
            status = scorer._get_health_status_enhanced(total_score)

            # Calculate confidence score based on data quality
            confidence = scorer._calculate_confidence_score(
                website_data, historical_data)

            health_info = {
                'score': round(total_score, 1),
                'grade': grade,
                'status': status,
                'confidence': confidence,
                'breakdown': {
                    'response_time': round(response_score, 1),
                    'status_code': round(status_score, 1),
                    'error_count': round(error_score, 1),
                    'ssl_security': round(ssl_score, 1),
                    'uptime': round(uptime_score, 1),
                    'performance_consistency': round(performance_score, 1),
                    'security_comprehensive': round(security_score, 1),
                    # For template compatibility
                    'security_headers': round(security_score, 1),
                    'performance_trends': round(trend_score, 1)
                },
                'weights_used': weights,
                'analysis': {
                    'consistency_factor': round(consistency_factor, 3),
                    'trend_direction': scorer._get_trend_direction(historical_data),
                    'performance_category': scorer._categorize_performance(website_data),
                    'risk_factors': scorer._identify_risk_factors(website_data, historical_data)
                },
                'calculated_at': datetime.now().isoformat()
            }

            logger.info(
                f"Enhanced health score calculated: {total_score:.1f} ({grade}) with {confidence:.1f}% confidence")
            return health_info

        except Exception as e:
            logger.error(f"Error calculating enhanced health score: {e}")
            return scorer._create_error_score(str(e))

    def _score_response_time_enhanced(self, data: Dict, historical_data: List[Dict] = None) -> float:
        """Enhanced response time scoring with adaptive thresholds (0-25 points)"""
        response_time = data.get('response_time')
        if not response_time:
            return 0.0

        try:
            # Extract numeric value from "123ms" format
            if isinstance(response_time, str) and 'ms' in response_time:
                time_ms = float(response_time.replace('ms', ''))
            else:
                time_ms = float(response_time)

            # Calculate adaptive thresholds based on historical data
            if historical_data:
                historical_times = self._extract_response_times(
                    historical_data)
                if historical_times:
                    baseline = statistics.median(historical_times)
                    # Adjust thresholds based on historical performance
                    thresholds = self._calculate_adaptive_thresholds(baseline)
                else:
                    thresholds = self.RESPONSE_TIME_THRESHOLDS
            else:
                thresholds = self.RESPONSE_TIME_THRESHOLDS

            # Score with smooth transitions instead of hard thresholds (0-30 points)
            if time_ms <= thresholds['excellent']:
                return 30.0
            elif time_ms <= thresholds['good']:
                # Linear interpolation between excellent and good
                ratio = (time_ms - thresholds['excellent']) / \
                    (thresholds['good'] - thresholds['excellent'])
                return 30.0 - (ratio * 5.0)  # 30 to 25 points
            elif time_ms <= thresholds['fair']:
                ratio = (time_ms - thresholds['good']) / \
                    (thresholds['fair'] - thresholds['good'])
                return 20.0 - (ratio * 5.0)  # 20 to 15 points
            elif time_ms <= thresholds['poor']:
                ratio = (time_ms - thresholds['fair']) / \
                    (thresholds['poor'] - thresholds['fair'])
                return 15.0 - (ratio * 7.0)  # 15 to 8 points
            elif time_ms <= thresholds['critical']:
                ratio = (time_ms - thresholds['poor']) / \
                    (thresholds['critical'] - thresholds['poor'])
                return 8.0 - (ratio * 5.0)   # 8 to 3 points
            else:
                # Exponential decay for extremely slow responses
                decay_factor = math.exp(-(time_ms -
                                        thresholds['critical']) / 5000)
                return max(0.5, 3.0 * decay_factor)

        except (ValueError, TypeError):
            return 0.0

    def _score_status_code_enhanced(self, data: Dict, historical_data: List[Dict] = None) -> float:
        """Enhanced status code scoring with error pattern analysis (0-30 points)"""
        status_code = data.get('status_code')
        status = data.get('status', 'UNKNOWN')

        # Base scoring
        base_score = self._get_base_status_score(status_code, status)

        # Apply historical context
        if historical_data:
            stability_bonus = self._calculate_status_stability_bonus(
                status_code, historical_data)
            base_score += stability_bonus

        return min(30.0, max(0.0, base_score))

    def _score_error_count_enhanced(self, data: Dict, historical_data: List[Dict] = None) -> float:
        """Enhanced error count scoring with trend analysis (0-20 points)"""
        current_errors = data.get('error_count', 0)

        # Base scoring with smoother transitions
        if current_errors == 0:
            base_score = 20.0
        else:
            # Logarithmic penalty for errors
            base_score = max(0, 20.0 - (math.log(current_errors + 1) * 4))

        # Apply trend analysis
        if historical_data:
            trend_adjustment = self._calculate_error_trend_adjustment(
                current_errors, historical_data)
            base_score += trend_adjustment

        return min(20.0, max(0.0, base_score))

    def _score_ssl_security_enhanced(self, data: Dict) -> float:
        """Enhanced SSL security scoring with comprehensive analysis (0-15 points)"""
        ssl_info = data.get('ssl_info', {})
        url = data.get('url', '')

        if not url.startswith('https://'):
            # Penalize HTTP sites more heavily
            return 2.0

        if not ssl_info or not ssl_info.get('valid'):
            return 0.0

        # Base grade scoring
        ssl_grade = ssl_info.get('grade', 'F')
        grade_scores = {
            'A+': 10.0, 'A': 8.5, 'A-': 7.5,
            'B+': 6.5, 'B': 5.5, 'B-': 4.5,
            'C+': 3.5, 'C': 2.5, 'C-': 1.5,
            'D': 1.0, 'F': 0.0
        }
        base_score = grade_scores.get(ssl_grade, 0.0)

        # Additional security factors
        security_bonus = 0.0

        # Certificate validity period
        if ssl_info.get('days_until_expiry'):
            days_left = ssl_info.get('days_until_expiry', 0)
            if days_left > 30:
                security_bonus += 2.0
            elif days_left > 7:
                security_bonus += 1.0
            else:
                security_bonus -= 2.0  # Penalty for soon-to-expire certs

        # Protocol version bonus
        if ssl_info.get('protocol') == 'TLSv1.3':
            security_bonus += 1.5
        elif ssl_info.get('protocol') == 'TLSv1.2':
            security_bonus += 1.0

        # HSTS header bonus
        if ssl_info.get('hsts_enabled'):
            security_bonus += 1.5

        return min(15.0, base_score + security_bonus)

    def _score_uptime_enhanced(self, data: Dict, historical_data: List[Dict] = None) -> float:
        """Enhanced uptime scoring with availability pattern analysis (0-10 points)"""
        status = data.get('status', 'UNKNOWN')
        current_errors = data.get('error_count', 0)

        # Base uptime score
        if status == 'UP' and current_errors == 0:
            base_score = 10.0
        elif status == 'UP' and current_errors <= 2:
            base_score = 8.0
        elif status == 'SLOW':
            base_score = 6.0
        elif status == 'DOWN':
            base_score = 0.0
        else:
            base_score = 3.0

        # Historical availability analysis
        if historical_data:
            availability_bonus = self._calculate_availability_bonus(
                historical_data)
            base_score += availability_bonus

        return min(10.0, max(0.0, base_score))

    def _score_performance_consistency(self, data: Dict, historical_data: List[Dict] = None) -> float:
        """Score performance consistency and variability (0-10 points)"""
        if not historical_data or len(historical_data) < 3:
            return 5.0  # Neutral score for insufficient data

        response_times = self._extract_response_times(historical_data)
        if not response_times:
            return 5.0

        # Calculate coefficient of variation (CV)
        mean_time = statistics.mean(response_times)
        if mean_time == 0:
            return 10.0

        std_dev = statistics.stdev(response_times) if len(
            response_times) > 1 else 0
        cv = std_dev / mean_time

        # Score based on consistency (lower CV = higher score)
        if cv <= 0.1:      # Very consistent (±10%)
            return 10.0
        elif cv <= 0.2:    # Good consistency (±20%)
            return 8.0
        elif cv <= 0.4:    # Fair consistency (±40%)
            return 6.0
        elif cv <= 0.6:    # Poor consistency (±60%)
            return 4.0
        else:              # Very inconsistent
            return 2.0

    def _score_security_comprehensive(self, data: Dict) -> float:
        """Comprehensive security assessment beyond SSL (0-10 points)"""
        security_score = 0.0
        url = data.get('url', '')

        # HTTPS usage (base requirement)
        if url.startswith('https://'):
            security_score += 4.0
        else:
            return 1.0  # Heavy penalty for HTTP

        # SSL info analysis
        ssl_info = data.get('ssl_info', {})
        if ssl_info:
            # Certificate chain validation
            if ssl_info.get('valid'):
                security_score += 2.0

            # Modern cipher suites
            if ssl_info.get('cipher_strength', 0) >= 256:
                security_score += 1.5
            elif ssl_info.get('cipher_strength', 0) >= 128:
                security_score += 1.0

            # Perfect Forward Secrecy
            if ssl_info.get('perfect_forward_secrecy'):
                security_score += 1.0

            # Certificate transparency
            if ssl_info.get('certificate_transparency'):
                security_score += 1.5

        return min(10.0, security_score)

    def _score_performance_trends(self, historical_data: List[Dict] = None) -> float:
        """Score based on performance trends over time (0-10 points)"""
        if not historical_data or len(historical_data) < 5:
            return 5.0  # Neutral score for insufficient data

        response_times = self._extract_response_times(
            historical_data[-10:])  # Last 10 measurements
        if len(response_times) < 3:
            return 5.0

        # Calculate trend using linear regression
        x_values = list(range(len(response_times)))
        trend_slope = self._calculate_trend_slope(x_values, response_times)

        # Score based on trend direction and magnitude
        if trend_slope <= -10:     # Significant improvement
            return 10.0
        elif trend_slope <= -5:    # Moderate improvement
            return 8.0
        elif trend_slope <= 5:     # Stable performance
            return 6.0
        elif trend_slope <= 15:    # Slight degradation
            return 4.0
        else:                      # Significant degradation
            return 2.0

    def _calculate_adaptive_weights(self, website_data: Dict, historical_data: List[Dict] = None) -> Dict:
        """Calculate adaptive weights based on website characteristics and performance"""
        # Base weights
        weights = {
            'response_time': 0.20,
            'status_code': 0.25,
            'error_count': 0.15,
            'ssl_security': 0.15,
            'uptime': 0.10,
            'performance': 0.05,
            'security': 0.05,
            'trends': 0.05
        }

        # Adjust weights based on website type
        url = website_data.get('url', '')
        if 'api.' in url or '/api/' in url:
            # API endpoints prioritize response time and uptime
            weights['response_time'] = 0.30
            weights['uptime'] = 0.15
            weights['status_code'] = 0.20
        elif 'login' in url or 'secure' in url or 'admin' in url:
            # Security-sensitive sites prioritize SSL and security
            weights['ssl_security'] = 0.25
            weights['security'] = 0.15
            weights['status_code'] = 0.20
        elif 'shop' in url or 'store' in url or 'cart' in url:
            # E-commerce sites prioritize consistency and uptime
            weights['uptime'] = 0.20
            weights['performance'] = 0.15
            weights['response_time'] = 0.25

        # Adjust based on historical performance
        if historical_data and len(historical_data) > 10:
            variability = self._calculate_performance_variability(
                historical_data)
            if variability > 0.3:  # High variability
                weights['trends'] = 0.15  # Increase trend importance
                # Increase consistency importance
                weights['performance'] = 0.10

        return weights

    def _calculate_consistency_factor(self, historical_data: List[Dict] = None) -> float:
        """Calculate consistency factor (0.8 to 1.2)"""
        if not historical_data or len(historical_data) < 5:
            return 1.0

        response_times = self._extract_response_times(historical_data)
        if not response_times:
            return 1.0

        # Calculate variability
        variability = self._calculate_performance_variability(historical_data)

        # Reward consistency, penalize high variability
        if variability <= 0.1:     # Very consistent
            return 1.15
        elif variability <= 0.2:   # Good consistency
            return 1.1
        elif variability <= 0.4:   # Fair consistency
            return 1.0
        elif variability <= 0.6:   # Poor consistency
            return 0.95
        else:                      # Very inconsistent
            return 0.85

    def _calculate_confidence_score(self, website_data: Dict, historical_data: List[Dict] = None) -> float:
        """Calculate confidence in the health score (0-100)"""
        confidence = 50.0  # Base confidence

        # Increase confidence with more data points
        if historical_data:
            data_points = len(historical_data)
            if data_points >= 20:
                confidence += 30.0
            elif data_points >= 10:
                confidence += 20.0
            elif data_points >= 5:
                confidence += 10.0

        # Increase confidence with complete data
        if website_data.get('response_time'):
            confidence += 5.0
        if website_data.get('ssl_info'):
            confidence += 5.0
        if website_data.get('status_code'):
            confidence += 5.0

        # Decrease confidence for inconsistent data
        if historical_data:
            variability = self._calculate_performance_variability(
                historical_data)
            if variability > 0.5:
                confidence -= 15.0
            elif variability > 0.3:
                confidence -= 10.0

        return max(10.0, min(100.0, confidence))

    def _extract_response_times(self, historical_data: List[Dict]) -> List[float]:
        """Extract response times from historical data"""
        times = []
        for entry in historical_data:
            response_time = entry.get('response_time')
            if response_time:
                try:
                    if isinstance(response_time, str) and 'ms' in response_time:
                        time_ms = float(response_time.replace('ms', ''))
                    else:
                        time_ms = float(response_time)
                    times.append(time_ms)
                except (ValueError, TypeError):
                    continue
        return times

    def _calculate_adaptive_thresholds(self, baseline: float) -> Dict:
        """Calculate adaptive thresholds based on baseline performance"""
        # Adjust thresholds based on baseline performance
        factor = max(0.5, min(2.0, baseline / 500))  # Scale factor

        return {
            'excellent': int(self.RESPONSE_TIME_THRESHOLDS['excellent'] * factor),
            'good': int(self.RESPONSE_TIME_THRESHOLDS['good'] * factor),
            'fair': int(self.RESPONSE_TIME_THRESHOLDS['fair'] * factor),
            'poor': int(self.RESPONSE_TIME_THRESHOLDS['poor'] * factor),
            'critical': int(self.RESPONSE_TIME_THRESHOLDS['critical'] * factor)
        }

    def _get_base_status_score(self, status_code: int, status: str) -> float:
        """Get base status code score (0-30 points)"""
        if status == 'UP' and status_code == 200:
            return 30.0
        elif status == 'UP' and status_code in [201, 202, 204]:
            return 28.0
        elif status_code in range(300, 400):
            return 22.0  # Redirects
        elif status_code in [401, 403]:
            return 15.0  # Auth issues
        elif status_code == 404:
            return 10.0   # Not found
        elif status_code in range(500, 600):
            return 5.0   # Server errors
        elif status == 'DOWN':
            return 0.0
        else:
            return 12.0

    def _calculate_status_stability_bonus(self, current_status: int, historical_data: List[Dict]) -> float:
        """Calculate bonus for status code stability"""
        if not historical_data:
            return 0.0

        recent_statuses = [entry.get('status_code')
                           for entry in historical_data[-10:]]
        successful_statuses = [
            s for s in recent_statuses if s and 200 <= s < 300]

        stability_ratio = len(successful_statuses) / \
            len(recent_statuses) if recent_statuses else 0

        if stability_ratio >= 0.9:
            return 3.0
        elif stability_ratio >= 0.8:
            return 2.0
        elif stability_ratio >= 0.7:
            return 1.0
        else:
            return 0.0

    def _calculate_error_trend_adjustment(self, current_errors: int, historical_data: List[Dict]) -> float:
        """Calculate adjustment based on error trends"""
        if len(historical_data) < 3:
            return 0.0

        recent_errors = [entry.get('error_count', 0)
                         for entry in historical_data[-5:]]
        trend = self._calculate_simple_trend(recent_errors)

        if trend < -0.5:  # Improving (errors decreasing)
            return 2.0
        elif trend > 0.5:  # Worsening (errors increasing)
            return -2.0
        else:
            return 0.0

    def _calculate_availability_bonus(self, historical_data: List[Dict]) -> float:
        """Calculate availability bonus based on uptime history"""
        if not historical_data:
            return 0.0

        up_count = sum(
            1 for entry in historical_data if entry.get('status') == 'UP')
        availability_ratio = up_count / len(historical_data)

        if availability_ratio >= 0.99:
            return 2.0
        elif availability_ratio >= 0.95:
            return 1.0
        elif availability_ratio < 0.9:
            return -2.0
        else:
            return 0.0

    def _calculate_performance_variability(self, historical_data: List[Dict]) -> float:
        """Calculate performance variability coefficient"""
        response_times = self._extract_response_times(historical_data)
        if len(response_times) < 2:
            return 0.0

        mean_time = statistics.mean(response_times)
        if mean_time == 0:
            return 0.0

        std_dev = statistics.stdev(response_times)
        return std_dev / mean_time

    def _calculate_trend_slope(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate trend slope using simple linear regression"""
        n = len(x_values)
        if n < 2:
            return 0.0

        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x_values[i] - x_mean) *
                        (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator != 0 else 0.0

    def _calculate_simple_trend(self, values: List[float]) -> float:
        """Calculate simple trend direction"""
        if len(values) < 2:
            return 0.0

        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / \
            (len(values) - len(values)//2)

        return second_half - first_half

    def _get_trend_direction(self, historical_data: List[Dict] = None) -> str:
        """Get overall trend direction"""
        if not historical_data or len(historical_data) < 5:
            return 'UNKNOWN'

        response_times = self._extract_response_times(historical_data[-10:])
        if not response_times:
            return 'UNKNOWN'

        x_values = list(range(len(response_times)))
        slope = self._calculate_trend_slope(x_values, response_times)

        if slope < -10:
            return 'IMPROVING'
        elif slope > 10:
            return 'DEGRADING'
        else:
            return 'STABLE'

    def _categorize_performance(self, website_data: Dict) -> str:
        """Categorize overall performance"""
        response_time = website_data.get('response_time')
        if not response_time:
            return 'UNKNOWN'

        try:
            if isinstance(response_time, str) and 'ms' in response_time:
                time_ms = float(response_time.replace('ms', ''))
            else:
                time_ms = float(response_time)

            if time_ms <= 200:
                return 'HIGH_PERFORMANCE'
            elif time_ms <= 1000:
                return 'STANDARD'
            elif time_ms <= 3000:
                return 'LOW_PERFORMANCE'
            else:
                return 'CRITICAL_PERFORMANCE'
        except (ValueError, TypeError):
            return 'UNKNOWN'

    def _identify_risk_factors(self, website_data: Dict, historical_data: List[Dict] = None) -> List[str]:
        """Identify potential risk factors"""
        risks = []

        # Response time risks
        response_time = website_data.get('response_time')
        if response_time:
            try:
                if isinstance(response_time, str) and 'ms' in response_time:
                    time_ms = float(response_time.replace('ms', ''))
                else:
                    time_ms = float(response_time)

                if time_ms > 3000:
                    risks.append('SLOW_RESPONSE_TIME')
                elif time_ms > 1000:
                    risks.append('MODERATE_RESPONSE_TIME')
            except (ValueError, TypeError):
                pass

        # SSL risks
        ssl_info = website_data.get('ssl_info', {})
        if ssl_info:
            if ssl_info.get('days_until_expiry', 365) < 30:
                risks.append('SSL_EXPIRING_SOON')
            if ssl_info.get('grade', 'A') in ['C', 'D', 'F']:
                risks.append('POOR_SSL_GRADE')

        # Error risks
        error_count = website_data.get('error_count', 0)
        if error_count > 5:
            risks.append('HIGH_ERROR_RATE')
        elif error_count > 0:
            risks.append('ERRORS_DETECTED')

        # Trend risks
        if historical_data:
            trend = self._get_trend_direction(historical_data)
            if trend == 'DEGRADING':
                risks.append('PERFORMANCE_DEGRADING')

            variability = self._calculate_performance_variability(
                historical_data)
            if variability > 0.5:
                risks.append('HIGH_VARIABILITY')

        return risks

    def _score_to_grade_enhanced(self, score: float) -> str:
        """Enhanced grading system with plus/minus grades"""
        if score >= 97:
            return 'A+'
        elif score >= 93:
            return 'A'
        elif score >= 90:
            return 'A-'
        elif score >= 87:
            return 'B+'
        elif score >= 83:
            return 'B'
        elif score >= 80:
            return 'B-'
        elif score >= 77:
            return 'C+'
        elif score >= 73:
            return 'C'
        elif score >= 70:
            return 'C-'
        elif score >= 67:
            return 'D+'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _get_health_status_enhanced(self, score: float) -> str:
        """Enhanced health status with more granular categories"""
        if score >= 95:
            return 'EXCELLENT'
        elif score >= 85:
            return 'VERY_GOOD'
        elif score >= 75:
            return 'GOOD'
        elif score >= 65:
            return 'FAIR'
        elif score >= 50:
            return 'POOR'
        elif score >= 30:
            return 'CRITICAL'
        else:
            return 'FAILING'

    def _create_error_score(self, error_message: str) -> Dict:
        """Create error response for health scoring"""
        return {
            'score': 0.0,
            'grade': 'F',
            'status': 'ERROR',
            'confidence': 0.0,
            'error': error_message,
            'breakdown': {
                'response_time': 0.0,
                'status_code': 0.0,
                'error_count': 0.0,
                'ssl_security': 0.0,
                'uptime': 0.0,
                'performance_consistency': 0.0,
                'security_comprehensive': 0.0,
                'security_headers': 0.0,  # For template compatibility
                'performance_trends': 0.0
            },
            'weights_used': {},
            'analysis': {
                'consistency_factor': 1.0,
                'trend_direction': 'UNKNOWN',
                'performance_category': 'UNKNOWN',
                'risk_factors': ['CALCULATION_ERROR']
            },
            'calculated_at': datetime.now().isoformat()
        }

    @classmethod
    def get_health_recommendations(cls, health_data: Dict, website_data: Dict = None, historical_data: List[Dict] = None) -> Dict:
        """Get enhanced recommendations based on comprehensive health analysis"""
        recommendations = {
            'priority': [],      # High priority issues
            'optimization': [],  # Performance optimizations
            'security': [],      # Security improvements
            'monitoring': [],    # Monitoring suggestions
            'maintenance': []    # Maintenance tasks
        }

        breakdown = health_data.get('breakdown', {})
        analysis = health_data.get('analysis', {})
        risk_factors = analysis.get('risk_factors', [])

        # Priority recommendations (critical issues)
        if breakdown.get('status_code', 0) < 15:
            recommendations['priority'].append({
                'title': '🚨 Critical: Fix HTTP Status Issues',
                'description': 'Website returning error status codes that prevent access',
                'impact': 'HIGH',
                'effort': 'MEDIUM',
                'action': 'Investigate server errors, check configuration, and fix routing issues'
            })

        if breakdown.get('uptime', 0) < 5:
            recommendations['priority'].append({
                'title': '🚨 Critical: Resolve Downtime Issues',
                'description': 'Website experiencing significant downtime',
                'impact': 'HIGH',
                'effort': 'HIGH',
                'action': 'Check server status, hosting provider issues, and infrastructure'
            })

        if 'SSL_EXPIRING_SOON' in risk_factors:
            recommendations['priority'].append({
                'title': '🔒 Urgent: SSL Certificate Expiring',
                'description': 'SSL certificate expires within 30 days',
                'impact': 'HIGH',
                'effort': 'LOW',
                'action': 'Renew SSL certificate immediately to prevent security warnings'
            })

        # Performance optimization recommendations
        if breakdown.get('response_time', 0) < 15:
            performance_category = analysis.get(
                'performance_category', 'UNKNOWN')
            if performance_category == 'CRITICAL_PERFORMANCE':
                recommendations['optimization'].append({
                    'title': '⚡ Critical: Optimize Response Time',
                    'description': 'Extremely slow response times affecting user experience',
                    'impact': 'HIGH',
                    'effort': 'HIGH',
                    'action': 'Implement CDN, optimize database queries, enable caching, upgrade server resources'
                })
            elif performance_category == 'LOW_PERFORMANCE':
                recommendations['optimization'].append({
                    'title': '⚡ Optimize Response Time',
                    'description': 'Response times could be improved for better user experience',
                    'impact': 'MEDIUM',
                    'effort': 'MEDIUM',
                    'action': 'Consider CDN implementation, image optimization, and server-side caching'
                })

        if breakdown.get('performance_consistency', 0) < 6:
            recommendations['optimization'].append({
                'title': '📊 Improve Performance Consistency',
                'description': 'Website performance varies significantly between requests',
                'impact': 'MEDIUM',
                'effort': 'MEDIUM',
                'action': 'Implement load balancing, optimize resource allocation, and investigate bottlenecks'
            })

        trend_direction = analysis.get('trend_direction', 'UNKNOWN')
        if trend_direction == 'DEGRADING':
            recommendations['optimization'].append({
                'title': '📉 Address Performance Degradation',
                'description': 'Website performance is trending downward over time',
                'impact': 'MEDIUM',
                'effort': 'MEDIUM',
                'action': 'Analyze performance metrics, identify resource usage patterns, and optimize accordingly'
            })

        # Security recommendations
        if breakdown.get('ssl_security', 0) < 10:
            ssl_score = breakdown.get('ssl_security', 0)
            if ssl_score < 5:
                recommendations['security'].append({
                    'title': '🔒 Critical: Improve SSL Security',
                    'description': 'SSL configuration has serious security weaknesses',
                    'impact': 'HIGH',
                    'effort': 'MEDIUM',
                    'action': 'Update SSL certificate, enable modern protocols (TLS 1.3), and fix cipher suite configuration'
                })
            else:
                recommendations['security'].append({
                    'title': '🔒 Enhance SSL Configuration',
                    'description': 'SSL security can be improved with better configuration',
                    'impact': 'MEDIUM',
                    'effort': 'LOW',
                    'action': 'Enable HSTS, implement certificate pinning, and update to TLS 1.3'
                })

        if breakdown.get('security_comprehensive', 0) < 7:
            recommendations['security'].append({
                'title': '🛡️ Strengthen Security Posture',
                'description': 'Overall security configuration needs improvement',
                'impact': 'MEDIUM',
                'effort': 'MEDIUM',
                'action': 'Implement security headers, enable HTTPS redirects, and review security policies'
            })

        # Monitoring recommendations
        if len(historical_data or []) < 10:
            recommendations['monitoring'].append({
                'title': '📊 Establish Baseline Monitoring',
                'description': 'Insufficient historical data for accurate health assessment',
                'impact': 'LOW',
                'effort': 'LOW',
                'action': 'Continue monitoring to establish performance baselines and identify patterns'
            })

        if 'HIGH_VARIABILITY' in risk_factors:
            recommendations['monitoring'].append({
                'title': '📈 Implement Real-time Monitoring',
                'description': 'High performance variability detected',
                'impact': 'MEDIUM',
                'effort': 'MEDIUM',
                'action': 'Set up real-time performance monitoring and alerts for immediate issue detection'
            })

        # Maintenance recommendations
        if breakdown.get('error_count', 0) < 10 and breakdown.get('error_count', 0) > 0:
            recommendations['maintenance'].append({
                'title': '🛠️ Address Recurring Errors',
                'description': 'Website experiencing intermittent errors',
                'impact': 'MEDIUM',
                'effort': 'MEDIUM',
                'action': 'Investigate error logs, fix underlying issues, and implement error handling improvements'
            })

        # Positive reinforcement for good performance
        if health_data.get('score', 0) >= 90:
            recommendations['maintenance'].append({
                'title': '✅ Excellent Performance!',
                'description': 'Website is performing exceptionally well',
                'impact': 'POSITIVE',
                'effort': 'NONE',
                'action': 'Continue current monitoring practices and maintain consistent performance'
            })

        # Add confidence-based recommendations
        confidence = health_data.get('confidence', 0)
        if confidence < 70:
            recommendations['monitoring'].append({
                'title': '📊 Improve Data Quality',
                'description': f'Health score confidence is {confidence:.0f}% - more data needed for accurate assessment',
                'impact': 'LOW',
                'effort': 'LOW',
                'action': 'Continue monitoring for more accurate health assessments'
            })

        return recommendations


# Backward compatibility alias
class HealthScorer(EnhancedHealthScorer):
    """Backward compatibility alias for the enhanced health scorer"""

    @staticmethod
    def calculate_health_score(website_data: Dict) -> Dict:
        """Backward compatible method that calls enhanced version"""
        enhanced_scorer = EnhancedHealthScorer()
        return enhanced_scorer.calculate_health_score(website_data)

    @staticmethod
    def get_health_recommendations(health_data: Dict) -> list:
        """Backward compatible recommendations method"""
        enhanced_recommendations = EnhancedHealthScorer.get_health_recommendations(
            health_data)

        # Convert to simple list format for backward compatibility
        simple_recommendations = []
        for category_recs in enhanced_recommendations.values():
            for rec in category_recs:
                if rec.get('impact') == 'POSITIVE':
                    simple_recommendations.append(f"✅ {rec['description']}")
                elif rec.get('impact') == 'HIGH':
                    simple_recommendations.append(
                        f"🚨 {rec['title']}: {rec['description']}")
                else:
                    simple_recommendations.append(
                        f"{rec['title']}: {rec['description']}")

        if not simple_recommendations:
            simple_recommendations.append(
                "✅ No specific recommendations - website performing well")

        return simple_recommendations
