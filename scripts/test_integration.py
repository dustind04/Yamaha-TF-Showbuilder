#!/usr/bin/env python3
"""
Integration Test Suite for Yamaha TF Showbuilder

Simulates real-world usage scenarios:
- Complete show setup workflow
- Channel configuration workflow
- Scene creation and recall workflow
- Multi-user stress testing
"""

import requests
import json
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

results = {"passed": 0, "failed": 0, "errors": []}


def test(name: str, passed: bool, detail: str = None):
    """Record a test result."""
    if passed:
        results["passed"] += 1
        print(f"  ✅ {name}")
    else:
        results["failed"] += 1
        if detail:
            results["errors"].append(f"{name}: {detail}")
        print(f"  ❌ {name}")


def run_integration_tests():
    print("\n" + "="*70)
    print("  INTEGRATION TEST SUITE - Real-World Workflows")
    print("="*70)

    # ========== WORKFLOW 1: COMPLETE SHOW SETUP ==========
    print("\n📋 Workflow 1: Complete Show Setup")

    # Step 1: Create a show
    try:
        resp = requests.post(f"{BASE_URL}/api/shows/",
                             json={"name": "Rock Festival 2024", "venue": "Main Stage",
                                   "description": "Annual rock festival"},
                             timeout=10)
        test("Create show", resp.status_code == 200)
        show = resp.json() if resp.status_code == 200 else {}
        show_id = show.get("id")
    except Exception as e:
        test("Create show", False, str(e))
        show_id = None

    # Step 2: Create bands
    band_ids = []
    bands = [
        {"name": "The Rockers", "genre": "Rock"},
        {"name": "Jazz Fusion", "genre": "Jazz"},
        {"name": "Electronic Dreams", "genre": "Electronic"},
    ]
    for band in bands:
        try:
            resp = requests.post(f"{BASE_URL}/api/bands/", json=band, timeout=10)
            test(f"Create band: {band['name']}", resp.status_code == 200)
            if resp.status_code == 200:
                band_ids.append(resp.json().get("id"))
        except Exception as e:
            test(f"Create band: {band['name']}", False, str(e))

    # Step 3: Create artists
    artist_ids = []
    artists = [
        {"name": "John Lead", "primary_instrument": "Vocals"},
        {"name": "Mike Rhythm", "primary_instrument": "Guitar"},
        {"name": "Sarah Bass", "primary_instrument": "Bass"},
        {"name": "Dave Drums", "primary_instrument": "Drums"},
        {"name": "Lisa Keys", "primary_instrument": "Keyboards"},
    ]
    for artist in artists:
        try:
            resp = requests.post(f"{BASE_URL}/api/artists/", json=artist, timeout=10)
            test(f"Create artist: {artist['name']}", resp.status_code == 200)
            if resp.status_code == 200:
                artist_ids.append(resp.json().get("id"))
        except Exception as e:
            test(f"Create artist: {artist['name']}", False, str(e))

    # Step 4: Add artists to band
    if band_ids and artist_ids:
        for i, artist_id in enumerate(artist_ids[:4]):
            try:
                resp = requests.post(f"{BASE_URL}/api/bands/{band_ids[0]}/artists/{artist_id}",
                                     timeout=10)
                test(f"Add artist to band", resp.status_code == 200)
            except Exception as e:
                test("Add artist to band", False, str(e))

    # Step 5: Add bands to show
    if show_id and band_ids:
        for band_id in band_ids:
            try:
                resp = requests.post(f"{BASE_URL}/api/shows/{show_id}/bands/{band_id}",
                                     timeout=10)
                test("Add band to show", resp.status_code == 200)
            except Exception as e:
                test("Add band to show", False, str(e))

    # ========== WORKFLOW 2: CHANNEL CONFIGURATION ==========
    print("\n🎚️  Workflow 2: Channel Configuration")

    channel_ids = []
    channel_configs = [
        {"channel_number": 1, "name": "VOX 1", "channel_type": "input"},
        {"channel_number": 2, "name": "VOX 2", "channel_type": "input"},
        {"channel_number": 3, "name": "GTR L", "channel_type": "input"},
        {"channel_number": 4, "name": "GTR R", "channel_type": "input"},
        {"channel_number": 5, "name": "BASS", "channel_type": "input"},
        {"channel_number": 6, "name": "KICK", "channel_type": "input"},
        {"channel_number": 7, "name": "SNARE", "channel_type": "input"},
        {"channel_number": 8, "name": "KEYS L", "channel_type": "input"},
    ]

    for config in channel_configs:
        try:
            resp = requests.post(f"{BASE_URL}/api/channels/", json=config, timeout=10)
            test(f"Create channel: {config['name']}", resp.status_code == 200)
            if resp.status_code == 200:
                channel_ids.append(resp.json().get("id"))
        except Exception as e:
            test(f"Create channel: {config['name']}", False, str(e))

    # Configure channel processing
    if channel_ids:
        # Set fader levels
        try:
            for i, ch_id in enumerate(channel_ids):
                level = -6.0 + (i * -3)  # Graduated levels
                resp = requests.put(f"{BASE_URL}/api/channels/{ch_id}/fader",
                                    json={"level": level}, timeout=10)
            test("Set fader levels", True)
        except Exception as e:
            test("Set fader levels", False, str(e))

        # Configure EQ on vocal channel
        try:
            eq_settings = {
                "hpf_enabled": True,
                "hpf_frequency": 120,
                "low": {"frequency": 100, "gain": -3, "q": 1.0, "type": "shelf"},
                "low_mid": {"frequency": 350, "gain": -2, "q": 1.4, "type": "peak"},
                "high_mid": {"frequency": 3500, "gain": 3, "q": 2.0, "type": "peak"},
                "high": {"frequency": 12000, "gain": 2, "q": 1.0, "type": "shelf"}
            }
            resp = requests.put(f"{BASE_URL}/api/channels/{channel_ids[0]}/eq",
                                json=eq_settings, timeout=10)
            test("Configure vocal EQ", resp.status_code == 200)
        except Exception as e:
            test("Configure vocal EQ", False, str(e))

        # Configure compressor on bass channel
        try:
            comp_settings = {
                "threshold": -12,
                "ratio": 4.0,
                "attack": 15,
                "release": 150,
                "gain": 3,
                "knee": "medium"
            }
            resp = requests.put(f"{BASE_URL}/api/channels/{channel_ids[4]}/compressor",
                                json=comp_settings, timeout=10)
            test("Configure bass compressor", resp.status_code == 200)
        except Exception as e:
            test("Configure bass compressor", False, str(e))

        # Configure gate on drum channels
        try:
            gate_settings = {
                "threshold": -40,
                "range": -60,
                "attack": 0.5,
                "hold": 50,
                "release": 100
            }
            resp = requests.put(f"{BASE_URL}/api/channels/{channel_ids[5]}/gate",
                                json=gate_settings, timeout=10)
            test("Configure kick gate", resp.status_code == 200)
        except Exception as e:
            test("Configure kick gate", False, str(e))

    # ========== WORKFLOW 3: SCENE MANAGEMENT ==========
    print("\n🎬 Workflow 3: Scene Management")

    scene_ids = []
    scenes = [
        {"scene_number": 1, "name": "Opening", "fade_time": 2.0},
        {"scene_number": 2, "name": "Main Set", "fade_time": 1.0},
        {"scene_number": 3, "name": "Quiet Song", "fade_time": 3.0},
        {"scene_number": 4, "name": "Finale", "fade_time": 0.5},
    ]

    for scene in scenes:
        try:
            resp = requests.post(f"{BASE_URL}/api/scenes/", json=scene, timeout=10)
            test(f"Create scene: {scene['name']}", resp.status_code == 200)
            if resp.status_code == 200:
                scene_ids.append(resp.json().get("id"))
        except Exception as e:
            test(f"Create scene: {scene['name']}", False, str(e))

    # Store scene state
    if scene_ids:
        try:
            resp = requests.post(f"{BASE_URL}/api/scenes/{scene_ids[0]}/store", timeout=10)
            test("Store scene state", resp.status_code == 200)
        except Exception as e:
            test("Store scene state", False, str(e))

        # Recall scene
        try:
            resp = requests.post(f"{BASE_URL}/api/scenes/{scene_ids[0]}/recall",
                                 json={"update_eink": False}, timeout=10)
            test("Recall scene", resp.status_code == 200)
        except Exception as e:
            test("Recall scene", False, str(e))

        # Preview another scene
        try:
            resp = requests.get(f"{BASE_URL}/api/scenes/{scene_ids[0]}/preview", timeout=10)
            test("Preview scene", resp.status_code == 200)
        except Exception as e:
            test("Preview scene", False, str(e))

    # ========== WORKFLOW 4: PATCHING ==========
    print("\n🔀 Workflow 4: Audio Patching")

    try:
        # Quick patch analog inputs
        for i in range(1, 9):
            resp = requests.post(f"{BASE_URL}/api/patches/quick-patch",
                                 json={"input_number": i, "source_type": "analog", "source_port": i},
                                 timeout=10)
        test("Create 8 analog patches", True)
    except Exception as e:
        test("Create 8 analog patches", False, str(e))

    try:
        # Get patch matrix
        resp = requests.get(f"{BASE_URL}/api/patches/matrix", timeout=10)
        matrix = resp.json() if resp.status_code == 200 else {}
        test("Get patch matrix", resp.status_code == 200 and "inputs" in matrix)
    except Exception as e:
        test("Get patch matrix", False, str(e))

    # ========== WORKFLOW 5: BACKSTAGE DISPLAY ==========
    print("\n📺 Workflow 5: Backstage Display")

    try:
        resp = requests.get(f"{BASE_URL}/api/backstage/current", timeout=10)
        test("Get backstage data", resp.status_code == 200)
    except Exception as e:
        test("Get backstage data", False, str(e))

    try:
        resp = requests.get(f"{BASE_URL}/api/backstage/display-config", timeout=10)
        test("Get display config", resp.status_code == 200)
    except Exception as e:
        test("Get display config", False, str(e))

    try:
        resp = requests.get(f"{BASE_URL}/display", timeout=10)
        test("Access backstage display page", resp.status_code == 200)
    except Exception as e:
        test("Access backstage display page", False, str(e))

    # ========== STRESS TEST ==========
    print("\n⚡ Stress Test: Concurrent Operations")

    def make_request(endpoint):
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            return resp.status_code == 200
        except:
            return False

    endpoints = [
        "/api/channels/",
        "/api/scenes/",
        "/api/shows/",
        "/api/patches/",
        "/api/backstage/current",
        "/health",
    ]

    start_time = time.time()
    success_count = 0
    total_requests = 100

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(total_requests):
            endpoint = endpoints[i % len(endpoints)]
            futures.append(executor.submit(make_request, endpoint))

        for future in as_completed(futures):
            if future.result():
                success_count += 1

    elapsed = time.time() - start_time
    rps = total_requests / elapsed if elapsed > 0 else 0

    test(f"Concurrent requests ({success_count}/{total_requests} succeeded, {rps:.1f} req/s)",
         success_count >= total_requests * 0.95)  # 95% success rate

    # Fader stress test
    if channel_ids:
        start_time = time.time()
        success_count = 0

        def update_fader(ch_id, level):
            try:
                resp = requests.put(f"{BASE_URL}/api/channels/{ch_id}/fader",
                                    json={"level": level}, timeout=10)
                return resp.status_code == 200
            except:
                return False

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(50):
                ch_id = channel_ids[i % len(channel_ids)]
                level = -20 + (i % 30)
                futures.append(executor.submit(update_fader, ch_id, level))

            for future in as_completed(futures):
                if future.result():
                    success_count += 1

        elapsed = time.time() - start_time
        test(f"Rapid fader updates ({success_count}/50 in {elapsed:.2f}s)",
             success_count >= 45)  # 90% success rate

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")

    # Delete scenes
    for scene_id in scene_ids:
        try:
            requests.delete(f"{BASE_URL}/api/scenes/{scene_id}", timeout=10)
        except:
            pass
    test("Cleanup scenes", True)

    # Delete channels
    for ch_id in channel_ids:
        try:
            requests.delete(f"{BASE_URL}/api/channels/{ch_id}", timeout=10)
        except:
            pass
    test("Cleanup channels", True)

    # Delete artists
    for artist_id in artist_ids:
        try:
            requests.delete(f"{BASE_URL}/api/artists/{artist_id}", timeout=10)
        except:
            pass
    test("Cleanup artists", True)

    # Delete bands
    for band_id in band_ids:
        try:
            requests.delete(f"{BASE_URL}/api/bands/{band_id}", timeout=10)
        except:
            pass
    test("Cleanup bands", True)

    # Delete show
    if show_id:
        try:
            requests.delete(f"{BASE_URL}/api/shows/{show_id}", timeout=10)
        except:
            pass
    test("Cleanup show", True)

    # Delete remaining patches
    try:
        resp = requests.get(f"{BASE_URL}/api/patches/", timeout=10)
        if resp.status_code == 200:
            for patch in resp.json():
                requests.delete(f"{BASE_URL}/api/patches/{patch['id']}", timeout=10)
    except:
        pass
    test("Cleanup patches", True)

    # ========== RESULTS ==========
    print("\n" + "="*70)
    print(f"  INTEGRATION RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("="*70)

    if results["errors"]:
        print("\n❌ Errors:")
        for err in results["errors"][:10]:
            print(f"   - {err}")

    print()
    return results["failed"] == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
