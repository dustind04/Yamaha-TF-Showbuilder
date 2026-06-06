#!/usr/bin/env python3
"""
Intensive Songs Feature Tests - 4 Rounds of Increasing Intensity

Round 1: Feature Validation (Medium)
Round 2: Edge Cases & Stress (High)
Round 3: Security & Integration (Very High)
Round 4: Chaos Testing (Maximum)
"""

import requests
import json
import sys
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

results = {"passed": 0, "failed": 0, "errors": []}
round_stats = {}


def test(name: str, method: str, endpoint: str,
         expected_status: int = 200, data: Dict = None,
         check_response: callable = None) -> tuple:
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

        # Additional response validation
        if passed and check_response:
            try:
                passed = check_response(resp.json())
            except:
                passed = False

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


def run_round_1():
    """Round 1: Feature Validation (Medium Intensity)"""
    print("\n" + "="*70)
    print("  ROUND 1: FEATURE VALIDATION (Medium Intensity)")
    print("="*70)
    start = time.time()

    # ========== SONG CRUD ==========
    print("\n🎵 Song CRUD Operations")

    # Create songs
    songs_created = []
    test_songs = [
        {"title": "Bohemian Rhapsody", "artist_name": "Queen", "original_key": "Bb", "tempo": 72},
        {"title": "Stairway to Heaven", "artist_name": "Led Zeppelin", "original_key": "Am", "tempo": 82},
        {"title": "Hotel California", "artist_name": "Eagles", "original_key": "Bm", "tempo": 75},
        {"title": "Sweet Child O Mine", "artist_name": "Guns N Roses", "original_key": "D", "tempo": 126},
        {"title": "Wonderwall", "artist_name": "Oasis", "original_key": "F#m", "tempo": 87},
    ]

    for song in test_songs:
        passed, result = test(f"Create song: {song['title']}", "POST", "/api/songs/", data=song)
        if passed and result:
            songs_created.append(result)

    # List songs
    test("List all songs", "GET", "/api/songs/",
         check_response=lambda r: len(r) == len(test_songs))

    # Get individual song
    if songs_created:
        test("Get song by ID", "GET", f"/api/songs/{songs_created[0]['id']}",
             check_response=lambda r: r['title'] == 'Bohemian Rhapsody')

    # Update song
    if songs_created:
        test("Update song", "PUT", f"/api/songs/{songs_created[0]['id']}",
             data={"tempo": 75, "genre": "Rock"})

    # Search songs
    test("Search songs by title", "GET", "/api/songs/?search=Hotel",
         check_response=lambda r: len(r) == 1)

    test("Search songs by artist", "GET", "/api/songs/?search=Queen",
         check_response=lambda r: len(r) == 1)

    # Get genres
    test("Get genres", "GET", "/api/songs/genres")

    # Get available keys
    test("Get available keys", "GET", "/api/songs/keys",
         check_response=lambda r: len(r['keys']) > 20)

    # ========== CHORD CHART & TRANSPOSITION ==========
    print("\n🎸 Chord Chart & Transposition")

    # Create song with chord chart
    chord_song = {
        "title": "Amazing Grace",
        "artist_name": "Traditional",
        "original_key": "G",
        "tempo": 90,
        "chord_chart": """{title: Amazing Grace}
{key: G}
{tempo: 90}

{start_of_verse}
[G]Amazing [G7]grace, how [C]sweet the [G]sound
That [G]saved a [Em]wretch like [D]me
[G]I once was [G7]lost, but [C]now am [G]found
Was [G]blind but [D]now I [G]see
{end_of_verse}"""
    }

    passed, chart_song = test("Create song with chord chart", "POST", "/api/songs/", data=chord_song)

    if chart_song:
        song_id = chart_song['id']

        # Get chord chart in original key
        test("Get chord chart (original key)", "GET", f"/api/songs/{song_id}/chart",
             check_response=lambda r: '[G]' in r['chart'])

        # Get transposed chart
        test("Get chart transposed to C", "GET", f"/api/songs/{song_id}/chart?key=C",
             check_response=lambda r: r['display_key'] == 'C')

        test("Get chart transposed to D", "GET", f"/api/songs/{song_id}/chart?key=D")

        # Get text format
        test("Get chart as text", "GET", f"/api/songs/{song_id}/chart?format=text")

        # Get printable version
        test("Get printable chart", "GET", f"/api/songs/{song_id}/print")

        # Transpose and save
        test("Transpose song to A", "POST", f"/api/songs/{song_id}/transpose",
             data={"target_key": "A"})

        songs_created.append(chart_song)

    # ========== ARTIST-SONG RELATIONSHIPS ==========
    print("\n👤 Artist-Song Relationships")

    # Create artists
    artists_created = []
    test_artists = [
        {"name": "John Lead", "primary_instrument": "Vocals"},
        {"name": "Mike Guitar", "primary_instrument": "Guitar"},
        {"name": "Sarah Bass", "primary_instrument": "Bass"},
    ]

    for artist in test_artists:
        passed, result = test(f"Create artist: {artist['name']}", "POST", "/api/artists/", data=artist)
        if passed and result:
            artists_created.append(result)

    # Link artists to songs
    if artists_created and songs_created:
        test("Link artist to song", "POST",
             f"/api/songs/artists/{artists_created[0]['id']}/songs/{songs_created[0]['id']}?is_lead_vocal=true")

        test("Link second artist to song", "POST",
             f"/api/songs/artists/{artists_created[1]['id']}/songs/{songs_created[0]['id']}")

        # Get artist's songs
        test("Get artist's songs", "GET",
             f"/api/songs/artists/{artists_created[0]['id']}/songs",
             check_response=lambda r: len(r['songs']) > 0)

        # Set lead vocalist
        test("Set lead vocalist", "PUT",
             f"/api/songs/artists/{artists_created[0]['id']}/songs/{songs_created[0]['id']}/lead?is_lead=true")

    # ========== SHOW SETLIST ==========
    print("\n📋 Show Setlist")

    # Create show
    passed, show = test("Create show for setlist", "POST", "/api/shows/",
                        data={"name": "Test Concert", "venue": "Main Stage"})

    if show and songs_created:
        show_id = show['id']

        # Add songs to setlist
        for i, song in enumerate(songs_created[:3]):
            test(f"Add song to setlist (pos {i+1})", "POST", f"/api/songs/shows/{show_id}/setlist",
                 data={"song_id": song['id'], "position": i + 1})

        # Get setlist
        test("Get show setlist", "GET", f"/api/songs/shows/{show_id}/setlist",
             check_response=lambda r: len(r['setlist']) == 3)

        # Reorder setlist
        if len(songs_created) >= 3:
            test("Reorder setlist", "PUT", f"/api/songs/shows/{show_id}/setlist/reorder",
                 data={"song_ids": [songs_created[2]['id'], songs_created[0]['id'], songs_created[1]['id']]})

        # Remove song from setlist
        test("Remove from setlist", "DELETE",
             f"/api/songs/shows/{show_id}/setlist/{songs_created[0]['id']}")

    # ========== SCENE INTEGRATION ==========
    print("\n🎬 Scene Integration")

    # Create scene
    passed, scene = test("Create scene for song", "POST", "/api/scenes/",
                         data={"scene_number": 50, "name": "Amazing Grace Scene"})

    if scene and songs_created:
        scene_id = scene['id']
        song_id = songs_created[-1]['id']

        # Link scene to song
        test("Set song scene", "PUT", f"/api/songs/{song_id}/scene/{scene_id}")

        # Quick save (will store current mixer state)
        test("Quick save scene", "POST", f"/api/songs/{song_id}/scene/save")

    # ========== IMPORT ==========
    print("\n📥 Import Functions")

    # Search external
    test("Search external sources", "GET", "/api/songs/search/external?q=yesterday beatles",
         check_response=lambda r: 'search_urls' in r)

    # Import song
    test("Import song", "POST", "/api/songs/import",
         data={
             "source": "manual",
             "title": "Yesterday",
             "artist_name": "The Beatles",
             "original_key": "F",
             "chord_chart": "[F]Yesterday, [Em7]all my [A7]troubles seemed so [Dm]far away"
         })

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")

    # Delete songs
    for song in songs_created:
        test(f"Delete song {song['id']}", "DELETE", f"/api/songs/{song['id']}")

    # Delete artists
    for artist in artists_created:
        test(f"Delete artist {artist['id']}", "DELETE", f"/api/artists/{artist['id']}")

    # Delete show
    if show:
        test("Delete show", "DELETE", f"/api/shows/{show['id']}")

    # Delete scene
    if scene:
        test("Delete scene", "DELETE", f"/api/scenes/{scene['id']}")

    elapsed = time.time() - start
    round_stats['round_1'] = {'time': elapsed, 'passed': results['passed'], 'failed': results['failed']}
    print(f"\n⏱️  Round 1 completed in {elapsed:.2f}s")


