"""
Fetch SPHEREx FITS images of Barnard's Star from the IRSA archive.

Barnard's Star (J2000): RA 17h 57m 48.498s, Dec +04° 41' 36.11"
                        RA = 269.45208 deg, Dec = +4.69336 deg

Data is queried from SPHEREx DR1 and QR3 Wide Survey collections via
IRSA's SIA2 service and saved as local FITS files.

Requirements:
    pip install astropy astroquery

Usage:
    python fetch_spherex_barnard.py [-v | -q] [--log-file PATH]
"""

import argparse
import http.client
import logging
import sys
import time
import urllib.error
from pathlib import Path

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import vstack
from astropy.utils.data import conf
from astroquery.ipac.irsa import Irsa

log = logging.getLogger("spherex_fetch")

# SPHEREx FITS files can be large; increase the network timeout.
conf.remote_timeout = 120

# ---------------------------------------------------------------------------
# Target: Barnard's Star
# High proper motion star: ~10 arcsec/yr, so we use a generous search radius.
# ---------------------------------------------------------------------------
BARNARD_RA_DEG  = 269.45208   # 17h 57m 48.498s
BARNARD_DEC_DEG =   4.69336   # +04° 41' 36.11"

SEARCH_RADIUS   = 0.1 * u.deg   # 6 arcmin – wide enough to catch all detectors
                                  # that image the field around Barnard's Star

# SIA2 collections to query (DR1 + QR3 Wide Survey)
COLLECTIONS = ["spherex_dr1", "spherex_qr3"]

OUTPUT_DIR  = Path("spherex_barnard")
MAX_FILES   = 12    # cap on how many FITS files to download (one per detector image)
MAX_RETRIES = 3


