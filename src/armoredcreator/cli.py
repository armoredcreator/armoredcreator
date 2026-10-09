from __future__ import annotations

import argparse
import json

from .config import Settings
from .db import Database


def main() -> int:
    parser = argparse.ArgumentParser(prog="armoredcreator")
    parser.add_argument("command", choices=("check", "status"), nargs="?", default="check")
    args = parser.parse_args()
    settings = Settings.from_env()
    db = Database(settings.database_path)
    if args.command == "check":
        print(json.dumps({
            "root": str(settings.root),
            "database": str(settings.database_path),
            "database_exists": settings.database_path.exists(),
            "configured_sources": len(settings.source_routes),
            "mode": "safe-check-only",
        }, ensure_ascii=False, indent=2))
        return 0
    with db.connect() as con:
        rows = con.execute("SELECT state, COUNT(*) AS count FROM items GROUP BY state ORDER BY state").fetchall()
    print(json.dumps({row["state"]: row["count"] for row in rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
