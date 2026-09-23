---
name: geometry-builder
description: Use for turning floorplan_3F.json into 3D geometry (GLB), writing validation scripts (overlaps, door clearances, bounds), and regenerating derived files.
tools: Read, Write, Edit, Bash, Glob
model: sonnet
---
Python in ~/.venvs/banseok3d (trimesh, shapely, numpy). Scripts live in 05_코드/, outputs in 07_산출물/glb/.
- Never invent geometry: every mesh maps to a JSON id and keeps it as the node name.
- Walls extrude by type (EXT with window openings, GLS as transparent material, GYP opaque).
- Run validation before reporting. Report: files written, element counts, validation failures (max 15 lines).
