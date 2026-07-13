"""
Cleans raw Egnyte material-release exports (.csv or .xlsx).

The raw files are laid out as repeating blocks, not a normal table:

    Material: G12 GALVND ST,,,,
    Component Name,Width (in),Height (in),,
    FRM-1003-90_..._0,90,7.81,702.9,
    FRM-1003-90_..._0,90,7.81,702.9,
    ...
    ,,,144.7054507,FT²
    Material: G14 GALVND ST,,,,
    Component Name,Width (in),Height (in),,
    ...

Each block starts with a "Material:" line, has a repeated column-header
line, a run of component rows, and ends with a subtotal line (no
component name, just a total quantity + unit).

This script turns that into two tidy tables:

  1. materials_detail.csv  - one row per component, with Material as its
     own column (Component Name, Width, Height, Quantity all preserved).
  2. material_totals.csv   - one row per material block's subtotal
     (Total Quantity + Unit), since those rows don't belong in the
     per-component table.

Usage:
    python src/clean.py
    (reads every *.csv and *.xlsx in data/raw/, writes combined output
    to data/processed/)
"""

import csv
from pathlib import Path

import openpyxl

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# The raw CSV exports use Windows-1252 (they contain characters like "²"
# that aren't valid UTF-8), so we read with this encoding to avoid
# mangled text. .xlsx files store text as proper unicode already, so no
# encoding guessing is needed for those.
SOURCE_ENCODING = "cp1252"


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def rows_from_csv(path: Path):
    with path.open("r", encoding=SOURCE_ENCODING, newline="") as f:
        for raw_fields in csv.reader(f):
            yield [_stringify(c) for c in raw_fields]


def rows_from_xlsx(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    for ws in wb.worksheets:
        for raw_fields in ws.iter_rows(values_only=True):
            yield [_stringify(c) for c in raw_fields]


def parse_rows(rows, source_name: str):
    """Turn an iterable of raw row fields into (detail_rows, total_rows)."""
    detail_rows = []
    total_rows = []
    current_material = None

    for raw_fields in rows:
        # Pad short rows so we can always index safely.
        fields = list(raw_fields) + [""] * (5 - len(raw_fields))
        first = fields[0]

        if first.startswith("Material:"):
            current_material = first.split("Material:", 1)[1].strip()
            continue

        if first == "Component Name":
            # Repeated header row inside every block - skip it.
            continue

        if first == "" and fields[1] == "" and fields[2] == "":
            # Subtotal row for the block just finished, e.g.
            # ",,,144.7054507,FT²"
            qty, unit = fields[3], fields[4]
            if qty:
                total_rows.append(
                    {
                        "Source File": source_name,
                        "Material": current_material,
                        "Total Quantity": qty,
                        "Unit": unit,
                    }
                )
            continue

        if first == "":
            # Genuinely blank line - ignore.
            continue

        # Otherwise this is a normal component row.
        detail_rows.append(
            {
                "Source File": source_name,
                "Material": current_material,
                "Component Name": fields[0],
                "Width (in)": fields[1],
                "Height (in)": fields[2],
                "Quantity": fields[3],
            }
        )

    return detail_rows, total_rows


def parse_file(path: Path):
    if path.suffix.lower() == ".csv":
        rows = rows_from_csv(path)
    elif path.suffix.lower() == ".xlsx":
        rows = rows_from_xlsx(path)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")
    return parse_rows(rows, path.name)


def write_csv(rows, out_path: Path, fieldnames):
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    raw_files = sorted(
        p for p in RAW_DIR.iterdir() if p.suffix.lower() in (".csv", ".xlsx")
    )
    if not raw_files:
        print(f"No CSV or XLSX files found in {RAW_DIR}")
        return

    all_detail, all_totals = [], []
    for path in raw_files:
        detail_rows, total_rows = parse_file(path)
        all_detail.extend(detail_rows)
        all_totals.extend(total_rows)
        print(f"{path.name}: {len(detail_rows)} component rows, {len(total_rows)} material totals")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    detail_out = PROCESSED_DIR / "materials_detail.csv"
    totals_out = PROCESSED_DIR / "material_totals.csv"

    write_csv(
        all_detail,
        detail_out,
        fieldnames=["Source File", "Material", "Component Name", "Width (in)", "Height (in)", "Quantity"],
    )
    write_csv(
        all_totals,
        totals_out,
        fieldnames=["Source File", "Material", "Total Quantity", "Unit"],
    )

    print(f"\nWrote {len(all_detail)} rows to {detail_out}")
    print(f"Wrote {len(all_totals)} rows to {totals_out}")


if __name__ == "__main__":
    main()
