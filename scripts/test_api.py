#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Yamaha TF Showbuilder
"""

import requests
import json
import sys
from typing import Dict, Any, Tuple

BASE_URL = "http://localhost:8000"

# Test results tracking
results = {"passed": 0, "failed": 0, "errors": []}


def test(name: str, method: str, endpoint: str,
         expected_status: int = 200,
         data: Dict = None,
         check_fields: list = None) -> Tuple[bool, Any]:
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

        # Check response fields if specified
        if passed and check_fields and resp.status_code == 200:
            try:
                json_resp = resp.json()
                for field in check_fields:
                    if isinstance(json_resp, list):
                        # For list responses, we just check it's a valid list
                        pass
                    elif field not in json_resp:
                        passed = False
                        results["errors"].append(f"{name}: Missing field '{field}'")
            except:
                pass

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


def run_tests():
    print("\n" + "="*60)
    print("  YAMAHA TF SHOWBUILDER - COMPREHENSIVE API TESTS")
    print("="*60)

    # ========== HEALTH & ROOT ==========
    print("\n📍 Health & Root Endpoints")
    test("Root endpoint", "GET", "/", check_fields=["name", "version", "status"])
    test("Health check", "GET", "/health", check_fields=["status", "tf_rack_connected"])

    # ========== CHANNELS ==========
    print("\n🎚️  Channel API")
    test("List channels", "GET", "/api/channels/")
    test("List input channels", "GET", "/api/channels/?channel_type=input")

    # Create a test channel (max channel_number is 40 for TF-Rack)
    passed, channel = test("Create channel", "POST", "/api/channels/",
        data={"channel_number": 33, "name": "TEST CH", "channel_type": "input"})

    if passed and channel:
        channel_id = channel.get("id", 1)
        test("Get channel", "GET", f"/api/channels/{channel_id}")
        test("Update channel", "PUT", f"/api/channels/{channel_id}",
             data={"name": "UPDATED"})
        test("Set fader level", "PUT", f"/api/channels/{channel_id}/fader",
             data={"level": -6.0})
        test("Toggle mute", "POST", f"/api/channels/{channel_id}/mute")
        test("Delete channel", "DELETE", f"/api/channels/{channel_id}")

    # ========== SCENES ==========
    print("\n🎬 Scene API")
    test("List scenes", "GET", "/api/scenes/")

    passed, scene = test("Create scene", "POST", "/api/scenes/",
        data={"scene_number": 99, "name": "Test Scene", "description": "API Test"})

    if passed and scene:
        scene_id = scene.get("id", 1)
        test("Get scene", "GET", f"/api/scenes/{scene_id}")
        test("Update scene", "PUT", f"/api/scenes/{scene_id}",
             data={"name": "Updated Scene", "fade_time": 2.0})
        test("Store scene", "POST", f"/api/scenes/{scene_id}/store")
        test("Recall scene (no stored state)", "POST", f"/api/scenes/{scene_id}/recall",
             data={"update_eink": False}, expected_status=400)  # Expected: scene has no stored state
        test("Delete scene", "DELETE", f"/api/scenes/{scene_id}")

    # ========== SHOWS ==========
    print("\n📅 Show API")
    test("List shows", "GET", "/api/shows/")

    passed, show = test("Create show", "POST", "/api/shows/",
        data={"name": "API Test Show", "venue": "Test Venue", "description": "Test"})

    show_id = None
    if passed and show:
        show_id = show.get("id")
        test("Get show", "GET", f"/api/shows/{show_id}")
        test("Update show", "PUT", f"/api/shows/{show_id}",
             data={"venue": "Updated Venue"})

    # ========== BANDS ==========
    print("\n🎸 Band API")
    test("List bands", "GET", "/api/bands/")

    passed, band = test("Create band", "POST", "/api/bands/",
        data={"name": "API Test Band", "genre": "Test Genre"})

    band_id = None
    if passed and band:
        band_id = band.get("id")
        test("Get band", "GET", f"/api/bands/{band_id}")
        test("Update band", "PUT", f"/api/bands/{band_id}",
             data={"genre": "Updated Genre"})

    # ========== ARTISTS ==========
    print("\n👤 Artist API")
    test("List artists", "GET", "/api/artists/")

    passed, artist = test("Create artist", "POST", "/api/artists/",
        data={"name": "API Test Artist", "primary_instrument": "Test"})

    artist_id = None
    if passed and artist:
        artist_id = artist.get("id")
        test("Get artist", "GET", f"/api/artists/{artist_id}")
        test("Update artist", "PUT", f"/api/artists/{artist_id}",
             data={"primary_instrument": "Updated"})

    # ========== RELATIONSHIPS ==========
    print("\n🔗 Relationship API")
    if band_id and artist_id:
        test("Add artist to band", "POST", f"/api/bands/{band_id}/artists/{artist_id}")

    if show_id and band_id:
        test("Add band to show", "POST", f"/api/shows/{show_id}/bands/{band_id}")
        test("Get show bands", "GET", f"/api/shows/{show_id}/bands")

    # ========== PRESETS ==========
    print("\n🎛️  Preset API")
    test("List presets", "GET", "/api/presets/")
    test("Get preset categories", "GET", "/api/presets/categories")
    test("Search presets", "GET", "/api/presets/search?q=vocal")

    # Get first preset to test apply
    _, presets = test("Get presets for apply test", "GET", "/api/presets/")
    if presets and len(presets) > 0:
        preset_id = presets[0].get("id", 1)
        # Need a channel to apply to - this might fail if no channels exist
        test("Apply preset (may fail without channel)", "POST",
             f"/api/presets/{preset_id}/apply",
             data={"channel_id": 1, "update_eink": False},
             expected_status=404)  # Expected to fail if channel 1 doesn't exist

    # ========== E-INK ==========
    print("\n🖥️  E-Ink API")
    test("Get display status", "GET", "/api/eink/status")
    test("Get display mappings", "GET", "/api/eink/mapping/all")
    test("Get single display (not connected)", "GET", "/api/eink/0", expected_status=404)  # Display exists but not connected

    # ========== DEVICES ==========
    print("\n📡 Device API")
    test("List devices", "GET", "/api/devices/")
    test("Get TF-Rack status", "GET", "/api/devices/tf-rack/status")
    test("Get Dante devices", "GET", "/api/devices/dante")

    # ========== BACKSTAGE ==========
    print("\n📺 Backstage API")
    test("Get current backstage", "GET", "/api/backstage/current")
    test("Get wireless overview", "GET", "/api/backstage/wireless-overview")
    test("Get display config", "GET", "/api/backstage/display-config")

    # ========== PATCHES ==========
    print("\n🔀 Patch API")
    test("List patches", "GET", "/api/patches/")
    test("Get patch matrix", "GET", "/api/patches/matrix")

    # ========== INPUT LISTS ==========
    print("\n📋 Input List API")
    test("List input lists", "GET", "/api/input-lists/")

    passed, input_list = test("Create input list", "POST", "/api/input-lists/",
        data={"name": "Test Input List", "inputs": []})

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")
    if artist_id:
        test("Delete test artist", "DELETE", f"/api/artists/{artist_id}")
    if band_id:
        test("Delete test band", "DELETE", f"/api/bands/{band_id}")
    if show_id:
        test("Delete test show", "DELETE", f"/api/shows/{show_id}")

    # ========== ERROR HANDLING ==========
    print("\n⚠️  Error Handling")
    test("404 on missing resource", "GET", "/api/shows/99999", expected_status=404)
    test("Invalid endpoint", "GET", "/api/nonexistent", expected_status=404)

    # ========== RESULTS ==========
    print("\n" + "="*60)
    print(f"  RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("="*60)

    if results["errors"]:
        print("\n❌ Errors:")
        for err in results["errors"][:10]:  # Show first 10 errors
            print(f"   - {err}")
        if len(results["errors"]) > 10:
            print(f"   ... and {len(results['errors']) - 10} more")

    print()
    return results["failed"] == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
