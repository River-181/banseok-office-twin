# Banseok 3F Office 3D Model — Project Context

## Goal
Web-viewable 3D model of the new NTS office (Daejeon, 북유성대로 336, 3F, ~21.35 x 15.55 m) plus surrounding terrain, so staff can preview seats, routes and atmosphere. Accuracy of layout > photorealism.

## Source of truth
- **The local folder is canonical (정본).** Every change lands here first; sandbox copies and the online artifact are derived. After any change, update the affected docs/logs here in the same session.
- `04_데이터/floorplan_3F.json` is the ONLY geometry source. Never hand-edit derived files (SVG/PNG/GLB/HTML).
- `04_데이터/org.json` holds people, teams, vehicles; `좌석배정.csv` holds seat names. Both are local-only: public builds (`build_viewer.py --public`) must never contain names.
- Furniture sizes come from `CATALOG` in build_plan.py (standard specs); change sizes there, not per item.
- Build chain (regenerates JSON, SVG, PNG, GLB, both viewers): build_plan.py → build_glb.py → build_viewer.py → build_viewer.py --public
- Edit geometry in `05_코드/build_plan.py`, then regenerate. Record every non-trivial change in `01_기획/결정로그.md`.
- Original drawing is NOT to scale: dimension labels win; unlabeled = local proportion; furniture snapped to standard sizes.
- Units cm. Origin = NW inner corner of drawing. x = drawing right, y = drawing down. True north unverified.
- `conf: "low"` fields are assumptions. Check `01_기획/질문-답변.md` before treating them as facts.

## Folder map
_trash soft-deleted files (River empties) · _archive/zip delivered zips (dated, read-only) · 01_기획 plan, decisions, Q&A · 02_자료 raw inputs (read-only) · 03_전처리 rectified image + tiles · 04_데이터 JSON/clean plan · 05_코드 scripts + viewer · 06_지형 GIS raw/processed · 07_산출물 glb/renders · 08_세션로그 one file per session

## Token rules
1. Read JSON, not images. Only `plan-auditor` looks at images, and only the relevant tile from `03_전처리/tiles/`.
2. Prefer deterministic scripts (validation, geometry) over LLM reasoning for numbers.
3. Delegate by task type (see Agents). Subagents return short summaries (<15 lines), not full dumps.
4. Do not re-read `02_자료/원본` unless the user asks or a conflict needs the original.
5. Never put venv, node_modules or large caches inside this folder (iCloud sync). venv lives at `~/.venvs/banseok3d`.

## Deletion rule
Never hard-delete (`rm`) anything in this folder. Move it to `_trash/` with a date prefix (`YYMMDD_<original name>`) and mention it in the session log. Only River empties `_trash/` (iCloud syncs deletions to every device).

## Agents (.claude/agents)
| agent | model | use for |
|---|---|---|
| plan-auditor | opus | reading drawing/photos, JSON vs original cross-check |
| geometry-builder | sonnet | JSON -> glTF/GLB generation, validation scripts |
| viewer-builder | sonnet | single-file three.js viewer (CDN, no build step) |
| site-terrain | sonnet | GIS/DEM fetch & conversion for surroundings |
| scribe | haiku | session logs, decision log, Q&A file upkeep |

## Session protocol (River's convention)
- Start: `SessionID: PCC-YYMMDD-NTS-3D-NN` + one-line Goal.
- End: scribe writes `08_세션로그/<SessionID>.md` with CloseSummary (변경점 / 산출물 / 다음행동) and updates `00_README.md` status.
- Milestone gate: finish and confirm one milestone before starting the next (M1..M6 in the plan).

## Communication
Reply to River in Korean, casual tone, conclusion first. Keep technical terms in English. River is ~6 months into coding: add a one-line "why" for advanced concepts. Code: minimal comments, intention-revealing names, build step by step.
