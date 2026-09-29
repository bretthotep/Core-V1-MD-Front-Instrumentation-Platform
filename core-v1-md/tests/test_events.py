import threading

from core.events import Event, EventBus, EventType


def test_publish_to_specific_and_wildcard_subscribers():
    bus = EventBus()
    specific, everything = [], []
    bus.subscribe(EventType.APP_LAUNCHED, specific.append)
    bus.subscribe(None, everything.append)
    bus.emit(EventType.APP_LAUNCHED, app="game.exe")
    bus.emit(EventType.HIGH_TEMP, sensor="cpu")
    assert [e.payload["app"] for e in specific] == ["game.exe"]
    assert [e.type for e in everything] == [EventType.APP_LAUNCHED, EventType.HIGH_TEMP]


def test_unsubscribe():
    bus = EventBus()
    seen = []
    unsubscribe = bus.subscribe(EventType.SYSTEM_START, seen.append)
    unsubscribe()
    bus.emit(EventType.SYSTEM_START)
    assert seen == []


def test_post_is_deferred_until_dispatch_and_thread_safe():
    bus = EventBus()
    seen = []
    bus.subscribe(None, seen.append)
    threads = [threading.Thread(target=bus.post, args=(Event(EventType.NETWORK_CONNECTED),)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert seen == []
    assert bus.dispatch_pending() == 10
    assert len(seen) == 10


def test_failing_handler_does_not_break_other_handlers():
    bus = EventBus()
    seen = []

    def broken(_event):
        raise RuntimeError("boom")

    bus.subscribe(EventType.HIGH_TEMP, broken)
    bus.subscribe(EventType.HIGH_TEMP, seen.append)
    bus.emit(EventType.HIGH_TEMP)
    assert len(seen) == 1


def test_all_required_event_types_exist():
    names = {e.name for e in EventType}
    assert {
        "APP_LAUNCHED", "APP_CLOSED", "SYSTEM_START", "SYSTEM_SHUTDOWN",
        "NETWORK_CONNECTED", "NETWORK_DISCONNECTED", "HIGH_TEMP", "LOW_FAN_SPEED",
    } <= names
