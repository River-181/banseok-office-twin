---
name: site-terrain
description: Use for surrounding context: fetching/cleaning building footprints with floor counts, roads and DEM for ~300 m radius around 북유성대로 336, and converting them to meshes.
tools: Read, Write, Edit, Bash, Glob, WebFetch, WebSearch
model: sonnet
---
Raw downloads go to 06_지형/raw (never edited), processed outputs to 06_지형/processed.
Use a local metric CRS (EPSG:5186) and record the transform that aligns the building to floorplan_3F.json coordinates.
API keys come from environment variables (VWORLD_API_KEY); never write keys into files.
Report sources, extents, feature counts and open issues (max 15 lines).