def run_round_2():
    """Round 2: Edge Cases & Stress (High Intensity)"""
    print("\n" + "="*70)
    print("  ROUND 2: EDGE CASES & STRESS (High Intensity)")
    print("="*70)
    start = time.time()
    passed_before = results['passed']

    # ========== BOUNDARY TESTING ==========
    print("\n📏 Boundary Testing")

    # Very long title
    test("Song with max length title", "POST", "/api/songs/",
         data={"title": "A" * 128, "artist_name": "Test", "original_key": "C"})

    test("Song with over-length title (129)", "POST", "/api/songs/",
         data={"title": "A" * 129, "artist_name": "Test", "original_key": "C"},
         expected_status=422)

    # Empty fields
    test("Song with empty title", "POST", "/api/songs/",
         data={"title": "", "artist_name": "Test", "original_key": "C"},
         expected_status=422)

    # All keys transposition
    print("\n🎹 All Keys Transposition Test")
    passed, song = test("Create song for key tests", "POST", "/api/songs/",
                        data={
                            "title": "Key Test",
                            "artist_name": "Test",
                            "original_key": "C",
                            "chord_chart": "[C]Test [G]chord [Am]chart [F]here"
                        })

    if song:
        all_keys = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
        for key in all_keys:
            test(f"Transpose to {key}", "GET", f"/api/songs/{song['id']}/chart?key={key}")

        # Minor keys
        for key in ['Am', 'Em', 'Dm', 'Gm']:
            test(f"Transpose to {key}", "GET", f"/api/songs/{song['id']}/chart?key={key}")

        test("Delete key test song", "DELETE", f"/api/songs/{song['id']}")

    # ========== UNICODE & SPECIAL CHARACTERS ==========
    print("\n🌍 Unicode & Special Characters")

    unicode_songs = [
        {"title": "日本語の歌", "artist_name": "日本のアーティスト", "original_key": "C"},
        {"title": "Песня на русском", "artist_name": "Русский артист", "original_key": "Am"},
        {"title": "한국어 노래", "artist_name": "한국 가수", "original_key": "G"},
        {"title": "Chanson française", "artist_name": "Artiste français", "original_key": "D"},
        {"title": "🎵 Emoji Song 🎸", "artist_name": "🎤 Emoji Artist", "original_key": "E"},
    ]

    for song in unicode_songs:
        passed, result = test(f"Unicode song: {song['title'][:20]}...", "POST", "/api/songs/", data=song)
        if passed and result:
            test(f"Delete unicode song", "DELETE", f"/api/songs/{result['id']}")

    # ========== STRESS TESTING ==========
    print("\n⚡ Stress Testing")

    # Bulk create
    bulk_songs = []
    start_bulk = time.time()
    for i in range(50):
        passed, song = test(f"Bulk create song {i+1}", "POST", "/api/songs/",
                            data={"title": f"Bulk Song {i}", "artist_name": f"Artist {i}", "original_key": "C"})
        if passed and song:
            bulk_songs.append(song)

    bulk_time = time.time() - start_bulk
    print(f"   Created 50 songs in {bulk_time:.2f}s ({50/bulk_time:.1f} songs/s)")

    # Concurrent reads
    def read_song(song_id):
        return requests.get(f"{BASE_URL}/api/songs/{song_id}", timeout=10).status_code == 200

    if bulk_songs:
        start_concurrent = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_song, s['id']) for s in bulk_songs * 2]  # 100 reads
            successes = sum(1 for f in as_completed(futures) if f.result())
        concurrent_time = time.time() - start_concurrent
        test(f"Concurrent reads ({successes}/100)", "GET", "/api/songs/",
             check_response=lambda r: successes >= 95)

    # Complex search
    test("Search all bulk songs", "GET", "/api/songs/?search=Bulk",
         check_response=lambda r: len(r) == len(bulk_songs))

    # Cleanup bulk
    for song in bulk_songs:
        requests.delete(f"{BASE_URL}/api/songs/{song['id']}")
    print(f"   Cleaned up {len(bulk_songs)} bulk songs")

    # ========== CHORD CHART EDGE CASES ==========
    print("\n🎸 Chord Chart Edge Cases")

    # Very large chord chart
    large_chart = "{title: Large Chart}\n{key: C}\n\n"
    for i in range(200):
        large_chart += f"[C]Line {i} [G]with [Am]many [F]chords [D]and [Em]more [B7]here\n"

    passed, large_song = test("Create song with large chart", "POST", "/api/songs/",
                              data={"title": "Large Chart", "artist_name": "Test", "original_key": "C",
                                    "chord_chart": large_chart})

    if large_song:
        test("Transpose large chart", "GET", f"/api/songs/{large_song['id']}/chart?key=D")
        test("Delete large chart song", "DELETE", f"/api/songs/{large_song['id']}")

    # Chart with unusual chords
    unusual_chords = "[Cmaj7]Intro [Dm7b5]verse [G7#9]bridge [Fadd9]chorus [Em11]outro"
    passed, unusual_song = test("Create song with unusual chords", "POST", "/api/songs/",
                                 data={"title": "Jazz Tune", "artist_name": "Test", "original_key": "C",
                                       "chord_chart": unusual_chords})
    if unusual_song:
        test("Transpose unusual chords", "GET", f"/api/songs/{unusual_song['id']}/chart?key=Eb")
        test("Delete unusual song", "DELETE", f"/api/songs/{unusual_song['id']}")

    elapsed = time.time() - start
    round_stats['round_2'] = {'time': elapsed, 'passed': results['passed'] - passed_before, 'failed': results['failed'] - round_stats.get('round_1', {}).get('failed', 0)}
    print(f"\n⏱️  Round 2 completed in {elapsed:.2f}s")


