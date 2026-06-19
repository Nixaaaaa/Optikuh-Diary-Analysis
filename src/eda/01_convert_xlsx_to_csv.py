"""
Fast XLSX -> CSV converter for the OptiKuh workbook.

Why this file exists:
    pandas.read_excel and openpyxl can be slow on the large optikuh.xlsx file.
    This script streams the XLSX XML directly and writes a normal CSV cache.

Usage from the project root:
    python src/01_convert_xlsx_to_csv.py --input data/raw/optikuh.xlsx --output data/interim/optikuh.csv

The repository already contains data/interim/optikuh.csv, so you only need to run
this script if you want to rebuild the cache from the raw Excel file.
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import List

CELL_RE = re.compile(br"<c ([^>]*)>(.*?)</c>")
ATTR_R_RE = re.compile(br'r="([A-Z]+)[0-9]+"')
ATTR_T_RE = re.compile(br't="([^"]+)"')
V_RE = re.compile(br"<v>(.*?)</v>")
SI_RE = re.compile(br"<si>(.*?)</si>", re.S)
TAG_RE = re.compile(br"<[^>]+>")


def _load_shared_strings(xlsx_zip: zipfile.ZipFile) -> List[str]:
    """Return shared string table from an XLSX archive."""
    try:
        data = xlsx_zip.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    strings: List[str] = []
    for si in SI_RE.findall(data):
        text = TAG_RE.sub(b"", si).decode("utf-8", errors="replace")
        strings.append(html.unescape(text))
    return strings


def _col_to_idx(col_bytes: bytes) -> int:
    """Convert Excel column letters (A, B, AA) to a zero-based index."""
    idx = 0
    for byte in col_bytes:
        idx = idx * 26 + (byte & 0xDF) - 64
    return idx - 1


def _parse_row(row_bytes: bytes, shared_strings: List[str], ncols: int) -> List[str]:
    values = [""] * ncols
    for cell_match in CELL_RE.finditer(row_bytes):
        attrs = cell_match.group(1)
        body = cell_match.group(2)

        ref_match = ATTR_R_RE.search(attrs)
        if not ref_match:
            continue
        col_idx = _col_to_idx(ref_match.group(1))
        if col_idx >= ncols:
            continue

        value_match = V_RE.search(body)
        if not value_match:
            continue
        raw_value = value_match.group(1)

        type_match = ATTR_T_RE.search(attrs)
        if type_match and type_match.group(1) == b"s":
            value = shared_strings[int(raw_value)]
        else:
            value = raw_value.decode("utf-8", errors="replace")
        values[col_idx] = value
    return values


def convert_xlsx_to_csv(input_xlsx: Path, output_csv: Path, ncols: int = 49) -> None:
    if not input_xlsx.exists():
        raise FileNotFoundError(f"Raw workbook not found: {input_xlsx}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    with zipfile.ZipFile(input_xlsx) as xlsx_zip:
        shared_strings = _load_shared_strings(xlsx_zip)
        print(f"Loaded {len(shared_strings):,} shared strings")

        with xlsx_zip.open("xl/worksheets/sheet1.xml") as sheet_xml, output_csv.open(
            "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.writer(csv_file)
            buffer = b""
            nrows = 0

            while True:
                chunk = sheet_xml.read(4 * 1024 * 1024)
                if not chunk and not buffer:
                    break

                buffer += chunk
                parts = buffer.split(b"</row>")
                if chunk:
                    complete_parts = parts[:-1]
                    buffer = parts[-1]
                else:
                    complete_parts = parts
                    buffer = b""

                for part in complete_parts:
                    row_start = part.rfind(b"<row")
                    if row_start == -1:
                        continue
                    row = part[row_start:] + b"</row>"
                    writer.writerow(_parse_row(row, shared_strings, ncols=ncols))
                    nrows += 1
                    if nrows % 100_000 == 0:
                        elapsed = time.time() - start
                        print(f"{nrows:,} rows written in {elapsed:.1f}s")

    elapsed = time.time() - start
    print(f"Done: {nrows:,} rows written to {output_csv} in {elapsed:.1f}s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert optikuh.xlsx to a fast CSV cache.")
    parser.add_argument("--input", default="data/raw/optikuh.xlsx", type=Path)
    parser.add_argument("--output", default="data/interim/optikuh.csv", type=Path)
    parser.add_argument("--ncols", default=49, type=int)
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Do nothing if the output CSV already exists and is non-empty.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_if_exists and args.output.exists() and args.output.stat().st_size > 0:
        print(f"CSV already exists: {args.output}")
        return 0
    convert_xlsx_to_csv(args.input, args.output, args.ncols)
    return 0


if __name__ == "__main__":
    sys.exit(main())
