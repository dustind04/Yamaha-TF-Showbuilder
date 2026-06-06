"""
Chord Transposition and ChordPro Parsing Utilities.

Provides functions for:
- Transposing chord charts to different keys
- Parsing ChordPro format
- Converting between chord formats
"""

import re
from typing import List, Tuple, Optional, Dict

# Chromatic scale for transposition
CHROMATIC_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHROMATIC_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

# Map flats to sharps for consistent handling
FLAT_TO_SHARP = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'
}

# Map sharps to flats for output
SHARP_TO_FLAT = {v: k for k, v in FLAT_TO_SHARP.items()}

# Common chord qualities
CHORD_QUALITIES = [
    'maj7', 'min7', 'maj9', 'min9', 'maj11', 'min11', 'maj13', 'min13',
    'm7b5', 'dim7', 'aug7', '7sus4', '7sus2', 'add9', 'add11',
    'sus4', 'sus2', 'dim', 'aug', 'maj', 'min', '7', '9', '11', '13',
    'm7', 'm9', 'm', '6', '5', '2', '4'
]

# Sort by length (longest first) to match properly
CHORD_QUALITIES.sort(key=len, reverse=True)


def normalize_chord_root(root: str) -> str:
    """Normalize a chord root to sharp notation."""
    if len(root) > 1 and root[1] == 'b':
        return FLAT_TO_SHARP.get(root, root)
    return root


def get_semitones(from_key: str, to_key: str) -> int:
    """Calculate semitones between two keys."""
    from_normalized = normalize_chord_root(from_key.replace('m', ''))
    to_normalized = normalize_chord_root(to_key.replace('m', ''))

    try:
        from_idx = CHROMATIC_SHARP.index(from_normalized)
        to_idx = CHROMATIC_SHARP.index(to_normalized)
        return (to_idx - from_idx) % 12
    except ValueError:
        return 0


def transpose_chord_root(root: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose a chord root by given semitones."""
    normalized = normalize_chord_root(root)

    try:
        idx = CHROMATIC_SHARP.index(normalized)
        new_idx = (idx + semitones) % 12

        if use_flats:
            return CHROMATIC_FLAT[new_idx]
        return CHROMATIC_SHARP[new_idx]
    except ValueError:
        return root


def parse_chord(chord: str) -> Tuple[str, str, Optional[str]]:
    """
    Parse a chord into root, quality, and bass note.

    Returns: (root, quality, bass_note)
    Example: "Am7/G" -> ("A", "m7", "G")
    """
    if not chord:
        return ('', '', None)

    # Handle slash chords
    bass_note = None
    if '/' in chord:
        parts = chord.split('/')
        chord = parts[0]
        if len(parts) > 1 and parts[1]:
            bass_note = parts[1]

    # Extract root note
    root = chord[0].upper()
    rest = chord[1:]

    # Check for sharp/flat on root
    if rest and rest[0] in '#b':
        root += rest[0]
        rest = rest[1:]

    # The rest is the quality
    quality = rest

    return (root, quality, bass_note)


def build_chord(root: str, quality: str, bass_note: Optional[str] = None) -> str:
    """Build a chord string from components."""
    chord = root + quality
    if bass_note:
        chord += '/' + bass_note
    return chord


def transpose_chord(chord: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose a single chord by given semitones."""
    root, quality, bass = parse_chord(chord)

    if not root:
        return chord

    new_root = transpose_chord_root(root, semitones, use_flats)
    new_bass = transpose_chord_root(bass, semitones, use_flats) if bass else None

    return build_chord(new_root, quality, new_bass)


def transpose_chord_chart(chart: str, from_key: str, to_key: str) -> str:
    """
    Transpose an entire chord chart from one key to another.

    Handles ChordPro format with chords in [brackets].
    """
    semitones = get_semitones(from_key, to_key)

    if semitones == 0:
        return chart

    # Determine if target key typically uses flats
    use_flats = to_key in ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb',
                           'Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm']

    # Pattern to find chords in brackets
    chord_pattern = r'\[([A-Ga-g][#b]?[^\]]*)\]'

    def replace_chord(match):
        chord = match.group(1)
        transposed = transpose_chord(chord, semitones, use_flats)
        return f'[{transposed}]'

    return re.sub(chord_pattern, replace_chord, chart)


def transpose_to_key(chart: str, original_key: str, target_key: str) -> str:
    """
    Convenience function to transpose a chart to a new key.
    """
    return transpose_chord_chart(chart, original_key, target_key)


