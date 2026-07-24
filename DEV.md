# geocoding-skill - Development Doc

## Purpose
Forward and reverse geocoding using Nominatim (OpenStreetMap) and Open-Meteo Geocoding API.

## Data Sources
1. Nominatim: `https://nominatim.openstreetmap.org/search` (free, no key, 1 req/sec)
2. Open-Meteo Geocoding: `https://geocoding-api.open-meteo.com/v1/search` (free, no key)

## CLI Design
```
geocoding-skill geocode --address --provider --output
geocoding-skill reverse --lat --lon --provider --output
geocoding-skill batch --input --address-col --provider --output
```

## Dependencies
- requests>=2.28.0

## Implementation Notes
- Nominatim rate limit: 1 req/sec. Implement time.sleep(1) between requests
- Open-Meteo: no rate limit but less detailed results
- Batch mode: read CSV, geocode each row, write results
- Fallback: if primary provider fails, try secondary
- Output: CSV or JSON with lat, lon, display_name, etc.
