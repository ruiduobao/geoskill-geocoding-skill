#!/usr/bin/env python3
"""
geocoding-skill: Forward & Reverse Geocoding Tool
====================================================
Geocode addresses to coordinates (forward) and coordinates to addresses (reverse)
using Nominatim (OpenStreetMap) and Open-Meteo Geocoding API.

Privacy Disclosure:
- Nominatim: address queries are sent to nominatim.openstreetmap.org via HTTPS.
  OSM logs queries per their privacy policy. Max 1 request/second.
- Open-Meteo Geocoding: city/country queries sent to geocoding-api.open-meteo.com.
  No API key required.
- Batch mode: addresses from your CSV are sent one-by-one to the selected provider.
  Consider the sensitivity of your data before batch geocoding.

Data Source:
- Nominatim / OpenStreetMap (https://nominatim.org/) — ODbL
- Open-Meteo (https://open-meteo.com/) — CC BY 4.0

License: MIT-0 (No attribution required)
Author: ruiduobao
Version: 0.1.0
"""

import argparse
import sys
import os
import json
import csv
import time
from typing import Optional, List, Dict

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required. Install with: pip install requests>=2.28.0")
    sys.exit(1)


# ============================================================
# Constants
# ============================================================

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

NOMINATIM_RATE_LIMIT = 1.0  # seconds between requests
DEFAULT_USER_AGENT = "geocoding-skill/0.1.0 (OpenClaw GIS tool)"


# ============================================================
# Nominatim Provider
# ============================================================

def nominatim_geocode(address: str, user_agent: str = DEFAULT_USER_AGENT) -> Optional[Dict]:
    """Forward geocode using Nominatim.

    Args:
        address: Address string to geocode
        user_agent: User agent string (required by Nominatim ToS)

    Returns:
        Dict with lat, lon, display_name, etc. or None if not found.
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": user_agent}

    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/search",
            params=params,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  WARNING: Nominatim request failed: {e}")
        return None

    results = resp.json()
    if not results:
        return None

    r = results[0]
    return {
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "display_name": r.get("display_name", ""),
        "type": r.get("type", ""),
        "importance": r.get("importance", 0),
        "osm_id": r.get("osm_id", ""),
        "provider": "nominatim",
    }


def nominatim_reverse(lat: float, lon: float, user_agent: str = DEFAULT_USER_AGENT) -> Optional[Dict]:
    """Reverse geocode using Nominatim.

    Args:
        lat: Latitude
        lon: Longitude
        user_agent: User agent string

    Returns:
        Dict with address components or None.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": user_agent}

    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params=params,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  WARNING: Nominatim reverse request failed: {e}")
        return None

    r = resp.json()
    if "error" in r:
        print(f"  WARNING: {r['error']}")
        return None

    return {
        "lat": float(r.get("lat", lat)),
        "lon": float(r.get("lon", lon)),
        "display_name": r.get("display_name", ""),
        "type": r.get("type", ""),
        "address": r.get("address", {}),
        "osm_id": r.get("osm_id", ""),
        "provider": "nominatim",
    }


# ============================================================
# Open-Meteo Provider
# ============================================================

