"""Admin — data source mode configuration stored in Redis.

Each domain can be set independently to:
  synthetic — always use seeded fixture data, never call external API
  api       — always call real external API (error if unavailable)
  auto      — try real API, silently fall back to synthetic on failure
"""
from __future__ import annotations

from enum import Enum

import redis.asyncio as aioredis
from pydantic import BaseModel

CONFIG_KEY = "config:data_source"


class DataSourceMode(str, Enum):
    SYNTHETIC = "synthetic"
    API = "api"
    AUTO = "auto"


class DataSourceConfig(BaseModel):
    street_works: DataSourceMode = DataSourceMode.AUTO
    road_classification: DataSourceMode = DataSourceMode.AUTO
    usrn_resolution: DataSourceMode = DataSourceMode.AUTO
    underground_assets: DataSourceMode = DataSourceMode.SYNTHETIC  # NUAR live access not yet granted
    ai_copilot: DataSourceMode = DataSourceMode.AUTO


async def get_config(r: aioredis.Redis) -> DataSourceConfig:
    raw = await r.get(CONFIG_KEY)
    if raw:
        try:
            return DataSourceConfig.model_validate_json(raw)
        except Exception:
            pass
    return DataSourceConfig()


async def save_config(r: aioredis.Redis, config: DataSourceConfig) -> None:
    await r.set(CONFIG_KEY, config.model_dump_json())
