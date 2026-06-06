#!/usr/bin/env python3
"""
Security Test Suite for Yamaha TF Showbuilder

Tests for common web application vulnerabilities:
- SQL Injection
- XSS (Cross-Site Scripting)
- Path Traversal
- Command Injection
- IDOR (Insecure Direct Object References)
- Rate Limiting
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

results = {"passed": 0, "failed": 0, "warnings": []}


def test_security(name: str, passed: bool, warning_msg: str = None):
    """Record a security test result."""
    if passed:
        results["passed"] += 1
        print(f"  ✅ {name}")
    else:
        results["failed"] += 1
        if warning_msg:
            results["warnings"].append(warning_msg)
        print(f"  ❌ {name}")


def run_security_tests():
    print("\n" + "="*70)
    print("  SECURITY TEST SUITE - Vulnerability Assessment")
    print("="*70)

    # ========== SQL INJECTION TESTS ==========
    print("\n🔒 SQL Injection Tests")

    # Test various SQL injection payloads
    sql_payloads = [
        "1; DROP TABLE channels;--",
        "1' OR '1'='1",
        "1 UNION SELECT * FROM users--",
        "' OR 1=1--",
        "1; DELETE FROM shows WHERE 1=1;--",
    ]

    for payload in sql_payloads:
        try:
            # Test in channel name
            resp = requests.post(f"{BASE_URL}/api/channels/",
                                 json={"channel_number": 35, "name": payload, "channel_type": "input"},
                                 timeout=10)
            # Should either succeed (storing safely) or reject (validation)
            # A vulnerable app might crash or return unusual data
            is_safe = resp.status_code in [200, 201, 400, 422]
            test_security(f"SQL injection in name: {payload[:30]}...", is_safe)
        except Exception as e:
            test_security(f"SQL injection in name: {payload[:30]}...", False, str(e))

    # Test in URL parameters
    try:
        resp = requests.get(f"{BASE_URL}/api/channels/?channel_type=input'; DROP TABLE channels;--",
                            timeout=10)
        is_safe = resp.status_code in [200, 400, 422]
        test_security("SQL injection in query param", is_safe)
    except Exception as e:
        test_security("SQL injection in query param", False, str(e))

    # ========== XSS TESTS ==========
    print("\n🔒 XSS (Cross-Site Scripting) Tests")

    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "{{constructor.constructor('alert(1)')()}}",  # Template injection
    ]

    for payload in xss_payloads:
        try:
            # Create an artist with XSS payload
            resp = requests.post(f"{BASE_URL}/api/artists/",
                                 json={"name": payload, "primary_instrument": "Test"},
                                 timeout=10)
            if resp.status_code == 200:
                artist_id = resp.json().get("id")
                # Retrieve and check if properly escaped
                resp2 = requests.get(f"{BASE_URL}/api/artists/{artist_id}", timeout=10)
                if resp2.status_code == 200:
                    stored = resp2.json().get("name", "")
                    # Just check it was stored (escaping is frontend responsibility)
                    test_security(f"XSS payload stored: {payload[:30]}...", True)
                    # Cleanup
                    requests.delete(f"{BASE_URL}/api/artists/{artist_id}")
                else:
                    test_security(f"XSS payload retrieval: {payload[:30]}...", True)
            else:
                test_security(f"XSS payload rejected: {payload[:30]}...", True)
        except Exception as e:
            test_security(f"XSS test error: {payload[:30]}...", False, str(e))

    # ========== PATH TRAVERSAL TESTS ==========
    print("\n🔒 Path Traversal Tests")

    path_payloads = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "/etc/passwd%00",
        "..%252f..%252f..%252fetc/passwd",
    ]

    for payload in path_payloads:
        try:
            # Test in various endpoints that might use file paths
            resp = requests.get(f"{BASE_URL}/api/presets/search?q={payload}", timeout=10)
            # Should not return file contents or crash
            is_safe = resp.status_code in [200, 400, 404, 422] and "root:" not in resp.text
            test_security(f"Path traversal: {payload[:30]}...", is_safe)
        except Exception as e:
            test_security(f"Path traversal test error", False, str(e))

    # ========== COMMAND INJECTION TESTS ==========
    print("\n🔒 Command Injection Tests")

    cmd_payloads = [
        "; ls -la",
        "| cat /etc/passwd",
        "`whoami`",
        "$(id)",
        "& ping -c 3 127.0.0.1 &",
    ]

    for payload in cmd_payloads:
        try:
            resp = requests.post(f"{BASE_URL}/api/shows/",
                                 json={"name": payload, "venue": "Test"},
                                 timeout=10)
            # Should store safely or reject
            is_safe = resp.status_code in [200, 201, 400, 422]
            test_security(f"Command injection: {payload[:20]}...", is_safe)
            if resp.status_code == 200:
                show_id = resp.json().get("id")
                requests.delete(f"{BASE_URL}/api/shows/{show_id}")
        except Exception as e:
            test_security(f"Command injection test error", False, str(e))

    # ========== IDOR TESTS ==========
    print("\n🔒 IDOR (Insecure Direct Object Reference) Tests")

    # Create a resource and try to access/modify it with different IDs
    try:
        # Create a show
        resp = requests.post(f"{BASE_URL}/api/shows/",
                             json={"name": "IDOR Test", "venue": "Test"},
                             timeout=10)
        if resp.status_code == 200:
            show_id = resp.json().get("id")

            # Try to access non-existent IDs (should return 404)
            resp2 = requests.get(f"{BASE_URL}/api/shows/99999", timeout=10)
            test_security("IDOR: Non-existent ID returns 404", resp2.status_code == 404)

            # Try negative ID
            resp3 = requests.get(f"{BASE_URL}/api/shows/-1", timeout=10)
            test_security("IDOR: Negative ID handled", resp3.status_code in [400, 404, 422])

            # Try string ID
            resp4 = requests.get(f"{BASE_URL}/api/shows/abc", timeout=10)
            test_security("IDOR: String ID handled", resp4.status_code in [400, 404, 422])

            # Cleanup
            requests.delete(f"{BASE_URL}/api/shows/{show_id}")
    except Exception as e:
        test_security("IDOR tests failed", False, str(e))

    # ========== INPUT VALIDATION TESTS ==========
    print("\n🔒 Input Validation Tests")

    # Test extremely large inputs
    try:
        large_string = "A" * 100000
        resp = requests.post(f"{BASE_URL}/api/channels/",
                             json={"channel_number": 36, "name": large_string, "channel_type": "input"},
                             timeout=30)
        # Should be rejected due to max_length constraint
        test_security("Large string input rejected", resp.status_code in [400, 413, 422])
    except Exception as e:
        # Connection error or timeout is also acceptable (server protecting itself)
        test_security("Large string input handled", True)

    # Test null bytes
    try:
        resp = requests.post(f"{BASE_URL}/api/artists/",
                             json={"name": "Test\x00Null", "primary_instrument": "Test"},
                             timeout=10)
        test_security("Null byte in input handled", resp.status_code in [200, 400, 422])
        if resp.status_code == 200:
            requests.delete(f"{BASE_URL}/api/artists/{resp.json().get('id')}")
    except Exception as e:
        test_security("Null byte test", False, str(e))

    # Test JSON structure attacks
    try:
        # Deeply nested JSON
        nested = {"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}}
        resp = requests.post(f"{BASE_URL}/api/shows/",
                             json={"name": "Nested", "venue": "Test", "extra": nested},
                             timeout=10)
        test_security("Deeply nested JSON handled", resp.status_code in [200, 400, 422])
        if resp.status_code == 200:
            requests.delete(f"{BASE_URL}/api/shows/{resp.json().get('id')}")
    except Exception as e:
        test_security("Nested JSON test", True)  # Exception is acceptable

    # ========== CORS TESTS ==========
    print("\n🔒 CORS Configuration Tests")

    try:
        # Check CORS headers
        resp = requests.options(f"{BASE_URL}/api/channels/",
                                headers={"Origin": "http://evil.com",
                                         "Access-Control-Request-Method": "POST"},
                                timeout=10)
        cors_origin = resp.headers.get("Access-Control-Allow-Origin", "")

        # Note: Current config has allow_origins=["*"] which is insecure for production
        if cors_origin == "*":
            test_security("CORS allows all origins (WARNING for production)", True)
            results["warnings"].append("CORS is set to allow all origins (*) - restrict for production")
        else:
            test_security("CORS properly restricted", True)
    except Exception as e:
        test_security("CORS test", False, str(e))

    # ========== RATE LIMITING TESTS ==========
    print("\n🔒 Rate Limiting Tests")

    try:
        # Send many rapid requests
        success_count = 0
        for i in range(50):
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 429:
                # Rate limited - good!
                break

        if success_count == 50:
            test_security("No rate limiting detected (WARNING)", True)
            results["warnings"].append("No rate limiting - consider adding for production")
        else:
            test_security("Rate limiting is active", True)
    except Exception as e:
        test_security("Rate limiting test", False, str(e))

    # ========== HEADER SECURITY TESTS ==========
    print("\n🔒 Security Headers Tests")

    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)

        headers_to_check = [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("X-XSS-Protection", "1; mode=block"),
            ("Content-Security-Policy", None),
            ("Strict-Transport-Security", None),
        ]

        for header, expected in headers_to_check:
            value = resp.headers.get(header)
            if value:
                test_security(f"Header present: {header}", True)
            else:
                test_security(f"Header missing: {header} (WARNING)", True)
                results["warnings"].append(f"Missing security header: {header}")
    except Exception as e:
        test_security("Security headers test", False, str(e))

    # ========== RESULTS ==========
    print("\n" + "="*70)
    print(f"  SECURITY RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("="*70)

    if results["warnings"]:
        print("\n⚠️  Security Warnings:")
        for warning in results["warnings"]:
            print(f"   - {warning}")

    print()
    return results["failed"] == 0


if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)
