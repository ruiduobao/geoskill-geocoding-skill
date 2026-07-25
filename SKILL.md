---
description: 'Forward and reverse geocoding using Nominatim (OpenStreetMap) and Open-Meteo

  Geocoding API. Supports address-to-coordinates, coordinates-to-address,

  and batch geocoding from CSV files.

  '
name: geocoding-skill
---

# geocoding-skill

Forward and reverse geocoding tool using Nominatim (OpenStreetMap) and Open-Meteo Geocoding API. Supports single and batch geocoding with rate limiting.

## Features

- **Forward Geocoding**: Address → Latitude/Longitude
- **Reverse Geocoding**: Latitude/Longitude → Address
- **Batch Processing**: Geocode multiple addresses from CSV
- **Multiple Providers**: Nominatim (detailed) + Open-Meteo (fast, cities)
- **Rate Limiting**: Automatic 1 req/sec for Nominatim compliance
- **CSV/JSON Output**: Flexible output formats

## Usage

```bash
# Forward geocode
python scripts\geocoding-skill.py geocode --address "Beijing, China"

# Reverse geocode
python scripts\geocoding-skill.py reverse --lat 39.9042 --lon 116.4074

# Batch geocode from CSV
python scripts\geocoding-skill.py batch --input addresses.csv --address_col "address"

# Use Open-Meteo (faster, good for cities)
python scripts\geocoding-skill.py geocode --address "Tokyo" --provider open-meteo
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--address` | Address to geocode | Required (geocode) |
| `--lat` | Latitude (-90 to 90) | Required (reverse) |
| `--lon` | Longitude (-180 to 180) | Required (reverse) |
| `--input` | Input CSV file path | Required (batch) |
| `--address-col` | Column name with addresses | Required (batch) |
| `--provider` | Provider: nominatim or open-meteo | nominatim |
| `--output` | Output file path | Auto-generated |

## Data Sources

