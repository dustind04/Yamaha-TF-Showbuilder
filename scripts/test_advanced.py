#!/usr/bin/env python3
"""
Advanced API Test Suite - Edge Cases, Boundaries, and Stress Tests
"""

import requests
import json
import sys
import time
import concurrent.futures
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

results = {"passed": 0, "failed": 0, "errors": []}


def test(name: str, method: str, endpoint: str,
         expected_status: int = 200, data: Dict = None) -> bool:
    """Run a single API test."""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            resp = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=10)
        else:
            raise ValueError(f"Unknown method: {method}")

        passed = resp.status_code == expected_status
        if passed:
            results["passed"] += 1
            print(f"  ✅ {name}")
        else:
            results["failed"] += 1
            results["errors"].append(f"{name}: Expected {expected_status}, got {resp.status_code}")
            print(f"  ❌ {name} (status: {resp.status_code})")

        try:
            return passed, resp.json()
        except:
            return passed, resp.text

    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"{name}: {str(e)}")
        print(f"  ❌ {name} (error: {e})")
        return False, None


def run_advanced_tests():
    print("\n" + "="*70)
    print("  ADVANCED API TESTS - Edge Cases, Boundaries, Stress Tests")
    print("="*70)

    # ========== BOUNDARY TESTS ==========
    print("\n📏 Boundary Value Tests")

    # Channel boundaries
    test("Channel min number (1)", "POST", "/api/channels/",
         data={"channel_number": 1, "name": "CH1", "channel_type": "input"})
    test("Channel max number (40)", "POST", "/api/channels/",
         data={"channel_number": 40, "name": "CH40", "channel_type": "input"})
    test("Channel over max (41)", "POST", "/api/channels/",
         data={"channel_number": 41, "name": "CH41", "channel_type": "input"},
         expected_status=422)
    test("Channel under min (0)", "POST", "/api/channels/",
         data={"channel_number": 0, "name": "CH0", "channel_type": "input"},
         expected_status=422)
    test("Channel negative (-1)", "POST", "/api/channels/",
         data={"channel_number": -1, "name": "CHneg", "channel_type": "input"},
         expected_status=422)

    # Fader level boundaries
    _, ch = test("Create channel for fader test", "POST", "/api/channels/",
                 data={"channel_number": 5, "name": "FADER", "channel_type": "input"})
    if ch:
        ch_id = ch.get("id", 1)
        test("Fader min level (-90dB)", "PUT", f"/api/channels/{ch_id}/fader",
             data={"level": -90.0})
        test("Fader max level (+10dB)", "PUT", f"/api/channels/{ch_id}/fader",
             data={"level": 10.0})
        test("Fader over max (+11dB)", "PUT", f"/api/channels/{ch_id}/fader",
             data={"level": 11.0}, expected_status=422)
        test("Fader under min (-91dB)", "PUT", f"/api/channels/{ch_id}/fader",
             data={"level": -91.0}, expected_status=422)
        test("Delete fader test channel", "DELETE", f"/api/channels/{ch_id}")

    # Scene boundaries
    test("Scene min number (1)", "POST", "/api/scenes/",
         data={"scene_number": 1, "name": "Scene 1"})
    test("Scene max number (200)", "POST", "/api/scenes/",
         data={"scene_number": 200, "name": "Scene 200"})
    test("Scene over max (201)", "POST", "/api/scenes/",
         data={"scene_number": 201, "name": "Scene 201"},
         expected_status=422)

    # Cleanup boundary test data
    test("Delete scene 1", "DELETE", "/api/scenes/1")
    test("Delete scene 200", "DELETE", "/api/scenes/2")

    # ========== SPECIAL CHARACTER TESTS ==========
    print("\n🔤 Special Character & Unicode Tests")

    # Unicode names
    test("Channel with Unicode name", "POST", "/api/channels/",
         data={"channel_number": 10, "name": "日本語チャンネル", "channel_type": "input"})
    test("Channel with emoji", "POST", "/api/channels/",
         data={"channel_number": 11, "name": "🎤 Vocal", "channel_type": "input"})
    test("Channel with special chars", "POST", "/api/channels/",
         data={"channel_number": 12, "name": "CH&'\"<>", "channel_type": "input"})
    test("Channel with long name (32 chars)", "POST", "/api/channels/",
         data={"channel_number": 13, "name": "A" * 32, "channel_type": "input"})
    test("Channel with too long name (33+)", "POST", "/api/channels/",
         data={"channel_number": 14, "name": "A" * 33, "channel_type": "input"},
         expected_status=422)

    # Artist with special names
    test("Artist with accents", "POST", "/api/artists/",
         data={"name": "José García", "primary_instrument": "Guitar"})
    test("Artist with Cyrillic", "POST", "/api/artists/",
         data={"name": "Иван Петров", "primary_instrument": "Drums"})

    # ========== DUPLICATE & CONFLICT TESTS ==========
    print("\n🔄 Duplicate & Conflict Tests")

    test("Create show", "POST", "/api/shows/",
         data={"name": "Conflict Test Show", "venue": "Test"})

    # Duplicate scene number
    test("Create scene 50", "POST", "/api/scenes/",
         data={"scene_number": 50, "name": "Scene 50"})
    test("Duplicate scene 50", "POST", "/api/scenes/",
         data={"scene_number": 50, "name": "Another Scene 50"},
         expected_status=400)

    # ========== INVALID DATA TESTS ==========
    print("\n❌ Invalid Data Tests")

    test("Invalid channel type", "POST", "/api/channels/",
         data={"channel_number": 20, "name": "Test", "channel_type": "invalid"},
         expected_status=422)
    test("Missing required field", "POST", "/api/channels/",
         data={"name": "No Number"},
         expected_status=422)
    test("Invalid JSON body", "POST", "/api/shows/",
         expected_status=422)
    test("Empty request body for show", "POST", "/api/shows/",
         data={}, expected_status=422)

    # ========== RELATIONSHIP TESTS ==========
    print("\n🔗 Advanced Relationship Tests")

    # Create test data
    _, show = test("Create show for relations", "POST", "/api/shows/",
                   data={"name": "Relation Test", "venue": "Test"})
    _, band1 = test("Create band 1", "POST", "/api/bands/",
                    data={"name": "Band Alpha", "genre": "Rock"})
    _, band2 = test("Create band 2", "POST", "/api/bands/",
                    data={"name": "Band Beta", "genre": "Jazz"})
    _, artist1 = test("Create artist 1", "POST", "/api/artists/",
                      data={"name": "Artist One", "primary_instrument": "Vocals"})
    _, artist2 = test("Create artist 2", "POST", "/api/artists/",
                      data={"name": "Artist Two", "primary_instrument": "Guitar"})

    if show and band1 and band2 and artist1 and artist2:
        show_id = show.get("id")
        band1_id = band1.get("id")
        band2_id = band2.get("id")
        artist1_id = artist1.get("id")
        artist2_id = artist2.get("id")

        # Multiple bands to one show
        test("Add band 1 to show", "POST", f"/api/shows/{show_id}/bands/{band1_id}")
        test("Add band 2 to show", "POST", f"/api/shows/{show_id}/bands/{band2_id}")
        test("Get show with multiple bands", "GET", f"/api/shows/{show_id}/bands")

        # Multiple artists to one band
        test("Add artist 1 to band", "POST", f"/api/bands/{band1_id}/artists/{artist1_id}")
        test("Add artist 2 to band", "POST", f"/api/bands/{band1_id}/artists/{artist2_id}")

        # Try duplicate relationship
        test("Duplicate band to show (should fail or be idempotent)",
             "POST", f"/api/shows/{show_id}/bands/{band1_id}")

        # Non-existent relationships
        test("Add non-existent band to show", "POST", f"/api/shows/{show_id}/bands/99999",
             expected_status=404)
        test("Add artist to non-existent band", "POST", f"/api/bands/99999/artists/{artist1_id}",
             expected_status=404)

        # Cleanup
        test("Delete artist 1", "DELETE", f"/api/artists/{artist1_id}")
        test("Delete artist 2", "DELETE", f"/api/artists/{artist2_id}")
        test("Delete band 1", "DELETE", f"/api/bands/{band1_id}")
        test("Delete band 2", "DELETE", f"/api/bands/{band2_id}")
        test("Delete show", "DELETE", f"/api/shows/{show_id}")

    # ========== CONCURRENT ACCESS TESTS ==========
    print("\n⚡ Concurrent Access Tests")

    # Create a channel for concurrent testing
    _, ch = test("Create channel for concurrent test", "POST", "/api/channels/",
                 data={"channel_number": 30, "name": "CONCURRENT", "channel_type": "input"})

    if ch:
        ch_id = ch.get("id")

        def update_fader(level):
            return requests.put(
                f"{BASE_URL}/api/channels/{ch_id}/fader",
                json={"level": level},
                timeout=10
            )

        # Send multiple concurrent updates
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            levels = [-10 + i for i in range(10)]
            futures = [executor.submit(update_fader, level) for level in levels]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start_time
        success_count = sum(1 for r in responses if r.status_code == 200)

        if success_count == len(levels):
            results["passed"] += 1
            print(f"  ✅ Concurrent fader updates ({len(levels)} requests in {elapsed:.2f}s)")
        else:
            results["failed"] += 1
            print(f"  ❌ Concurrent fader updates ({success_count}/{len(levels)} succeeded)")

        test("Delete concurrent test channel", "DELETE", f"/api/channels/{ch_id}")

    # ========== EQ PARAMETER TESTS ==========
    print("\n🎛️  EQ Parameter Boundary Tests")

    _, ch = test("Create channel for EQ test", "POST", "/api/channels/",
                 data={"channel_number": 25, "name": "EQ Test", "channel_type": "input"})

    if ch:
        ch_id = ch.get("id")

        # Valid EQ settings
        test("Update EQ with valid settings", "PUT", f"/api/channels/{ch_id}/eq",
             data={
                 "hpf_enabled": True,
                 "hpf_frequency": 80,
                 "low": {"frequency": 100, "gain": -18, "q": 1.0, "type": "shelf"},
                 "low_mid": {"frequency": 400, "gain": 18, "q": 0.1, "type": "peak"},
                 "high_mid": {"frequency": 2000, "gain": 0, "q": 10.0, "type": "peak"},
                 "high": {"frequency": 20000, "gain": 0, "q": 1.0, "type": "shelf"}
             })

        # Invalid EQ - frequency too low
        test("EQ frequency too low", "PUT", f"/api/channels/{ch_id}/eq",
             data={
                 "hpf_enabled": False,
                 "hpf_frequency": 80,
                 "low": {"frequency": 10, "gain": 0, "q": 1.0, "type": "shelf"},
                 "low_mid": {"frequency": 400, "gain": 0, "q": 1.0, "type": "peak"},
                 "high_mid": {"frequency": 2000, "gain": 0, "q": 1.0, "type": "peak"},
                 "high": {"frequency": 8000, "gain": 0, "q": 1.0, "type": "shelf"}
             }, expected_status=422)

        test("Delete EQ test channel", "DELETE", f"/api/channels/{ch_id}")

    # ========== PATCH ROUTING TESTS ==========
    print("\n🔀 Advanced Patch Routing Tests")

    # Test quick-patch
    test("Quick patch analog input", "POST", "/api/patches/quick-patch",
         data={"input_number": 1, "source_type": "analog", "source_port": 1})
    test("Quick patch dante TIO", "POST", "/api/patches/quick-patch",
         data={"input_number": 2, "source_type": "dante_tio", "source_port": 1})
    test("Quick patch dante other (missing device)", "POST", "/api/patches/quick-patch",
         data={"input_number": 3, "source_type": "dante_other", "source_port": 1},
         expected_status=400)
    test("Quick patch dante other (with device)", "POST", "/api/patches/quick-patch",
         data={"input_number": 3, "source_type": "dante_other", "source_device": "MIC-RX", "source_port": 1})
    test("Quick patch invalid source type", "POST", "/api/patches/quick-patch",
         data={"input_number": 4, "source_type": "invalid", "source_port": 1},
         expected_status=400)
    test("Quick patch input over max", "POST", "/api/patches/quick-patch",
         data={"input_number": 33, "source_type": "analog", "source_port": 1},
         expected_status=422)

    # Dante subscriptions
    test("Create Dante subscription", "POST", "/api/patches/dante/subscribe",
         data={
             "receiver_device": "TF-RACK",
             "receiver_channel": 1,
             "transmitter_device": "TIO-1608-D",
             "transmitter_channel": 1
         })

    # Auto-patch TIO
    test("Auto-patch TIO", "POST", "/api/patches/auto-patch-tio?tio_name=TIO-TEST&start_channel=17")

    # ========== SCENE WORKFLOW TESTS ==========
    print("\n🎬 Scene Workflow Tests")

    # Create channels first for scene storage
    _, ch1 = test("Create channel for scene test 1", "POST", "/api/channels/",
                  data={"channel_number": 31, "name": "Scene CH1", "channel_type": "input"})
    _, ch2 = test("Create channel for scene test 2", "POST", "/api/channels/",
                  data={"channel_number": 32, "name": "Scene CH2", "channel_type": "input"})

    # Create and store scene
    _, scene = test("Create scene for workflow", "POST", "/api/scenes/",
                    data={"scene_number": 100, "name": "Workflow Scene", "fade_time": 2.0})

    if scene:
        scene_id = scene.get("id")

        # Store current state
        test("Store scene state", "POST", f"/api/scenes/{scene_id}/store")

        # Preview scene
        test("Preview scene", "GET", f"/api/scenes/{scene_id}/preview")

        # Recall scene with options
        test("Recall scene with fade override", "POST", f"/api/scenes/{scene_id}/recall",
             data={"fade_override": 5.0, "update_eink": False})

        # Copy scene
        test("Copy scene to new number", "POST", f"/api/scenes/copy/{scene_id}/to/101")

        # Update e-ink labels for scene
        test("Update scene e-ink labels", "PUT", f"/api/scenes/{scene_id}/eink-labels",
             data={"labels": {"31": "VOX 1", "32": "GTR 1"}})

        # Get scene by number
        test("Get scene by number", "GET", "/api/scenes/number/100")

        # Cleanup
        test("Delete copied scene", "DELETE", "/api/scenes/3")
        test("Delete original scene", "DELETE", f"/api/scenes/{scene_id}")

    if ch1:
        test("Delete scene test channel 1", "DELETE", f"/api/channels/{ch1.get('id')}")
    if ch2:
        test("Delete scene test channel 2", "DELETE", f"/api/channels/{ch2.get('id')}")

    # ========== CLEANUP REMAINING TEST DATA ==========
    print("\n🧹 Final Cleanup")

    # Clean up any remaining channels
    resp = requests.get(f"{BASE_URL}/api/channels/")
    if resp.status_code == 200:
        channels = resp.json()
        for ch in channels:
            test(f"Cleanup channel {ch['id']}", "DELETE", f"/api/channels/{ch['id']}")

    # Clean up remaining scenes
    resp = requests.get(f"{BASE_URL}/api/scenes/")
    if resp.status_code == 200:
        scenes = resp.json()
        for scene in scenes:
            test(f"Cleanup scene {scene['id']}", "DELETE", f"/api/scenes/{scene['id']}")

    # Clean up artists
    resp = requests.get(f"{BASE_URL}/api/artists/")
    if resp.status_code == 200:
        artists = resp.json()
        for artist in artists:
            test(f"Cleanup artist {artist['id']}", "DELETE", f"/api/artists/{artist['id']}")

    # ========== RESULTS ==========
    print("\n" + "="*70)
    print(f"  ADVANCED RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("="*70)

    if results["errors"]:
        print("\n❌ Errors:")
        for err in results["errors"][:15]:
            print(f"   - {err}")
        if len(results["errors"]) > 15:
            print(f"   ... and {len(results['errors']) - 15} more")

    print()
    return results["failed"] == 0


if __name__ == "__main__":
    success = run_advanced_tests()
    sys.exit(0 if success else 1)
