"""Infrastructure layer: application settings read from the environment."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./hotel.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(database_url=os.environ.get("HOTEL_DATABASE_URL", cls.database_url))