- **Nominatim** (https://nominatim.org/) — OpenStreetMap, ODbL
  - Full address geocoding worldwide
  - Rate limit: 1 request/second
  - No API key required
- **Open-Meteo Geocoding** (https://open-meteo.com/) — CC BY 4.0
  - City/country name lookup
  - No rate limit
  - No API key required

## Installation

```bash
pip install requests>=2.28.0 tqdm numpy scipy
# Or: pip install -r scripts/requirements.txt
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests to geocoding APIs |
| `tqdm` | Progress bars for batch processing |

## Providers Comparison

| Feature | Nominatim | Open-Meteo |
|---------|-----------|------------|
| Street address | ✅ | ❌ |
| City name | ✅ | ✅ |
| Country | ✅ | ✅ |
| Rate limit | 1 req/sec | None |
| Reverse geocoding | ✅ | ❌ (fallback to Nominatim) |

## CSV Format Specification (Batch Input)

```csv
id,address
1,北京市天安门
2,上海市外滩
3,广州市天河区
```

For reverse geocoding batch:

```csv
id,lat,lon
1,39.9042,116.4074
2,31.2304,121.4737
```

## Output Schema

| Column | Description |
|--------|-------------|
| `id` | Input row identifier |
| `address` | Matched address (forward) |
| `lat` | Latitude |
| `lon` | Longitude |
| `display_name` | Full display name |
| `confidence` | Match confidence (0-1) |

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Address not found | Ambiguous or non-existent address | Return empty result with confidence=0 |
| Network error | Connection failure | Auto-retry up to 3 times |
| `HTTP 429` | Rate limit exceeded | Wait and retry with backoff |
| CSV encoding error | Non-UTF-8 input | Convert to UTF-8 first |

## Result Disambiguation

When multiple matches are found, all candidates are returned with confidence scores. The highest confidence match appears first. Filter by `confidence >= 0.5` for reliable results.

## Timeout Configuration

```bash
python scripts\geocoding-skill.py batch --input addresses.csv --timeout 60
```

Default timeout is 30 seconds per request. Increase for slow connections.

## Resume Mechanism for Failed Batch Jobs

```bash
# Resume from last successful row
python scripts\geocoding-skill.py batch --input addresses.csv --resume --state-file .geocoding_state.json
```

The state file tracks completed rows, allowing interruption and resumption without reprocessing.

## Encoding / Language Info

- Input CSV must be **UTF-8** encoded
- For Nominatim, use `--language` parameter to specify preferred language:
  ```bash
  python scripts\geocoding-skill.py geocode --address "北京市" --language zh
  ```
- Supported language codes: `en`, `zh`, `ja`, `ko`, `fr`, `de`, etc.

## Custom Nominatim Endpoint

```bash
# Use a self-hosted Nominatim instance
python scripts\geocoding-skill.py geocode --address "Beijing" --endpoint https://nominatim.example.com/search
```

Default endpoint: `https://nominatim.openstreetmap.org/search`

## Region Biasing

```bash
# Prioritize results in China
python scripts\geocoding-skill.py geocode --address "Springfield" --countrycode us
```

Use `--countrycode` with ISO 3166-1 alpha-2 codes to bias results toward a specific country.

## Accuracy Information

| Match Type | Typical Accuracy |
|------------|-----------------|
| Street address | 5-10 m |
| City name | ~1 km (city center) |
| Country | ~10 km (country centroid) |
| POI | Variable (10-100 m) |

## Citation

```bibtex
@misc{nominatim,
  title={Nominatim - OpenStreetMap reverse geocoding},
  author={{OpenStreetMap contributors}},
  year={2024},
  url={https://nominatim.org/},
  note={ODbL}
}
@misc{openmeteo2024geocoding,
  title={Open-Meteo Geocoding API},
  author={{Open-Meteo}},
  year={2024},
  url={https://open-meteo.com/en/docs/geocoding-api},
  note={CC BY 4.0}
}
```

## Visualization Guidance

```python
import pandas as pd
import folium

df = pd.read_csv("geocoded_results.csv")
m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=4)
for _, row in df.iterrows():
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=row["display_name"],
        tooltip=str(row["id"])
    ).add_to(m)
m.save("geocoded_map.html")
```

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `ConnectionError` | Network issue | Check internet, retry |
| `HTTP 429` | Rate limit | Wait 60s, retry |
| `ValueError` | Invalid input | Check parameter format |
| Empty output | No data | Try different parameters |
| `ModuleNotFoundError` | Missing dep | Run pip install |

---

## Advanced Usage

### Batch Geocoding with Resume
```bash
python scripts\geocoding-skill.py batch   --input addresses.csv --output geocoded.json --resume
```

### CI/CD Integration (GitHub Actions)
```yaml
# .github/workflows/geocode-update.yml
name: Geocode Addresses
on:
  push:
    paths: ['data/addresses.csv']
jobs:
  geocode:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests
      - run: |
          python scripts\geocoding-skill.py batch \
            --input data/addresses.csv \
            --output data/geocoded.json --resume
```

### PostGIS Import
```bash
python scripts\geocoding-skill.py batch --input addresses.csv --output geocoded.json

# Convert to CSV and import
python -c "
import json, csv
data = json.load(open('geocoded.json'))
with open('geocoded.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['input', 'lat', 'lon', 'display_name'])
    w.writeheader()
    for r in data:
        w.writerow({'input': r['input'], 'lat': r['lat'], 'lon': r['lon'], 'display_name': r['display_name']})
"
psql -d gis_db -c "\COPY geocoded_addresses FROM 'geocoded.csv' CSV HEADER"
```

### Performance Tips
- Use `--resume` to continue interrupted batch jobs
- Add `--delay 1` to respect Nominatim rate limit (1 req/sec)
- For >10k addresses, consider self-hosted Nominatim with `--endpoint`

---

## 中文说明

基于 Nominatim（OpenStreetMap）和 Open-Meteo 的正向/反向地理编码工具，支持单条和批量地理编码。

## 安装

```bash
pip install requests>=2.28.0 tqdm numpy scipy
# 或: pip install -r scripts/requirements.txt
```

## 依赖

| 包 | 用途 |
|-----|------|
| `requests` | 地理编码 API 的 HTTP 请求 |
| `tqdm` | 批量处理进度条 |

## CSV 格式规范（批量输入）

```csv
id,address
1,北京市天安门
2,上海市外滩
3,广州市天河区
```

反向地理编码批量输入：

```csv
id,lat,lon
1,39.9042,116.4074
2,31.2304,121.4737
```

## 输出结构

| 列名 | 说明 |
|------|------|
| `id` | 输入行标识 |
| `address` | 匹配地址（正向） |
| `lat` | 纬度 |
| `lon` | 经度 |
| `display_name` | 完整显示名称 |
| `confidence` | 匹配置信度（0-1） |

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 地址未找到 | 模糊或不存在的地址 | 返回空结果，confidence=0 |
| 网络错误 | 连接失败 | 自动重试最多 3 次 |
| `HTTP 429` | 超出速率限制 | 等待后重试 |
| CSV 编码错误 | 非 UTF-8 输入 | 先转换为 UTF-8 |

## 结果消歧义

找到多个匹配时，返回所有候选结果及置信度分数。最高置信度匹配排在首位。筛选 `confidence >= 0.5` 获取可靠结果。

## 超时配置

```bash
python scripts\geocoding-skill.py batch --input addresses.csv --timeout 60
```

默认超时 30 秒/请求。网络较慢时增加超时时间。

## 失败批量任务恢复机制

```bash
# 从上次成功行恢复
python scripts\geocoding-skill.py batch --input addresses.csv --resume --state-file .geocoding_state.json
```

状态文件跟踪已完成行，支持中断后恢复，无需重新处理。

## 编码/语言信息

- 输入 CSV 必须为 **UTF-8** 编码
- Nominatim 使用 `--language` 参数指定首选语言：
  ```bash
  python scripts\geocoding-skill.py geocode --address "北京市" --language zh
  ```
- 支持的语言代码：`en`、`zh`、`ja`、`ko`、`fr`、`de` 等

## 自定义 Nominatim 端点

```bash
# 使用自托管 Nominatim 实例
python scripts\geocoding-skill.py geocode --address "Beijing" --endpoint https://nominatim.example.com/search
```

默认端点：`https://nominatim.openstreetmap.org/search`

## 区域偏好

```bash
# 优先返回中国结果
python scripts\geocoding-skill.py geocode --address "Springfield" --countrycode us
```

使用 ISO 3166-1 alpha-2 代码指定 `--countrycode` 以偏向特定国家。

## 精度信息

| 匹配类型 | 典型精度 |
|----------|----------|
| 街道地址 | 5-10 米 |
| 城市名 | ~1 公里（城市中心） |
| 国家 | ~10 公里（国家质心） |
| POI | 变化较大（10-100 米） |

## 引用格式

```bibtex
@misc{nominatim,
  title={Nominatim - OpenStreetMap reverse geocoding},
  author={{OpenStreetMap contributors}},
  year={2024},
  url={https://nominatim.org/},
  note={ODbL}
}
@misc{openmeteo2024geocoding,
  title={Open-Meteo Geocoding API},
  author={{Open-Meteo}},
  year={2024},
  url={https://open-meteo.com/en/docs/geocoding-api},
  note={CC BY 4.0}
}
```

## 可视化指南

```python
import pandas as pd
import folium

df = pd.read_csv("geocoded_results.csv")
m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=4)
for _, row in df.iterrows():
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=row["display_name"],
        tooltip=str(row["id"])
    ).add_to(m)
m.save("geocoded_map.html")
```

## 故障排除

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `ConnectionError` | 网络问题 | 检查网络，重试 |
| `HTTP 429` | 速率限制 | 等待 60 秒后重试 |
| `ValueError` | 无效输入 | 检查参数格式 |
| 空输出 | 无数据 | 尝试不同参数 |
| `ModuleNotFoundError` | 缺少依赖 | 运行 pip install |

基于 Nominatim（OpenStreetMap）和 Open-Meteo 的正向/反向地理编码工具，支持单条和批量地理编码。

## 功能特性

- **正向地理编码**：地址 → 经纬度
- **反向地理编码**：经纬度 → 地址
- **批量处理**：从 CSV 文件批量地理编码
- **多提供者**：Nominatim（详细）+ Open-Meteo（快速，城市级）
- **速率限制**：自动 1 请求/秒，符合 Nominatim 使用条款
- **CSV/JSON 输出**：灵活输出格式

## 使用方法

```bash
# 正向地理编码
python scripts\geocoding-skill.py geocode --address "北京市天安门"

# 反向地理编码
python scripts\geocoding-skill.py reverse --lat 39.9042 --lon 116.4074

# 批量地理编码
python scripts\geocoding-skill.py batch --input addresses.csv --address_col "address"

# 使用 Open-Meteo（更快，适合城市名）
python scripts\geocoding-skill.py geocode --address "Tokyo" --provider open-meteo
```

## 数据来源

- **Nominatim** (https://nominatim.org/) — OpenStreetMap，ODbL
  - 全球完整地址地理编码
  - 速率限制：1 请求/秒
  - 无需 API key
- **Open-Meteo 地理编码** (https://open-meteo.com/) — CC BY 4.0
  - 城市/国家名称查询
  - 无速率限制
  - 无需 API key

## 提供者对比

| 功能 | Nominatim | Open-Meteo |
|------|-----------|------------|
| 街道地址 | ✅ | ❌ |
| 城市名 | ✅ | ✅ |
| 国家 | ✅ | ✅ |
| 速率限制 | 1 请求/秒 | 无限制 |
| 反向地理编码 | ✅ | ❌（回退到 Nominatim） |
