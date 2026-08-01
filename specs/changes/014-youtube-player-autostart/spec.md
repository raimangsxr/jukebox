---
id: 014-youtube-player-autostart
type: change
status: implemented
modifies:
  - backend-api
  - app-core
  - ops-platform
depends_on:
  - 004-kiosk-display-queue
  - 013-queue-approval-mode
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Auto-arranque del player YouTube

**Feature Branch**: `014-youtube-player-autostart`

**Created**: 2026-07-30

**Status**: Implemented

**Input**: El operador controla el evento solo desde móvil; la pantalla kiosk no recibe gestos físicos. La cola puede tener canciones pero el player muestra «Esperando canción» hasta un `Iniciar reproducción` manual. El player debe auto-arrancar al encolar y resistir políticas de autoplay del navegador.

## Problem

- `queue` (entradas `queued`) y `now_playing` son estados distintos; aprobar o enviar en modo Libre solo encola.
- El overlay «Activar reproducción» bloquea la creación del player hasta un gesto en el kiosk.
- Sin gesto en el display, Chrome bloquea autoplay con sonido.

## Goals

- Al encolar la primera canción mientras idle, promover automáticamente a `playing` (SSE actualiza kiosk).
- En el gesto de activación del kiosk, si hay cola sin `now_playing`, iniciar reproducción.
- Player arranca en mute sin overlay bloqueante; overlay solo para **Activar sonido**.
- Admin muestra estado de reproducción explícito.
- Documentar Chromium kiosk y `allow=autoplay` en iframe para producción.

## Non-Goals

- `bull:config` / `bull:resize` postMessage.
- Heartbeat `player_status` al backend (iteración 3 opcional — fuera de v1).
- Audio en el móvil admin.

## Acceptance

- Aprobar pendiente con cola idle → `GET /api/state` tiene `now_playing`.
- Free submit con cola idle → `now_playing` set.
- Aprobar con algo ya `playing` → solo encola, `now_playing` unchanged.
- Display: vídeo arranca muteado sin overlay bloqueante cuando hay `videoId`.
- Overlay «Activar sonido» desbloquea audio tras gesto.
- Admin: «Sonando: …» o «Cola lista — N canciones en espera».
