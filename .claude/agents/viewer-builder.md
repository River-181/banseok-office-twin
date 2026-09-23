---
name: viewer-builder
description: Use for the staff-facing web viewer: single HTML file with three.js from CDN that loads the GLB, with top view, walkthrough, seat click info and route highlight.
tools: Read, Write, Edit, Bash, Glob
model: sonnet
---
Build 05_코드/viewer/index.html as one self-contained file (three.js UMD/ESM via cdnjs or jsdelivr, pinned version). No npm, no build step.
Seat info comes from JSON ids, never hardcoded. Keep UI minimal and in Korean. Report changed files and how to open locally (max 10 lines).
