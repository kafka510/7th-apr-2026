"""
Upload satellite GHI/TEMP CSV to timeseries_data.

Reads a CSV with columns: time, GHI, TEMP.
Writes to timeseries_data with:
  device_id = {asset_code}_sat
  metric sat_ghi <- GHI, metric sat_amb_temp <- TEMP
  ts = parsed time (stored as UTC).

If data for the same device and time range already exists, it is deleted
before inserting the new data (replace-by-duration behavior).
"""
import csv
import io
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional, Tuple

from django.db import connection
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)

# Device id suffix for satellite data
SATELLITE_DEVICE_SUFFIX = "_sat"

# Metric names in timeseries_data
METRIC_GHI = "sat_ghi"
METRIC_TEMP = "sat_amb_temp"

# CSV column names (case-insensitive match)
COL_TIME = "time"
COL_GHI = "GHI"
COL_TEMP = "TEMP"


def _parse_ts(s: str):
    """Parse timestamp string to timezone-aware datetime (UTC)."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if django_timezone.is_naive(dt):
        dt = django_timezone.make_aware(dt)
    return dt.astimezone(dt_timezone.utc)


def _normalize_header(name: str) -> str:
    return (name or "").strip()


def upload_satellite_ghi_temp_csv(
    file_content: bytes,
    asset_code: str,
    filename: str = "",
) -> Tuple[bool, Optional[str], int, int, Optional[datetime], Optional[datetime]]:
    """
    Parse CSV and write GHI/TEMP to timeseries_data for device_id = {asset_code}_sat.

    CSV must have columns: time, GHI, TEMP (header row optional; column names
    matched case-sensitively for GHI/TEMP, time is case-insensitive).

    For the time range [min_ts, max_ts] present in the CSV, any existing
    timeseries_data for device_id = {asset_code}_sat is deleted, then new
    rows are inserted.

    Returns:
        (success, error_message, deleted_count, rows_written, start_ts, end_ts)
    """
    device_id = f"{asset_code}{SATELLITE_DEVICE_SUFFIX}"
    deleted_count = 0
    rows_written = 0
    start_ts = None
    end_ts = None

    try:
        print(f"[Satellite upload] Started for asset_code={asset_code!r}, device_id={device_id!r}")
        # Decode with common encodings
        text = None
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = file_content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return False, "Could not decode file as UTF-8 or Latin-1", 0, 0, None, None

        reader = csv.DictReader(io.StringIO(text))
        fieldnames = list(reader.fieldnames or [])
        # Normalize for column lookup: expect 'time', 'GHI', 'TEMP'
        col_map = {}
        for f in fieldnames:
            n = _normalize_header(f)
            if n == "time":
                col_map["time"] = f
            elif n == "GHI":
                col_map["ghi"] = f
            elif n == "TEMP":
                col_map["temp"] = f
        if "time" not in col_map or "ghi" not in col_map or "temp" not in col_map:
            return (
                False,
                "CSV must have columns: time, GHI, TEMP",
                0,
                0,
                None,
                None,
            )

        rows = []
        for row in reader:
            ts_str = row.get(col_map["time"]) or ""
            ghi_str = row.get(col_map["ghi"]) or ""
            temp_str = row.get(col_map["temp"]) or ""
            ts = _parse_ts(ts_str)
            if ts is None:
                continue
            try:
                ghi = float(ghi_str)
            except (ValueError, TypeError):
                ghi = None
            try:
                temp = float(temp_str)
            except (ValueError, TypeError):
                temp = None
            if ghi is None and temp is None:
                continue
            rows.append((ts, ghi, temp))
            if start_ts is None or ts < start_ts:
                start_ts = ts
            if end_ts is None or ts > end_ts:
                end_ts = ts

        if not rows:
            return False, "No valid rows with time and at least one of GHI/TEMP", 0, 0, None, None

        # Build insert rows: (device_id, ts, oem_metric, metric, value)
        insert_rows = []
        for ts, ghi, temp in rows:
            if ghi is not None:
                insert_rows.append((device_id, ts, "GHI", METRIC_GHI, str(ghi)))
            if temp is not None:
                insert_rows.append((device_id, ts, "TEMP", METRIC_TEMP, str(temp)))

        if not insert_rows:
            return False, "No valid GHI or TEMP values", 0, 0, None, None

        num_rows = len(insert_rows)
        print(f"[Satellite upload] Parsed {len(rows)} data rows -> {num_rows} records to insert (GHI + TEMP)")

        # Batch size for multi-row INSERT (avoids executemany's one-round-trip-per-row slowness)
        BATCH_SIZE = 500

        with connection.cursor() as cursor:
            # Delete existing data for this device in the time range
            print(f"[Satellite upload] Deleting existing data for {device_id!r} in time range...")
            cursor.execute(
                """
                DELETE FROM timeseries_data
                WHERE device_id = %s AND ts >= %s AND ts <= %s
                """,
                [device_id, start_ts, end_ts],
            )
            deleted_count = cursor.rowcount
            print(f"[Satellite upload] Deleted {deleted_count} existing rows. Inserting {num_rows} rows in batches of {BATCH_SIZE}...")

            # Bulk insert in batches (single INSERT with many VALUES per batch)
            num_batches = (len(insert_rows) + BATCH_SIZE - 1) // BATCH_SIZE
            for i in range(0, len(insert_rows), BATCH_SIZE):
                batch_num = (i // BATCH_SIZE) + 1
                batch = insert_rows[i : i + BATCH_SIZE]
                placeholders = ",".join("(%s, %s, %s, %s, %s)" for _ in batch)
                params = [item for row in batch for item in row]
                cursor.execute(
                    f"""
                    INSERT INTO timeseries_data (device_id, ts, oem_metric, metric, value)
                    VALUES {placeholders}
                    """,
                    params,
                )
                print(f"[Satellite upload] Batch {batch_num}/{num_batches} inserted ({len(batch)} rows)")
            rows_written = len(insert_rows)
            print(f"[Satellite upload] Done. Wrote {rows_written} rows for {device_id!r}")

        logger.info(
            "satellite_ghi_temp_upload: asset_code=%s device_id=%s deleted=%d written=%d start=%s end=%s",
            asset_code,
            device_id,
            deleted_count,
            rows_written,
            start_ts.isoformat() if start_ts else None,
            end_ts.isoformat() if end_ts else None,
        )
        return True, None, deleted_count, rows_written, start_ts, end_ts

    except Exception as e:
        logger.exception("satellite_ghi_temp_upload failed: %s", e)
        return False, str(e), deleted_count, rows_written, start_ts, end_ts
