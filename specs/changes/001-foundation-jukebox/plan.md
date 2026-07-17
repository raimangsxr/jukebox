# Implementation Plan: amrn-jukebox Foundation

**Branch**: `001-foundation-jukebox` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/001-foundation-jukebox/spec.md`

## Context Grounding

- Manifest read: `specs/manifest.yml`
- Active contracts read: `backend-api`, `app-core`, `ops-platform` (baseline drafts)
- Change spec read: `spec.md` + clarifications session 2026-07-17
- Context pack: [context-pack.md](./context-pack.md)
- Sibling references: `amrn-bull` (monorepo, auth, SSE, iframe), `amrn-escalabirras-dual` (embed density), `kiosk-screen` CHG-042
- Research: [research.md](./research.md)
- Data model: [data-model.md](./data-model.md)
- Contract deltas: [contracts/contract-deltas.md](./contracts/contract-deltas.md)

## Summary

Establish the **amrn-jukebox monorepo** with SDD tooling, baseline contracts, FastAPI health service, Angular placeholder routes, and compose/Docker/CI skeleton. Lock the **product baseline** (moderated queue, voting, dual auth, notifications, kiosk embed) in spec and data model for changes 002+.

**This plan does not implement product features** beyond scaffold acceptance criteria (US-1).

## Technical Context

| Dimension | Value |
|-----------|-------|
| **Languages** | Python 3.12+, TypeScript / Angular 22 |
| **Backend** | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| **Frontend** | Angular standalone, TailwindCSS |
| **Storage** | PostgreSQL (compose); SQLite in-memory (pytest) |
| **Testing** | pytest (backend); `ng build` (frontend) |
| **Env prefix** | `JUKEBOX_` |
| **API prefix** | `/api/*` |

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Contracts as source of truth | Pass — baseline contracts created |
| II. Manifest-driven context | Pass — `manifest.yml` entry for 001 |
| III. Incremental changes | Pass — product deferred to 002+ |
| IV. Contract updates before impl | Pass — deltas documented; consolidate post-implement |
| V. Tests for changed behavior | Pass — `test_health.py` for 001 |
| VI. Sibling conventions | Pass — layout matches bull |

## Phase 0 — Research

Complete. See [research.md](./research.md).

## Phase 1 — Design artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `data-model.md` | Done |
| Contract deltas | `contracts/contract-deltas.md` | Done |
| Quickstart | `quickstart.md` | Done |
| Checklist | `checklists/requirements.md` | Done |

## Phase 2 — Implementation outline (001 only)

1. Root: `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`
2. Backend: `app/main.py`, health router, bootstrap, models, Alembic 0001, pytest
3. Frontend: Angular app, 4 route placeholders, Tailwind, build config
4. Ops: Dockerfiles, nginx, GitHub release workflow
5. SDD: `.specify/`, Spec Kit commands, analyze gate

## Phase 3 — Downstream changes (not 001)

| Change | Focus |
|--------|-------|
| 002 | Operator auth + embed tokens |
| 003 | Event config + SSE skeleton |
| 004 | Queue + moderation API |
| 005 | Voting + reorder |
| 006 | Google OAuth + `/participar` |
| 007 | Display UI + YouTube player |
| 008 | Notifications |
| 009 | kiosk-screen `amrn_jukebox` |

## Risks

| Risk | Mitigation |
|------|------------|
| Scaffold before analyze | Recorded in `analyze.md`; validate against tasks before marking 001 complete |
| Product spec mixed with 001 | Scope section + FR split (001 vs FR-P*) |
| No k8s manifests yet | Document in ops-platform deferred section |

## Validation

See [quickstart.md](./quickstart.md) and checklist implementation section.