def openmeteo_geocode(name: str, language: str = "en") -> Optional[Dict]:
    """Forward geocode using Open-Meteo Geocoding API.

    Best for city/country names, less precise for street addresses.

    Args:
        name: City/country name
        language: Language code for results

    Returns:
        Dict with lat, lon, name, etc. or None.
    """
    params = {
        "name": name,
        "count": 1,
        "language": language,
        "format": "json",
    }

    try:
        resp = requests.get(OPEN_METEO_GEOCODE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  WARNING: Open-Meteo geocoding failed: {e}")
        return None

    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None

    r = results[0]
    return {
        "lat": float(r["latitude"]),
        "lon": float(r["longitude"]),
        "display_name": f"{r.get('name', '')}, {r.get('country', '')}",
        "name": r.get("name", ""),
        "country": r.get("country", ""),
        "admin1": r.get("admin1", ""),
        "timezone": r.get("timezone", ""),
        "provider": "open-meteo",
    }


def openmeteo_reverse(lat: float, lon: float) -> Optional[Dict]:
    """Reverse geocode using Open-Meteo (not natively supported).

    Uses Nominatim as fallback since Open-Meteo doesn't have reverse.
    """
    print("  NOTE: Open-Meteo doesn't support reverse geocoding. Falling back to Nominatim.")
    return nominatim_reverse(lat, lon)


# ============================================================
# Unified Interface
# ============================================================

def geocode_address(address: str, provider: str = "nominatim") -> Optional[Dict]:
    """Geocode an address with selected provider."""
    if provider == "nominatim":
        return nominatim_geocode(address)
    elif provider == "open-meteo":
        return openmeteo_geocode(address)
    else:
        print(f"ERROR: Unknown provider '{provider}'.")
        return None


def reverse_geocode(lat: float, lon: float, provider: str = "nominatim") -> Optional[Dict]:
    """Reverse geocode with selected provider."""
    if provider == "nominatim":
        return nominatim_reverse(lat, lon)
    elif provider == "open-meteo":
        return openmeteo_reverse(lat, lon)
    else:
        print(f"ERROR: Unknown provider '{provider}'.")
        return None


# ============================================================
# Batch Processing
# ============================================================

def batch_geocode(input_path: str, address_col: str, provider: str = "nominatim",
                  rate_limit: float = NOMINATIM_RATE_LIMIT) -> List[Dict]:
    """Batch geocode addresses from CSV.

    Args:
        input_path: Path to input CSV
        address_col: Column name containing addresses
        provider: Provider to use
        rate_limit: Seconds between requests

    Returns:
        List of result dicts (original row + geocoding results)
    """
    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    rows = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if address_col not in reader.fieldnames:
            print(f"ERROR: Column '{address_col}' not found in CSV.")
            print(f"  Available columns: {', '.join(reader.fieldnames)}")
            sys.exit(1)
        rows = list(reader)

    print(f"Batch geocoding {len(rows)} addresses using {provider}...")
    print(f"  Rate limit: {rate_limit} sec/request (estimated: {len(rows) * rate_limit / 60:.1f} min)")

    results = []
    for i, row in enumerate(rows):
        address = row.get(address_col, "").strip()
        if not address:
            result = {**row, "lat": "", "lon": "", "display_name": "", "geocode_status": "empty"}
            results.append(result)
            continue

        print(f"  [{i+1}/{len(rows)}] {address[:60]}...")

        geo = geocode_address(address, provider)
        if geo:
            result = {
                **row,
                "lat": geo["lat"],
                "lon": geo["lon"],
                "display_name": geo["display_name"],
                "geocode_status": "ok",
            }
        else:
            result = {**row, "lat": "", "lon": "", "display_name": "", "geocode_status": "not_found"}

        results.append(result)

        # Rate limiting
        if provider == "nominatim" and i < len(rows) - 1:
            time.sleep(rate_limit)

    # Summary
    ok_count = sum(1 for r in results if r["geocode_status"] == "ok")
    fail_count = sum(1 for r in results if r["geocode_status"] == "not_found")
    print(f"\nResults: {ok_count} found, {fail_count} not found, {len(results)} total.")

    return results


# ============================================================
# Output
# ============================================================

def write_output(records: List[Dict], output_path: str, as_json: bool = False):
    """Write results to CSV or JSON."""
    if not records:
        print("WARNING: No records to write.")
        return

    if as_json or output_path.endswith(".json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    else:
        # Collect all fieldnames
        fieldnames = []
        for r in records:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)

    print(f"Output saved to: {output_path} ({len(records)} records)")


# ============================================================
# CLI Subcommands
# ============================================================

def cmd_geocode(args):
    """Forward geocode an address."""
    provider = args.provider
    print(f"Geocoding: '{args.address}' (provider: {provider})")

    result = geocode_address(args.address, provider)

    if result:
        print(f"\nResult:")
        print(f"  Latitude:  {result['lat']}")
        print(f"  Longitude: {result['lon']}")
        print(f"  Name:      {result['display_name']}")
        if result.get("type"):
            print(f"  Type:      {result['type']}")
        if result.get("country"):
            print(f"  Country:   {result['country']}")

        output_path = args.output or "geocode_result.json"
        write_output([result], output_path, as_json=True)
    else:
        print("  No results found.")
        sys.exit(1)


def cmd_reverse(args):
    """Reverse geocode coordinates."""
    # Validate coordinates
    if not (-90 <= args.lat <= 90):
        print(f"ERROR: Latitude {args.lat} out of range [-90, 90].")
        sys.exit(1)
    if not (-180 <= args.lon <= 180):
        print(f"ERROR: Longitude {args.lon} out of range [-180, 180].")
        sys.exit(1)

    provider = args.provider
    print(f"Reverse geocoding: ({args.lat}, {args.lon}) (provider: {provider})")

    result = reverse_geocode(args.lat, args.lon, provider)

    if result:
        print(f"\nResult:")
        print(f"  Latitude:  {result['lat']}")
        print(f"  Longitude: {result['lon']}")
        print(f"  Name:      {result['display_name']}")
        if result.get("address"):
            addr = result["address"]
            for k in ["country", "state", "county", "city", "town", "village", "road"]:
                if k in addr:
                    print(f"  {k.capitalize()}: {addr[k]}")

        output_path = args.output or "reverse_geocode_result.json"
        write_output([result], output_path, as_json=True)
    else:
        print("  No results found.")
        sys.exit(1)


def cmd_batch(args):
    """Batch geocode from CSV."""
    results = batch_geocode(args.input, args.address_col, args.provider)

    output_path = args.output or "batch_geocode_results.csv"
    write_output(results, output_path, as_json=output_path.endswith(".json"))


# ============================================================
# Main CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="geocoding-skill",
        description="Forward & Reverse Geocoding — Address ↔ Coordinates via Nominatim / Open-Meteo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Forward geocode
  python geocoding-skill.py geocode --address "Beijing, China"

  # Reverse geocode
  python geocoding-skill.py reverse --lat 39.9042 --lon 116.4074

  # Batch geocode from CSV
  python geocoding-skill.py batch --input addresses.csv --address_col "address"

  # Use Open-Meteo (faster, good for cities)
  python geocoding-skill.py geocode --address "Tokyo" --provider open-meteo

Providers:
  nominatim  — Full address geocoding (rate limited: 1 req/sec)
  open-meteo — City/country geocoding (no rate limit)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # --- geocode ---
    geocode_parser = subparsers.add_parser("geocode", help="Forward geocode an address")
    geocode_parser.add_argument("--address", required=True, help="Address to geocode")
    geocode_parser.add_argument("--provider", default="nominatim",
                                choices=["nominatim", "open-meteo"], help="Geocoding provider")
    geocode_parser.add_argument("--output", help="Output file path")
    geocode_parser.set_defaults(func=cmd_geocode)

    # --- reverse ---
    reverse_parser = subparsers.add_parser("reverse", help="Reverse geocode coordinates")
    reverse_parser.add_argument("--lat", type=float, required=True, help="Latitude")
    reverse_parser.add_argument("--lon", type=float, required=True, help="Longitude")
    reverse_parser.add_argument("--provider", default="nominatim",
                                choices=["nominatim", "open-meteo"], help="Geocoding provider")
    reverse_parser.add_argument("--output", help="Output file path")
    reverse_parser.set_defaults(func=cmd_reverse)

    # --- batch ---
    batch_parser = subparsers.add_parser("batch", help="Batch geocode from CSV")
    batch_parser.add_argument("--input", required=True, help="Input CSV file path")
    batch_parser.add_argument("--address-col", required=True, help="Column name with addresses")
    batch_parser.add_argument("--provider", default="nominatim",
                              choices=["nominatim", "open-meteo"], help="Geocoding provider")
    batch_parser.add_argument("--output", help="Output file path")
    batch_parser.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