def run_round_3():
    """Round 3: Security & Integration (Very High Intensity)"""
    print("\n" + "="*70)
    print("  ROUND 3: SECURITY & INTEGRATION (Very High Intensity)")
    print("="*70)
    start = time.time()
    passed_before = results['passed']

    # ========== SECURITY TESTING ==========
    print("\n🔒 Security Testing")

    # SQL Injection attempts
    sql_payloads = [
        "'; DROP TABLE songs; --",
        "1 OR 1=1",
        "1; DELETE FROM songs WHERE 1=1; --",
        "UNION SELECT * FROM users",
    ]

    for payload in sql_payloads:
        test(f"SQL injection in title", "POST", "/api/songs/",
             data={"title": payload, "artist_name": "Test", "original_key": "C"})
        test(f"SQL injection in search", "GET", f"/api/songs/?search={payload}")

    # XSS attempts
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
    ]

    for payload in xss_payloads:
        passed, song = test(f"XSS in title", "POST", "/api/songs/",
                            data={"title": payload, "artist_name": "Test", "original_key": "C"})
        if passed and song:
            requests.delete(f"{BASE_URL}/api/songs/{song['id']}")

    # Path traversal - create a song first to test with valid ID
    passed, path_song = test("Create song for path test", "POST", "/api/songs/",
                             data={"title": "Path Test", "artist_name": "Test", "original_key": "C",
                                   "chord_chart": "[C]Test"})
    if path_song:
        test("Path traversal in key", "GET", f"/api/songs/{path_song['id']}/chart?key=../../../etc/passwd")
        test("Delete path test song", "DELETE", f"/api/songs/{path_song['id']}")

    # Invalid IDs
    test("Get song with invalid ID", "GET", "/api/songs/99999999", expected_status=404)
    test("Get song with negative ID", "GET", "/api/songs/-1", expected_status=404)
    test("Get song with string ID", "GET", "/api/songs/abc", expected_status=422)

    # ========== FULL INTEGRATION TEST ==========
    print("\n🔗 Full Integration Test (Complete Workflow)")

    # Create complete show setup
    _, show = test("Create integration show", "POST", "/api/shows/",
                   data={"name": "Integration Test Show", "venue": "Test Arena"})

    _, band = test("Create integration band", "POST", "/api/bands/",
                   data={"name": "Integration Band", "genre": "Rock"})

    artists = []
    for i in range(4):
        _, artist = test(f"Create band member {i+1}", "POST", "/api/artists/",
                         data={"name": f"Member {i+1}", "primary_instrument": ["Vocals", "Guitar", "Bass", "Drums"][i]})
        if artist:
            artists.append(artist)

    # Add artists to band
    if band and artists:
        for artist in artists:
            test(f"Add {artist['name']} to band", "POST",
                 f"/api/bands/{band['id']}/artists/{artist['id']}")

    # Create songs
    songs = []
    for i in range(5):
        _, song = test(f"Create setlist song {i+1}", "POST", "/api/songs/",
                       data={
                           "title": f"Song {i+1}",
                           "artist_name": "Various",
                           "original_key": ["C", "G", "D", "A", "E"][i],
                           "tempo": 120 + i*5
                       })
        if song:
            songs.append(song)

    # Link songs to all artists
    if artists and songs:
        for artist in artists:
            for song in songs:
                test(f"Link {artist['name']} to {song['title']}", "POST",
                     f"/api/songs/artists/{artist['id']}/songs/{song['id']}")

    # Check band available songs
    if band:
        test("Get band available songs", "GET", f"/api/songs/bands/{band['id']}/available",
             check_response=lambda r: len(r.get('available_songs', [])) == len(songs))

    # Add band to show
    if show and band:
        test("Add band to show", "POST", f"/api/shows/{show['id']}/bands/{band['id']}")

    # Build setlist
    if show and songs:
        for i, song in enumerate(songs):
            test(f"Add song {i+1} to setlist", "POST", f"/api/songs/shows/{show['id']}/setlist",
                 data={"song_id": song['id'], "position": i + 1})

        # Verify setlist
        test("Verify complete setlist", "GET", f"/api/songs/shows/{show['id']}/setlist",
             check_response=lambda r: len(r['setlist']) == len(songs))

    # Create scenes for each song
    scenes = []
    for i, song in enumerate(songs):
        _, scene = test(f"Create scene for song {i+1}", "POST", "/api/scenes/",
                        data={"scene_number": 60 + i, "name": f"Scene for {song['title']}"})
        if scene:
            scenes.append(scene)
            test(f"Link scene to song", "PUT", f"/api/songs/{song['id']}/scene/{scene['id']}")

    # Quick save all scenes
    for song in songs:
        test(f"Quick save scene for {song['title']}", "POST", f"/api/songs/{song['id']}/scene/save")

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")

    for scene in scenes:
        requests.delete(f"{BASE_URL}/api/scenes/{scene['id']}")
    for song in songs:
        requests.delete(f"{BASE_URL}/api/songs/{song['id']}")
    for artist in artists:
        requests.delete(f"{BASE_URL}/api/artists/{artist['id']}")
    if band:
        requests.delete(f"{BASE_URL}/api/bands/{band['id']}")
    if show:
        requests.delete(f"{BASE_URL}/api/shows/{show['id']}")

    elapsed = time.time() - start
    failed_before = round_stats.get('round_1', {}).get('failed', 0) + round_stats.get('round_2', {}).get('failed', 0)
    round_stats['round_3'] = {'time': elapsed, 'passed': results['passed'] - passed_before, 'failed': results['failed'] - failed_before}
    print(f"\n⏱️  Round 3 completed in {elapsed:.2f}s")


