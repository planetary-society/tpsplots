"""Data source configuration models (v2.0 spec)."""

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Data source configuration using a single source string."""

    source: str = Field(..., description="Data source string")


# Alias for backward compatibility with internal imports
DataSource = DataSourceConfig
