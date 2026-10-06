"""Telemetry hub: merges providers and derives application events."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from core.events import Event, EventBus, EventType
from telemetry.audio import AudioSource
from telemetry.models import TelemetrySnapshot
from telemetry.provider import TelemetryProvider

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Thresholds:
    high_temp_c: float = 85.0
    high_temp_clear_c: float = 80.0  # hysteresis: must drop below this to re-arm
    low_fan_rpm: float = 300.0

    def __post_init__(self) -> None:
        if self.high_temp_clear_c > self.high_temp_c:
            raise ValueError("high_temp_clear_c must not exceed high_temp_c")
        if self.low_fan_rpm < 0:
            raise ValueError("low_fan_rpm must be >= 0")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Thresholds:
        """Build thresholds from a mapping; missing keys keep their defaults."""
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"$comment"}
        if unknown:
            raise ValueError(f"unknown threshold keys: {', '.join(sorted(unknown))}")
        values: dict[str, float] = {}
        for key in known & set(data):
            value = data[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"threshold {key!r} must be a number")
            values[key] = float(value)
        return cls(**values)

    @classmethod
    def load(cls, path: str | Path) -> Thresholds:
        """Load thresholds from a JSON object file (see ``telemetry/thresholds.json``)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: thresholds file must contain a JSON object")
        return cls.from_dict(data)


class TelemetryHub:
    """Polls providers, keeps the latest merged snapshot and posts events.

    Derived events (all posted to the :class:`EventBus` queue):

    * ``APP_LAUNCHED`` / ``APP_CLOSED`` – changes to the running application set
    * ``NETWORK_CONNECTED`` / ``NETWORK_DISCONNECTED`` – link state edges
    * ``HIGH_TEMP`` – CPU/GPU temperature crosses the threshold (with hysteresis)
    * ``LOW_FAN_SPEED`` – a fan drops below the minimum RPM
    """

    def __init__(
        self,
        bus: EventBus,
        providers: Iterable[TelemetryProvider] = (),
        audio: AudioSource | None = None,
        thresholds: Thresholds | None = None,
    ) -> None:
        self.bus = bus
        self.providers: list[TelemetryProvider] = list(providers)
        self.audio = audio
        self.thresholds = thresholds or Thresholds()
        self._snapshot = TelemetrySnapshot()
        self._primed = False
        self._hot: set[str] = set()
        self._slow_fans: set[str] = set()

    @property
    def snapshot(self) -> TelemetrySnapshot:
        return self._snapshot

    def add_provider(self, provider: TelemetryProvider) -> None:
        self.providers.append(provider)

    def start(self) -> None:
        for provider in self.providers:
            try:
                provider.start()
            except Exception:
                log.exception("Telemetry provider %s failed to start", provider.name)
        if self.audio:
            try:
                self.audio.start()
            except Exception:
                log.exception("Audio source failed to start")

    def stop(self) -> None:
        for provider in self.providers:
            try:
                provider.stop()
            except Exception:
                log.exception("Telemetry provider %s failed to stop", provider.name)
        if self.audio:
            try:
                self.audio.stop()
            except Exception:
                log.exception("Audio source failed to stop")

    def poll(self, now: float) -> TelemetrySnapshot:
        merged = TelemetrySnapshot(timestamp=now)
        for provider in self.providers:
            try:
                merged = merged.merged_with(provider.poll(now))
            except Exception:
                log.exception("Telemetry provider %s failed", provider.name)
        merged = self._with_audio(merged, now)
        self._derive_events(self._snapshot, merged)
        self._snapshot = merged
        self._primed = True
        return merged

    def poll_audio(self, now: float) -> TelemetrySnapshot:
        """Refresh only the audio section (audio runs at frame rate, sensors slower)."""
        self._snapshot = self._with_audio(self._snapshot, now)
        return self._snapshot

    def _with_audio(self, snap: TelemetrySnapshot, now: float) -> TelemetrySnapshot:
        if self.audio is None:
            return snap
        return snap.merged_with(TelemetrySnapshot(timestamp=snap.timestamp, audio=self.audio.read_frame(now)))

    # ---- event derivation ----------------------------------------------
    def _post(self, event_type: EventType, **payload: object) -> None:
        self.bus.post(Event(event_type, dict(payload)))

    def _derive_events(self, old: TelemetrySnapshot, new: TelemetrySnapshot) -> None:
        t = self.thresholds
        if self._primed:
            if old.application and new.application:
                before, after = set(old.application.running), set(new.application.running)
                for app in [a for a in new.application.running if a not in before]:
                    self._post(EventType.APP_LAUNCHED, app=app)
                for app in [a for a in old.application.running if a not in after]:
                    self._post(EventType.APP_CLOSED, app=app)
            if old.network and new.network and old.network.connected != new.network.connected:
                kind = EventType.NETWORK_CONNECTED if new.network.connected else EventType.NETWORK_DISCONNECTED
                self._post(kind, adapter=new.network.adapter)

        for sensor, temp in (
            ("cpu", new.cpu.temperature_c if new.cpu else None),
            ("gpu", new.gpu.temperature_c if new.gpu else None),
        ):
            if temp is None:
                continue
            if sensor not in self._hot and temp >= t.high_temp_c:
                self._hot.add(sensor)
                self._post(EventType.HIGH_TEMP, sensor=sensor, value=temp)
            elif sensor in self._hot and temp < t.high_temp_clear_c:
                self._hot.discard(sensor)

        for fan in new.system.fans if new.system else ():
            if fan.name not in self._slow_fans and fan.rpm < t.low_fan_rpm:
                self._slow_fans.add(fan.name)
                self._post(EventType.LOW_FAN_SPEED, fan=fan.name, rpm=fan.rpm)
            elif fan.name in self._slow_fans and fan.rpm >= t.low_fan_rpm:
                self._slow_fans.discard(fan.name)
