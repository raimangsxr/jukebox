import asyncio
import json
from typing import Any

_subscribers: list[asyncio.Queue[str]] = []


def format_state_event(state: Any) -> str:
    if hasattr(state, "model_dump"):
        payload = state.model_dump(mode="json")
    else:
        payload = state
    return f"event: state\ndata: {json.dumps(payload)}\n\n"


def subscribe() -> asyncio.Queue[str]:
    queue: asyncio.Queue[str] = asyncio.Queue()
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[str]) -> None:
    if queue in _subscribers:
        _subscribers.remove(queue)


def broadcast_state(state: Any) -> None:
    message = format_state_event(state)
    for queue in list(_subscribers):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass


def format_notification_event(notification: Any) -> str:
    if hasattr(notification, "model_dump"):
        payload = notification.model_dump(mode="json")
    else:
        payload = notification
    return f"event: notification\ndata: {json.dumps(payload)}\n\n"


def broadcast_notification(notification: Any) -> None:
    message = format_notification_event(notification)
    for queue in list(_subscribers):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass


def format_api_key_usage_event(usage: Any) -> str:
    if hasattr(usage, "model_dump"):
        payload = usage.model_dump(mode="json")
    else:
        payload = usage
    return f"event: api_key_usage\ndata: {json.dumps(payload)}\n\n"


def broadcast_api_key_usage(usage: Any) -> None:
    message = format_api_key_usage_event(usage)
    for queue in list(_subscribers):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass
