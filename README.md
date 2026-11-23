# Galaxy Proper Motion Analysis

Tools and scripts for querying and analyzing galaxy proper motion data from the SIMBAD astronomical database using Astroquery.

## Features

- **SIMBAD Integration**: Query the SIMBAD astronomical database via Astroquery
- **Proper Motion Queries**: Retrieve proper motion (PM), parallax, and distance data
- **Batch Processing**: Query multiple galaxies efficiently
- **Data Analysis**: Calculate tangential velocities and 3D kinematic properties
- **Flexible Filtering**: Filter by object type, proper motion magnitude, distance, etc.
- **CSV Export**: Save results for further analysis

## Installation

### 1. Clone or navigate to the repository
```bash
cd /path/to/galaxy-proper-motion
```

### 2. Create/activate virtual environment (optional but recommended)
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install astropy astroquery pandas numpy matplotlib
```

## Quick Start

### Single Galaxy Query
```bash
python query_simbad_galaxies.py --object "M31"
```

### Query a Sky Region
```bash
python query_simbad_galaxies.py --ra-dec 10.6847 41.2691 --radius 10.0
```

### Batch Query Multiple Galaxies
```bash
python simbad_proper_motion_analysis.py --input example_galaxies.txt
```

### With Filtering
```bash
# Filter to galaxies only
python query_simbad_galaxies.py --object "M31" --galaxies-only

# Filter to objects with proper motion measurements
python query_simbad_galaxies.py --object "M31" --proper-motion-only --galaxies-only

# High proper motion objects (> 1 mas/yr)
python simbad_proper_motion_analysis.py --input example_galaxies.txt --min-pm 1.0

# Nearby objects (< 100 pc)
python simbad_proper_motion_analysis.py --input example_galaxies.txt --max-distance 100
```

## Scripts

### `query_simbad_galaxies.py`
Single or region-based SIMBAD queries with filtering options.

**Usage:**
```bash
python query_simbad_galaxies.py [-h] (--object OBJECT | --ra-dec RA DEC) 
                                [--radius RADIUS] [--output OUTPUT]
                                [--galaxies-only] [--proper-motion-only]
                                [-v | -q]
```

**Examples:**
```bash
# Query M31 (Andromeda)
python query_simbad_galaxies.py --object "M31"

# Query region, galaxies only
python query_simbad_galaxies.py --ra-dec 10.6847 41.2691 --radius 20 --galaxies-only

# Save to custom file
python query_simbad_galaxies.py --object "M33" --output m33_data.csv

# Verbose output
python query_simbad_galaxies.py --object "M31" -v
```

### `simbad_proper_motion_analysis.py`
Batch query and advanced analysis of proper motion data.

**Usage:**
```bash
python simbad_proper_motion_analysis.py [-h] --input INPUT [--output OUTPUT]
                                        [--min-pm MIN_PM] [--max-distance MAX_DISTANCE]
                                        [-v | -q]
```

**Examples:**
```bash
# Batch query from file
python simbad_proper_motion_analysis.py --input example_galaxies.txt

# High proper motion filter
python simbad_proper_motion_analysis.py --input example_galaxies.txt --min-pm 0.5

# Nearby objects
python simbad_proper_motion_analysis.py --input example_galaxies.txt --max-distance 500

# Combined filters with verbose output
python simbad_proper_motion_analysis.py --input example_galaxies.txt --min-pm 0.1 --max-distance 1000 -v
```

## Data Fields Retrieved

The scripts retrieve these fields from SIMBAD:

| Field | Description | Unit |
|-------|-------------|------|
| `MAIN_ID` | Primary object identifier | - |
| `RA`, `DEC` | Right Ascension, Declination | degrees |
| `OTYPE` | Object type (G, Sy1, etc.) | - |
| `PMRA`, `PMDEC` | Proper motion components | mas/yr |
| `PM` | Total proper motion | mas/yr |
| `PARALLAX` | Parallax measurement | mas |
| `DIST_X` | Distance estimate | pc |
| `RV_VALUE` | Radial velocity | km/s |
| `Z_VALUE` | Redshift | - |
| `MAG_*` | Magnitudes in various bands | mag |
| `FLUX_*` | Fluxes from Gaia/other surveys | - |

Additional calculated fields:
- `PM_TOTAL_CALC`: Total proper motion from components
- `V_TAN_PARALLAX`: Tangential velocity from parallax and PM (km/s)
- `V_TAN_DISTANCE`: Tangential velocity from distance and PM (km/s)

## Understanding Proper Motion

**Proper Motion (μ)**: Angular motion of an object across the sky per unit time
- Units: milliarcseconds per year (mas/yr) or arcseconds per year (arcsec/yr)
- Example: Barnard's Star ~10.3 arcsec/yr (highest known)

**Conversion Factors**:
- 1 arcsec/yr = 1000 mas/yr
- Tangential velocity: v_tan [km/s] = 4.74 × μ [mas/yr] × d [pc]

**Typical Values**:
- **High proper motion stars**: > 1 arcsec/yr (nearby, large velocity)
- **Most galaxies**: < 0.1 arcsec/yr (too distant for accurate PM)
- **Nearby galaxies** (M31, M33): ~0.05 arcsec/yr

## Output Files

Results are saved as CSV files with columns from SIMBAD plus calculated fields:

```csv
MAIN_ID,RA,DEC,OTYPE,PM,PMRA,PMDEC,PARALLAX,RV_VALUE,Z_VALUE,V_TAN_PARALLAX,...
M31,10.6847,41.2691,G,0.055,0.034,0.044,0.072,...
...
```

## Documentation

See `SIMBAD_ASTROQUERY_GUIDE.md` for:
- Detailed SIMBAD concepts
- Advanced query examples
- Object type codes
- Troubleshooting guide
- Python API usage examples

## Examples Directory

The `example_galaxies.txt` file contains a sample list of nearby galaxies:
```
M31           # Andromeda
M33           # Triangulum
M51           # Whirlpool
M74           # Phantom
...
```

Use it to test batch queries:
```bash
python simbad_proper_motion_analysis.py --input example_galaxies.txt --output results.csv
```

## Troubleshooting

### ImportError: No module named 'astroquery'
Install required packages:
```bash
pip install -r requirements.txt
```

### SIMBAD Query Returns No Results
- Check object name on https://simbad.cfa.harvard.edu/simbad/
- Try alternative names or catalog numbers
- For coordinates, ensure correct format (degrees)

### Connection Timeout
Increase timeout in code or use `--verbose` to debug:
```python
from astropy.utils.data import conf
conf.remote_timeout = 300  # 5 minutes
```

### Low proper motion for distant galaxies
This is expected—parallax-based distances and PM are limited to nearby objects (< ~10 Mpc).

## References

- **SIMBAD**: https://simbad.cfa.harvard.edu/simbad/
- **Astroquery**: https://astroquery.readthedocs.io/
- **Astropy**: https://www.astropy.org/
- **Proper Motion**: https://en.wikipedia.org/wiki/Proper_motion

## License

See LICENSE file for details.

## Author

Created for galaxy proper motion analysis.

---

**Last Updated**: November 23, 2026