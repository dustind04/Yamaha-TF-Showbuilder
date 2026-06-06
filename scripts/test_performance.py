#!/usr/bin/env python3
"""
Performance Test Suite for Yamaha TF Showbuilder

Measures response times and throughput for various operations.
"""

import requests
import time
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000"


def measure_endpoint(endpoint: str, method: str = "GET", data: dict = None,
                     iterations: int = 50) -> dict:
    """Measure response times for an endpoint."""
    times = []

    for _ in range(iterations):
        start = time.time()
        try:
            if method == "GET":
                resp = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            elif method == "POST":
                resp = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
            elif method == "PUT":
                resp = requests.put(f"{BASE_URL}{endpoint}", json=data, timeout=10)

            elapsed = (time.time() - start) * 1000  # Convert to ms
            if resp.status_code in [200, 201]:
                times.append(elapsed)
        except:
            pass

    if not times:
        return {"error": "No successful requests"}

    return {
        "min": min(times),
        "max": max(times),
        "avg": statistics.mean(times),
        "median": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
        "count": len(times)
    }


def run_performance_tests():
    print("\n" + "="*70)
    print("  PERFORMANCE TEST SUITE")
    print("="*70)

    # Create test data
    print("\n📊 Setting up test data...")
    setup_start = time.time()

    # Create channels
    channel_ids = []
    for i in range(1, 17):
        resp = requests.post(f"{BASE_URL}/api/channels/",
                             json={"channel_number": i, "name": f"CH{i}", "channel_type": "input"})
        if resp.status_code == 200:
            channel_ids.append(resp.json()["id"])

    # Create scenes
    scene_ids = []
    for i in range(1, 6):
        resp = requests.post(f"{BASE_URL}/api/scenes/",
                             json={"scene_number": i, "name": f"Scene {i}", "fade_time": 1.0})
        if resp.status_code == 200:
            scene_ids.append(resp.json()["id"])

    setup_time = time.time() - setup_start
    print(f"   Setup completed in {setup_time:.2f}s")

    # ========== ENDPOINT PERFORMANCE ==========
    print("\n⏱️  Endpoint Response Times (ms)")
    print("-" * 60)

    endpoints = [
        ("/health", "GET", None),
        ("/api/channels/", "GET", None),
        ("/api/scenes/", "GET", None),
        ("/api/shows/", "GET", None),
        ("/api/patches/", "GET", None),
        ("/api/patches/matrix", "GET", None),
        ("/api/backstage/current", "GET", None),
        ("/api/presets/", "GET", None),
        ("/api/eink/status", "GET", None),
    ]

    results = {}
    for endpoint, method, data in endpoints:
        stats = measure_endpoint(endpoint, method, data)
        results[endpoint] = stats
        if "error" not in stats:
            print(f"   {endpoint:40s} avg: {stats['avg']:6.1f}ms  p95: {stats['p95']:6.1f}ms")
        else:
            print(f"   {endpoint:40s} ERROR")

    # ========== WRITE OPERATION PERFORMANCE ==========
    print("\n⏱️  Write Operation Response Times (ms)")
    print("-" * 60)

    if channel_ids:
        # Fader update
        stats = measure_endpoint(f"/api/channels/{channel_ids[0]}/fader", "PUT", {"level": -10.0}, 30)
        if "error" not in stats:
            print(f"   {'Fader update':40s} avg: {stats['avg']:6.1f}ms  p95: {stats['p95']:6.1f}ms")

        # Channel update
        stats = measure_endpoint(f"/api/channels/{channel_ids[0]}", "PUT", {"name": "TEST"}, 30)
        if "error" not in stats:
            print(f"   {'Channel update':40s} avg: {stats['avg']:6.1f}ms  p95: {stats['p95']:6.1f}ms")

    # Scene store
    if scene_ids:
        stats = measure_endpoint(f"/api/scenes/{scene_ids[0]}/store", "POST", None, 20)
        if "error" not in stats:
            print(f"   {'Scene store':40s} avg: {stats['avg']:6.1f}ms  p95: {stats['p95']:6.1f}ms")

    # ========== CONCURRENT LOAD TEST ==========
    print("\n🔥 Concurrent Load Test")
    print("-" * 60)

    def make_request():
        start = time.time()
        resp = requests.get(f"{BASE_URL}/api/channels/", timeout=10)
        return time.time() - start, resp.status_code == 200

    # Test different concurrency levels
    for concurrency in [10, 25, 50]:
        times = []
        successes = 0
        total_requests = 100

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            for future in as_completed(futures):
                elapsed, success = future.result()
                times.append(elapsed * 1000)
                if success:
                    successes += 1

        rps = total_requests / (sum(times) / 1000 / concurrency)
        avg_time = statistics.mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        print(f"   Concurrency {concurrency:2d}: {successes}/{total_requests} OK, "
              f"avg: {avg_time:6.1f}ms, p95: {p95_time:6.1f}ms, ~{rps:.0f} req/s")

    # ========== BULK OPERATION TEST ==========
    print("\n📦 Bulk Operation Test")
    print("-" * 60)

    # Create many items quickly
    start = time.time()
    created = 0
    for i in range(20, 33):
        resp = requests.post(f"{BASE_URL}/api/channels/",
                             json={"channel_number": i, "name": f"BULK{i}", "channel_type": "input"})
        if resp.status_code == 200:
            created += 1
            channel_ids.append(resp.json()["id"])
    bulk_create_time = time.time() - start
    print(f"   Create {created} channels: {bulk_create_time:.2f}s ({created/bulk_create_time:.1f}/s)")

    # Fetch all channels
    start = time.time()
    resp = requests.get(f"{BASE_URL}/api/channels/")
    fetch_time = (time.time() - start) * 1000
    count = len(resp.json()) if resp.status_code == 200 else 0
    print(f"   Fetch all ({count} channels): {fetch_time:.1f}ms")

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")
    for ch_id in channel_ids:
        requests.delete(f"{BASE_URL}/api/channels/{ch_id}")
    for scene_id in scene_ids:
        requests.delete(f"{BASE_URL}/api/scenes/{scene_id}")
    print("   Cleanup complete")

    # ========== SUMMARY ==========
    print("\n" + "="*70)
    print("  PERFORMANCE SUMMARY")
    print("="*70)

    # Calculate overall stats
    read_times = [r["avg"] for e, r in results.items() if "error" not in r]
    if read_times:
        print(f"\n   Average read endpoint response time: {statistics.mean(read_times):.1f}ms")
        print(f"   Fastest endpoint: {min(read_times):.1f}ms")
        print(f"   Slowest endpoint: {max(read_times):.1f}ms")

    print("\n   Performance Rating: ", end="")
    avg = statistics.mean(read_times) if read_times else 100
    if avg < 20:
        print("EXCELLENT ⭐⭐⭐")
    elif avg < 50:
        print("GOOD ⭐⭐")
    elif avg < 100:
        print("ACCEPTABLE ⭐")
    else:
        print("NEEDS OPTIMIZATION ⚠️")

    print()


if __name__ == "__main__":
    run_performance_tests()
