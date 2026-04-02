from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    host: str = "127.0.0.1"
    port: int = 8000
    seed_demo_records: bool = True

    @classmethod
    def from_env(cls) -> "AppConfig":
        database_path = Path(os.getenv("FINANCE_DB_PATH", "data/finance.db"))
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8000"))
        seed_demo_records = os.getenv("SEED_DEMO_RECORDS", "true").lower() == "true"
        return cls(
            database_path=database_path,
            host=host,
            port=port,
            seed_demo_records=seed_demo_records,
        )

