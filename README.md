# geocoding-skill

**Forward & Reverse Geocoding** — Address ↔ Coordinates via Nominatim / Open-Meteo.

## Install

### ClawHub
```bash
clawhub install geocoding-skill
```

### Manual
```bash
git clone https://github.com/ruiduobao/geocoding-skill.git
cd geocoding-skill
pip install -r requirements.txt  # requests
```

### Claude Code / skills.sh
```bash
/clawhub install geocoding-skill
```

## Quick Start
```bash
python scripts/geocoding-skill.py geocode --address "Beijing, China"
python scripts/geocoding-skill.py reverse --lat 39.9042 --lon 116.4074
python scripts/geocoding-skill.py batch --input addresses.csv --address_col "address"
```

## Data Sources
- Nominatim / OpenStreetMap (https://nominatim.org/) — ODbL
- Open-Meteo Geocoding (https://open-meteo.com/) — CC BY 4.0

## License
MIT-0

---

# 地理编码工具

**正向/反向地理编码** — 通过 Nominatim / Open-Meteo 实现地址 ↔ 坐标转换。

## 安装

### 手动安装
```bash
git clone https://github.com/ruiduobao/geocoding-skill.git
cd geocoding-skill
pip install requests
```

## 快速开始
```bash
python scripts/geocoding-skill.py geocode --address "北京市天安门"
python scripts/geocoding-skill.py reverse --lat 39.9042 --lon 116.4074
python scripts/geocoding-skill.py batch --input addresses.csv --address_col "address"
```

## 数据来源
- Nominatim / OpenStreetMap (https://nominatim.org/) — ODbL
- Open-Meteo 地理编码 (https://open-meteo.com/) — CC BY 4.0

## 许可证
MIT-0
