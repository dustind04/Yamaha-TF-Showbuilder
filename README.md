# 3D Parts Generator

A web-based parametric 3D parts generator for creating printable replacement parts, mounts, organizers, enclosures, and more — without needing to learn CAD.

## How to Use

1. Open `index.html` in any modern browser (Chrome, Firefox, Edge)
2. Select a part type from the left panel
3. Enter your measurements in millimeters
4. Preview the part in real-time 3D
5. Click **Export STL** to download for your slicer

No installation, no accounts, no server required.

## Part Types

- **L-Bracket** — Simple angle brackets with mounting holes
- **U-Bracket** — Channel/U-shaped brackets
- **Flat Bracket** — Flat plates with mounting holes
- **Wall Mount** — Mount anything to a wall with screw holes
- **Shelf Bracket** — Triangular support brackets
- **Cable Organizer** — Multi-slot cable management clips
- **Grid Organizer** — Customizable grid boxes for parts/tools
- **Phone/Tablet Stand** — Adjustable device stands
- **Enclosure/Box** — Project boxes with optional lid
- **Pipe/Rod Clamp** — Clamps for round objects
- **Adapter Ring** — Convert between two diameters
- **Spacer/Washer** — Custom spacers and washers
- **Hinge** — Simple print-in-place hinges
- **Hook** — Wall hooks with customizable dimensions
- **Knob/Handle** — Replacement knobs and handles

## Tech Stack

- Pure HTML/CSS/JavaScript (no build step)
- [Three.js](https://threejs.org/) for 3D rendering
- CSG (Constructive Solid Geometry) for boolean operations
- Client-side STL export

## License

MIT