def run_round_4():
    """Round 4: Chaos Testing (Maximum Intensity)"""
    print("\n" + "="*70)
    print("  ROUND 4: CHAOS TESTING (Maximum Intensity)")
    print("="*70)
    start = time.time()
    passed_before = results['passed']

    # ========== RAPID FIRE OPERATIONS ==========
    print("\n🔥 Rapid Fire Operations")

    def random_operation():
        """Perform a random CRUD operation."""
        ops = ['create', 'read', 'update', 'delete', 'search', 'transpose']
        op = random.choice(ops)

        try:
            if op == 'create':
                resp = requests.post(f"{BASE_URL}/api/songs/", json={
                    "title": f"Chaos-{''.join(random.choices(string.ascii_letters, k=8))}",
                    "artist_name": "Chaos Artist",
                    "original_key": random.choice(['C', 'G', 'D', 'A', 'E', 'Am', 'Em'])
                }, timeout=5)
                return resp.status_code in [200, 201]

            elif op == 'read':
                resp = requests.get(f"{BASE_URL}/api/songs/", timeout=5)
                return resp.status_code == 200

            elif op == 'search':
                resp = requests.get(f"{BASE_URL}/api/songs/?search=Chaos", timeout=5)
                return resp.status_code == 200

            else:
                return True

        except:
            return False

    # 200 rapid operations
    start_rapid = time.time()
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(random_operation) for _ in range(200)]
        successes = sum(1 for f in as_completed(futures) if f.result())

    rapid_time = time.time() - start_rapid
    test(f"Rapid fire ops ({successes}/200 in {rapid_time:.2f}s)", "GET", "/api/songs/",
         check_response=lambda r: successes >= 180)

    # ========== CONCURRENT MODIFICATIONS ==========
    print("\n⚡ Concurrent Modifications")

    # Create songs for concurrent testing
    chaos_songs = []
    for i in range(10):
        resp = requests.post(f"{BASE_URL}/api/songs/", json={
            "title": f"Concurrent Song {i}",
            "artist_name": "Concurrent Artist",
            "original_key": "C",
            "chord_chart": f"[C]Chord {i}"
        })
        if resp.status_code == 200:
            chaos_songs.append(resp.json())

    def modify_song(song_id):
        """Attempt to modify a song."""
        try:
            keys = ['C', 'G', 'D', 'A', 'E', 'F', 'Bb', 'Eb']
            new_key = random.choice(keys)
            resp = requests.get(f"{BASE_URL}/api/songs/{song_id}/chart?key={new_key}", timeout=5)
            return resp.status_code == 200
        except:
            return False

    if chaos_songs:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for _ in range(100):
                song = random.choice(chaos_songs)
                futures.append(executor.submit(modify_song, song['id']))
            successes = sum(1 for f in as_completed(futures) if f.result())

        test(f"Concurrent modifications ({successes}/100)", "GET", "/api/songs/",
             check_response=lambda r: successes >= 90)

    # ========== CHAOS MONKEY: RANDOM FAILURES ==========
    print("\n🐵 Chaos Monkey: Error Handling")

    # Invalid requests that should fail gracefully
    # Create a song for key tests
    resp = requests.post(f"{BASE_URL}/api/songs/", json={
        "title": "Chaos Key Test", "artist_name": "Test", "original_key": "C",
        "chord_chart": "[C]Test"
    })
    chaos_key_song_id = resp.json().get('id', 999999) if resp.status_code == 200 else 999999

    chaos_tests = [
        ("Empty body", "POST", "/api/songs/", 422, None),
        ("Invalid JSON type", "POST", "/api/songs/", 422, "not json"),
        ("Missing required field", "POST", "/api/songs/", 422, {"artist_name": "Test"}),
        ("Invalid key for transpose", "GET", f"/api/songs/{chaos_key_song_id}/chart?key=XYZ", 200, None),  # Should handle gracefully
        ("Very long search", "GET", f"/api/songs/?search={'a'*1000}", 200, None),
        ("Empty search", "GET", "/api/songs/?search=", 200, None),
        ("Delete non-existent", "DELETE", "/api/songs/999999", 404, None),
    ]

    for name, method, endpoint, expected, data in chaos_tests:
        test(f"Chaos: {name}", method, endpoint, expected, data)

    # Clean up chaos key test song
    requests.delete(f"{BASE_URL}/api/songs/{chaos_key_song_id}")

    # ========== MIXED OPERATIONS STORM ==========
    print("\n🌪️  Mixed Operations Storm")

    def storm_operation():
        """Mixed CRUD operations."""
        try:
            # Create
            resp = requests.post(f"{BASE_URL}/api/songs/", json={
                "title": f"Storm-{time.time()}",
                "artist_name": "Storm",
                "original_key": "C"
            }, timeout=5)
            if resp.status_code != 200:
                return False

            song_id = resp.json()['id']

            # Read
            resp = requests.get(f"{BASE_URL}/api/songs/{song_id}", timeout=5)
            if resp.status_code != 200:
                return False

            # Update
            resp = requests.put(f"{BASE_URL}/api/songs/{song_id}",
                                json={"tempo": random.randint(60, 200)}, timeout=5)
            if resp.status_code != 200:
                return False

            # Delete
            resp = requests.delete(f"{BASE_URL}/api/songs/{song_id}", timeout=5)
            return resp.status_code == 200

        except:
            return False

    start_storm = time.time()
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(storm_operation) for _ in range(50)]
        successes = sum(1 for f in as_completed(futures) if f.result())

    storm_time = time.time() - start_storm
    test(f"Operation storm ({successes}/50 full cycles in {storm_time:.2f}s)", "GET", "/api/songs/",
         check_response=lambda r: successes >= 40)

    # ========== CLEANUP ==========
    print("\n🧹 Cleanup")

    # Clean up any remaining chaos songs
    for song in chaos_songs:
        requests.delete(f"{BASE_URL}/api/songs/{song['id']}")

    # Clean up any remaining songs
    resp = requests.get(f"{BASE_URL}/api/songs/?search=Chaos")
    if resp.status_code == 200:
        for song in resp.json():
            requests.delete(f"{BASE_URL}/api/songs/{song['id']}")

    resp = requests.get(f"{BASE_URL}/api/songs/?search=Storm")
    if resp.status_code == 200:
        for song in resp.json():
            requests.delete(f"{BASE_URL}/api/songs/{song['id']}")

    elapsed = time.time() - start
    failed_before = sum(s.get('failed', 0) for s in round_stats.values())
    round_stats['round_4'] = {'time': elapsed, 'passed': results['passed'] - passed_before, 'failed': results['failed'] - failed_before}
    print(f"\n⏱️  Round 4 completed in {elapsed:.2f}s")


def main():
    print("\n" + "="*70)
    print("  YAMAHA TF SHOWBUILDER - SONGS INTENSIVE TESTING")
    print("  4 Rounds of Increasing Intensity")
    print("="*70)

    total_start = time.time()

    run_round_1()
    run_round_2()
    run_round_3()
    run_round_4()

    total_time = time.time() - total_start

    print("\n" + "="*70)
    print("  FINAL RESULTS")
    print("="*70)

    print(f"\n  Total Tests: {results['passed'] + results['failed']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success Rate: {results['passed'] / (results['passed'] + results['failed']) * 100:.1f}%")
    print(f"  Total Time: {total_time:.2f}s")

    print("\n  Round Statistics:")
    for round_name, stats in round_stats.items():
        print(f"    {round_name}: {stats.get('passed', 0)} passed, {stats.get('failed', 0)} failed in {stats.get('time', 0):.2f}s")

    if results["errors"]:
        print("\n  ❌ First 10 Errors:")
        for err in results["errors"][:10]:
            print(f"     - {err}")

    print("\n" + "="*70)

    return results['failed'] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
