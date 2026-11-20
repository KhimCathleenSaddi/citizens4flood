from __future__ import annotations

from datetime import date
from io import BytesIO
import re
from urllib.parse import quote

import ee
import pandas as pd


PRECIPITATION_DATASETS = {
    "Monthly": {
        "dataset": "ECMWF/ERA5_LAND/MONTHLY_AGGR",
        "band": "total_precipitation_sum",
        "default_days": 365,
    },
    "Daily": {
        "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "band": "total_precipitation_sum",
        "default_days": 30,
    },
    "Hourly": {
        "dataset": "ECMWF/ERA5_LAND/HOURLY",
        "band": "total_precipitation_hourly",
        "default_days": 1,
    },
}
REQUIRED_COLUMNS = {"AOI", "Center_LONG", "Center_LAT"}


def load_aoi_data(
    uploaded_file: BytesIO | None,
    sheet_id: str,
    sheet_name: str,
) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)

    match = re.search(r"/spreadsheets/d/([^/]+)", sheet_id)
    spreadsheet_id = match.group(1) if match else sheet_id.strip()
    if not spreadsheet_id:
        raise ValueError("Upload an AOI CSV or enter a Google Sheet ID or URL.")

    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
    )
    return pd.read_csv(url)


def prepare_aoi_data(data: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    missing_columns = REQUIRED_COLUMNS - set(data.columns)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"The AOI data is missing required columns: {columns}.")

    cleaned = data.copy()
    cleaned["Center_LONG"] = pd.to_numeric(cleaned["Center_LONG"], errors="coerce")
    cleaned["Center_LAT"] = pd.to_numeric(cleaned["Center_LAT"], errors="coerce")
    valid = (
        cleaned["AOI"].notna()
        & cleaned["Center_LONG"].between(-180, 180)
        & cleaned["Center_LAT"].between(-90, 90)
    )
    skipped_count = int((~valid).sum())
    cleaned = cleaned.loc[valid].copy()
    cleaned["AOI"] = cleaned["AOI"].astype(str)
    if cleaned.empty:
        raise ValueError("No rows have a usable AOI name and valid longitude/latitude.")
    return cleaned, skipped_count


def fetch_precipitation(
    aoi_row: pd.Series,
    timescale: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    dataset = PRECIPITATION_DATASETS[timescale]
    geometry = ee.Geometry.Point(
        [float(aoi_row["Center_LONG"]), float(aoi_row["Center_LAT"])]
    )
    collection = (
        ee.ImageCollection(dataset["dataset"])
        .filterDate(start_date.isoformat(), end_date.isoformat())
        .filterBounds(geometry)
        .select(dataset["band"])
    )

    def extract_feature(image: ee.image.Image) -> ee.feature.Feature:
        precipitation = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e10,
        ).get(dataset["band"])
        return ee.Feature(
            None,
            {
                "precipitation": precipitation,
                "timestamp": image.get("system:time_start"),
            },
        )

    result = collection.map(extract_feature).getInfo()
    if result is None or "features" not in result:
        raise ValueError("Earth Engine returned an unexpected response.")

    rows = []
    for feature in result["features"]:
        properties = feature.get("properties", {})
        if properties.get("precipitation") is None or properties.get("timestamp") is None:
            continue
        rows.append(
            {
                "timestamp": pd.to_datetime(properties["timestamp"], unit="ms", utc=True),
                "precipitation": properties["precipitation"],
                "AOI": aoi_row["AOI"],
                "Event_Number": aoi_row.get("Event_Number", None),
                "Center_LAT": aoi_row["Center_LAT"],
                "Center_LONG": aoi_row["Center_LONG"],
            }
        )
    return pd.DataFrame(rows)