def setup_logging(level: int, log_file: Path | None) -> None:
    """Log to stderr at *level*; optionally also log everything (DEBUG) to *log_file*."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"))
        root.addHandler(fh)

    # Keep chatty third-party libraries out of the console unless debugging.
    for name in ("urllib3", "astroquery", "pyvo"):
        logging.getLogger(name).setLevel(max(level, logging.WARNING))


def fmt_size(n_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def query_irsa(coord: SkyCoord, radius: u.Quantity, collections: list[str]):
    """Return a combined SIA2 result table for all requested collections."""
    tables = []
    for coll in collections:
        log.info("Querying IRSA SIA2 collection '%s' (radius %s)", coll, radius)
        t0 = time.monotonic()
        try:
            t = Irsa.query_sia(pos=(coord, radius), collection=[coll])
        except Exception:
            log.warning("Query failed for '%s' after %.1fs",
                        coll, time.monotonic() - t0, exc_info=True)
            continue
        log.info("  '%s': %d image(s) found in %.1fs", coll, len(t), time.monotonic() - t0)
        if len(t) == 0:
            continue
        tables.append(t)

    if not tables:
        raise RuntimeError("No results returned from any SIA2 collection.")

    combined = vstack(tables)
    log.info("Total images found across all collections: %d", len(combined))
    return combined


def download_fits(url: str, out_path: Path, retries: int = MAX_RETRIES) -> bool:
    """
    Download a FITS file from *url* and save it to *out_path*.

    Returns True on success, False on permanent failure.
    """
    for attempt in range(1, retries + 1):
        t0 = time.monotonic()
        log.debug("Download attempt %d/%d: %s", attempt, retries, url)
        try:
            with fits.open(url, memmap=False) as hdulist:
                # Force all extensions into memory before the connection closes.
                for hdu in hdulist:
                    _ = hdu.data
                hdulist.writeto(out_path, overwrite=True)
        except (TimeoutError, urllib.error.HTTPError, http.client.IncompleteRead) as exc:
            elapsed = time.monotonic() - t0
            if attempt == retries:
                log.error("Giving up after %d attempts (last error after %.1fs): %s: %s",
                          retries, elapsed, type(exc).__name__, exc)
                break
            wait = 10 * attempt
            log.warning("Transient error on attempt %d/%d after %.1fs: %s: %s. "
                        "Retrying in %ds", attempt, retries, elapsed,
                        type(exc).__name__, exc, wait)
            time.sleep(wait)
        except Exception:
            log.exception("Non-retryable error downloading %s", url)
            break
        else:
            elapsed = time.monotonic() - t0
            size = out_path.stat().st_size
            rate = size / elapsed if elapsed > 0 else 0
            log.info("  Saved %s (%s in %.1fs, %s/s)",
                     out_path, fmt_size(size), elapsed, fmt_size(rate))
            return True

    # Don't leave a partial file behind, or it will be treated as cached next run.
    if out_path.exists():
        log.debug("Removing partial file %s", out_path)
        out_path.unlink()
    return False


def summarise_file(path: Path) -> None:
    """Log a brief summary of a downloaded FITS file."""
    try:
        with fits.open(path) as hdul:
            hdr = hdul[1].header
            shape = hdul[1].data.shape if hdul[1].data is not None else "N/A"
            log.info("  OBSID=%s detector=%s date=%s shape=%s units=%s extensions=%d",
                     hdr.get("OBSID", "?"), hdr.get("DETECTOR", "?"),
                     hdr.get("DATE", "?"), shape, hdr.get("BUNIT", "?"), len(hdul))
    except Exception:
        log.warning("  Could not summarise %s (file may be corrupt)", path, exc_info=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    g.add_argument("-q", "--quiet", action="store_true", help="only show warnings and errors")
    p.add_argument("--log-file", type=Path, default=OUTPUT_DIR / "fetch.log",
                   help="also write a full DEBUG log here (default: %(default)s)")
    p.add_argument("--no-log-file", action="store_true", help="disable the log file")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    level = logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO
    setup_logging(level, None if args.no_log_file else args.log_file)

    OUTPUT_DIR.mkdir(exist_ok=True)
    run_start = time.monotonic()

    coord = SkyCoord(ra=BARNARD_RA_DEG, dec=BARNARD_DEC_DEG, unit="deg")
    log.info("SPHEREx FITS fetcher – Barnard's Star: RA=%.5f deg, Dec=%.5f deg, radius=%s",
             BARNARD_RA_DEG, BARNARD_DEC_DEG, SEARCH_RADIUS)
    log.debug("Collections=%s, max files=%d, retries=%d, timeout=%ss, output=%s",
              COLLECTIONS, MAX_FILES, MAX_RETRIES, conf.remote_timeout, OUTPUT_DIR.resolve())

    try:
        results = query_irsa(coord, SEARCH_RADIUS, COLLECTIONS)
    except RuntimeError as exc:
        log.error("%s", exc)
        return 1

    log.debug("Available metadata columns: %s", results.colnames)

    rows_to_download = results[:MAX_FILES]
    if len(results) > MAX_FILES:
        log.info("Limiting to first %d of %d images (MAX_FILES)", MAX_FILES, len(results))

    downloaded: list[Path] = []
    cached: list[Path] = []
    failed: list[str] = []
    total = len(rows_to_download)

    for idx, row in enumerate(rows_to_download, start=1):
        url        = row["access_url"]
        collection = row.get("obs_collection", "unknown")
        obs_id     = row.get("obs_id",         f"img{idx:03d}")
        band       = row.get("energy_bandpassname", "")

        # Build a tidy local filename
        safe_obs_id = str(obs_id).replace("/", "_").replace(" ", "_")
        filename    = f"{collection}_{safe_obs_id}_{band}.fits".replace(" ", "_")
        out_path    = OUTPUT_DIR / filename

        log.info("[%d/%d] %s", idx, total, filename)
        log.debug("  URL: %s", url)

        if out_path.exists():
            log.info("  Already on disk (%s), skipping download",
                     fmt_size(out_path.stat().st_size))
            cached.append(out_path)
        elif download_fits(url, out_path):
            downloaded.append(out_path)
        else:
            log.error("  Download failed: %s", filename)
            failed.append(filename)
            continue

        summarise_file(out_path)

    elapsed = time.monotonic() - run_start
    log.info("Done in %.1fs. Downloaded: %d, cached: %d, failed: %d. Output: %s",
             elapsed, len(downloaded), len(cached), len(failed), OUTPUT_DIR.resolve())
    for name in failed:
        log.warning("  Failed: %s", name)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
