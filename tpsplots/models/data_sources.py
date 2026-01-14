"""Data source configuration models."""

from typing import Literal

from pydantic import BaseModel, Field


class ControllerMethodDataSource(BaseModel):
    """Controller method data source configuration."""

    type: Literal["controller_method"]
    class_name: str = Field(..., alias="class", description="Controller class name")
    method: str = Field(..., description="Method name to call")


class CSVFileDataSource(BaseModel):
    """CSV file data source configuration."""

    type: Literal["csv_file"]
    path: str = Field(..., description="Path to CSV file")


class URLDataSource(BaseModel):
    """URL/Google Sheets data source configuration."""

    type: Literal["google_sheets", "url"]
    url: str = Field(..., description="URL to fetch CSV data from")