def parse_chordpro(text: str) -> Dict:
    """
    Parse a ChordPro format song into structured data.

    Returns dict with:
    - title: Song title
    - artist: Artist name
    - key: Original key
    - tempo: BPM if specified
    - sections: List of (section_name, lines) tuples
    - chords: List of unique chords used
    """
    result = {
        'title': '',
        'artist': '',
        'key': 'C',
        'tempo': None,
        'capo': None,
        'time': '4/4',
        'sections': [],
        'chords': set()
    }

    lines = text.split('\n')
    current_section = 'Intro'
    section_lines = []

    # Directive patterns
    directive_pattern = r'\{(\w+)(?::\s*(.+))?\}'
    chord_pattern = r'\[([A-Ga-g][#b]?[^\]]*)\]'

    for line in lines:
        line = line.strip()

        # Check for directives
        directive_match = re.match(directive_pattern, line)
        if directive_match:
            directive = directive_match.group(1).lower()
            value = directive_match.group(2) or ''

            if directive in ['title', 't']:
                result['title'] = value
            elif directive in ['artist', 'a', 'subtitle', 'st']:
                result['artist'] = value
            elif directive == 'key':
                result['key'] = value
            elif directive == 'tempo':
                try:
                    result['tempo'] = int(value)
                except:
                    pass
            elif directive == 'capo':
                try:
                    result['capo'] = int(value)
                except:
                    pass
            elif directive == 'time':
                result['time'] = value
            elif directive in ['start_of_chorus', 'soc']:
                if section_lines:
                    result['sections'].append((current_section, section_lines))
                current_section = 'Chorus'
                section_lines = []
            elif directive in ['end_of_chorus', 'eoc']:
                if section_lines:
                    result['sections'].append((current_section, section_lines))
                current_section = 'Verse'
                section_lines = []
            elif directive in ['start_of_verse', 'sov']:
                if section_lines:
                    result['sections'].append((current_section, section_lines))
                current_section = 'Verse'
                section_lines = []
            elif directive in ['start_of_bridge', 'sob']:
                if section_lines:
                    result['sections'].append((current_section, section_lines))
                current_section = 'Bridge'
                section_lines = []
            elif directive == 'comment' or directive == 'c':
                section_lines.append(f"({value})")
            continue

        # Extract chords from line
        chords = re.findall(chord_pattern, line)
        for chord in chords:
            root, quality, bass = parse_chord(chord)
            result['chords'].add(chord)

        # Add non-empty lines to current section
        if line:
            section_lines.append(line)

    # Add final section
    if section_lines:
        result['sections'].append((current_section, section_lines))

    # Convert chords set to sorted list
    result['chords'] = sorted(list(result['chords']))

    return result


def chordpro_to_text(chordpro: str) -> str:
    """
    Convert ChordPro format to readable text with chords above lyrics.
    """
    lines = []
    chord_pattern = r'\[([A-Ga-g][#b]?[^\]]*)\]'
    directive_pattern = r'\{(\w+)(?::\s*(.+))?\}'

    for line in chordpro.split('\n'):
        line = line.strip()

        # Skip or convert directives
        directive_match = re.match(directive_pattern, line)
        if directive_match:
            directive = directive_match.group(1).lower()
            value = directive_match.group(2) or ''

            if directive in ['title', 't']:
                lines.append(f"=== {value} ===")
                lines.append('')
            elif directive in ['start_of_chorus', 'soc']:
                lines.append('')
                lines.append('[CHORUS]')
            elif directive in ['start_of_verse', 'sov']:
                lines.append('')
                lines.append('[VERSE]')
            elif directive in ['start_of_bridge', 'sob']:
                lines.append('')
                lines.append('[BRIDGE]')
            elif directive == 'comment' or directive == 'c':
                lines.append(f"  ({value})")
            continue

        if not line:
            lines.append('')
            continue

        # Find all chords and their positions
        chords_with_pos = []
        for match in re.finditer(chord_pattern, line):
            chords_with_pos.append((match.start(), match.group(1)))

        if not chords_with_pos:
            lines.append(line)
            continue

        # Build chord line and lyric line
        chord_line = ''
        lyric_line = ''
        last_end = 0
        offset = 0

        for pos, chord in chords_with_pos:
            # Add spaces to chord line to align with position
            actual_pos = pos - offset
            while len(chord_line) < actual_pos:
                chord_line += ' '
            chord_line += chord + ' '
            offset += len(chord) + 2  # Account for [ and ]

        # Remove chord markers from lyric line
        lyric_line = re.sub(chord_pattern, '', line)

        lines.append(chord_line.rstrip())
        lines.append(lyric_line)

    return '\n'.join(lines)


def get_all_keys() -> List[str]:
    """Return list of all major and minor keys."""
    major = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    minor = [k + 'm' for k in major]
    return major + minor


def suggest_capo_position(original_key: str, target_key: str) -> Optional[int]:
    """
    Suggest a capo position to play a song in a different key
    using open chord shapes.

    Returns capo fret number, or None if no good option.
    """
    semitones = get_semitones(original_key, target_key)

    # Common open chord keys (easy to play)
    open_keys = {'C', 'G', 'D', 'A', 'E', 'Am', 'Em', 'Dm'}

    # Check if using a capo could give us an open key
    for capo in range(1, 8):
        effective_key = transpose_chord_root(target_key.replace('m', ''), -capo)
        if target_key.endswith('m'):
            effective_key += 'm'
        if effective_key in open_keys:
            return capo

    return None
