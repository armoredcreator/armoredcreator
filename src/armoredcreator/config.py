from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import SourceRoute


@dataclass(frozen=True)
class Settings:
    root: Path
    database_path: Path
    source_routes: tuple[SourceRoute, ...]
    vision_timeout_seconds: float = 30.0
    max_vision_attempts: int = 3
    audio_pt_br_threshold: float = 0.85

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        root = Path(env.get("ARMORED_ROOT", Path(__file__).resolve().parents[2])).expanduser().resolve()
        db_value = Path(env.get("ARMORED_DB_PATH", "storage/database/armoredcreator.db"))
        db_path = db_value if db_value.is_absolute() else (root / db_value).resolve()
        raw_routes = env.get("ARMORED_SOURCES_JSON", "[]")
        try:
            values = json.loads(raw_routes)
        except json.JSONDecodeError as exc:
            raise ValueError("ARMORED_SOURCES_JSON precisa conter JSON válido") from exc
        if not isinstance(values, list):
            raise ValueError("ARMORED_SOURCES_JSON precisa ser uma lista")
        routes: list[SourceRoute] = []
        seen: set[int] = set()
        for row in values:
            if not isinstance(row, dict):
                raise ValueError("Cada fonte deve ser um objeto JSON")
            try:
                route = SourceRoute(
                    source_id=int(row["source_id"]),
                    destination_id=int(row["destination_id"]),
                    topic_id=int(row["topic_id"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Cada fonte exige source_id, destination_id e topic_id inteiros") from exc
            if route.source_id in seen:
                raise ValueError(f"Fonte duplicada: {route.source_id}")
            seen.add(route.source_id)
            routes.append(route)
        return cls(
            root=root,
            database_path=db_path,
            source_routes=tuple(routes),
            vision_timeout_seconds=float(env.get("ARMORED_VISION_TIMEOUT", "30")),
            max_vision_attempts=int(env.get("ARMORED_VISION_MAX_ATTEMPTS", "3")),
            audio_pt_br_threshold=float(env.get("ARMORED_AUDIO_PT_BR_THRESHOLD", "0.85")),
        )
