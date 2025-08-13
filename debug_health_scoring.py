#!/usr/bin/env python3
"""
Debug script for health scoring system
"""

from health_scoring import EnhancedHealthScorer


def test_individual_components():
    """Test each component individually"""
    scorer = EnhancedHealthScorer()

    # Perfect test data
    perfect_data = {
        'url': 'https://example.com',
        'status': 'UP',
        'status_code': 200,
        'response_time': '150ms',
        'error_count': 0,
        'ssl_info': {
            'valid': True,
            'grade': 'A+',
            'days_until_expiry': 90,
            'protocol': 'TLSv1.3',
            'cipher_strength': 256
        }
    }

    historical_data = [
        {'response_time': '140ms', 'status_code': 200,
            'status': 'UP', 'error_count': 0},
        {'response_time': '150ms', 'status_code': 200,
            'status': 'UP', 'error_count': 0},
        {'response_time': '145ms', 'status_code': 200,
            'status': 'UP', 'error_count': 0},
        {'response_time': '155ms', 'status_code': 200,
            'status': 'UP', 'error_count': 0},
        {'response_time': '148ms', 'status_code': 200,
            'status': 'UP', 'error_count': 0}
    ] * 4

    print("=== Individual Component Testing ===")

    # Test each component
    response_score = scorer._score_response_time_enhanced(
        perfect_data, historical_data)
    print(f"Response Time Score (max 30): {response_score}")

    status_score = scorer._score_status_code_enhanced(
        perfect_data, historical_data)
    print(f"Status Code Score (max 30): {status_score}")

    error_score = scorer._score_error_count_enhanced(
        perfect_data, historical_data)
    print(f"Error Count Score (max 20): {error_score}")

    ssl_score = scorer._score_ssl_security_enhanced(perfect_data)
    print(f"SSL Security Score (max 10): {ssl_score}")

    uptime_score = scorer._score_uptime_enhanced(perfect_data, historical_data)
    print(f"Uptime Score (max 10): {uptime_score}")

    performance_score = scorer._score_performance_consistency(
        perfect_data, historical_data)
    print(f"Performance Consistency Score (max 10): {performance_score}")

    security_score = scorer._score_security_comprehensive(perfect_data)
    print(f"Security Comprehensive Score (max 10): {security_score}")

    trend_score = scorer._score_performance_trends(historical_data)
    print(f"Performance Trends Score (max 10): {trend_score}")

    print(f"\nTotal possible: 130 points")
    total_raw = response_score + status_score + error_score + ssl_score + \
        uptime_score + performance_score + security_score + trend_score
    print(f"Total raw scores: {total_raw}")

    # Test weights
    weights = scorer._calculate_adaptive_weights(perfect_data, historical_data)
    print(f"\nWeights: {weights}")
    print(f"Weight sum: {sum(weights.values())}")

    # Calculate weighted score
    weighted_total = (
        response_score * weights['response_time'] +
        status_score * weights['status_code'] +
        error_score * weights['error_count'] +
        ssl_score * weights['ssl_security'] +
        uptime_score * weights['uptime'] +
        performance_score * weights['performance'] +
        security_score * weights['security'] +
        trend_score * weights['trends']
    )

    print(f"Weighted total (before consistency): {weighted_total}")

    consistency_factor = scorer._calculate_consistency_factor(historical_data)
    print(f"Consistency factor: {consistency_factor}")

    final_score = weighted_total * consistency_factor
    print(f"Final score: {final_score}")


if __name__ == "__main__":
    test_individual_components()
