import asyncio
import json
from dataclasses import dataclass
from typing import Any

# SSE audience tags. Every subscriber is classified at subscribe time so the
# server can route events by audience instead of broadcasting everything to
# everyone (010-hardening-and-polish, FR-001..FR-004).
OPERATOR = "operator"
PARTICIPANT = "participant"


@dataclass
class _Subscriber:
    queue: "asyncio.Queue[str]"
    audience: str
    participant_id: str | None = None


_subscribers: list[_Subscriber] = []


def subscribe(
    audience: str = PARTICIPANT,
    participant_id: str | None = None,
) -> "asyncio.Queue[str]":
    """Register an SSE subscriber.

    Defaults to the least-privileged audience (``participant``) so an ambiguous
    caller never receives operator-only events.
    """
    queue: asyncio.Queue[str] = asyncio.Queue()
    _subscribers.append(
        _Subscriber(queue=queue, audience=audience, participant_id=participant_id)
    )
    return queue


def unsubscribe(queue: "asyncio.Queue[str]") -> None:
    for sub in list(_subscribers):
        if sub.queue is queue:
            _subscribers.remove(sub)


def _put(sub: _Subscriber, message: str) -> None:
    try:
        sub.queue.put_nowait(message)
    except asyncio.QueueFull:
        pass


def format_state_event(state: Any) -> str:
    if hasattr(state, "model_dump"):
        payload = state.model_dump(mode="json")
    else:
        payload = state
    return f"event: state\ndata: {json.dumps(payload)}\n\n"


def broadcast_state(state: Any) -> None:
    """`state` is public to every authorized subscriber (operator + participant)."""
    message = format_state_event(state)
    for sub in list(_subscribers):
        _put(sub, message)


def format_notification_event(notification: Any) -> str:
    if hasattr(notification, "model_dump"):
        payload = notification.model_dump(mode="json")
    else:
        payload = notification
    return f"event: notification\ndata: {json.dumps(payload)}\n\n"


def deliver_notification(participant_id: str, notification: Any) -> None:
    """Deliver a notification ONLY to the target participant's subscribers.

    Other participants, operators, and kiosk clients never receive it.
    """
    if not participant_id:
        return
    message = format_notification_event(notification)
    for sub in list(_subscribers):
        if sub.audience == PARTICIPANT and sub.participant_id == participant_id:
            _put(sub, message)


def format_api_key_usage_event(usage: Any) -> str:
    if hasattr(usage, "model_dump"):
        payload = usage.model_dump(mode="json")
    else:
        payload = usage
    return f"event: api_key_usage\ndata: {json.dumps(payload)}\n\n"


def broadcast_api_key_usage(usage: Any) -> None:
    """API-key usage is operator-only; participant streams never receive it."""
    message = format_api_key_usage_event(usage)
    for sub in list(_subscribers):
        if sub.audience == OPERATOR:
            _put(sub, message)
