import io
import zipfile
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

import edits

app = FastAPI(title="PKG Editor")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
VERSION_PATH = Path(__file__).parent / "data" / "version.txt"

RATE_STEP = 0.5


def get_game_version() -> str:
    return VERSION_PATH.read_text(encoding="utf-8").strip()


def snap_to_step(value: float, step: float = RATE_STEP) -> float:
    """Round to the nearest multiple of `step` (e.g. 1.4 -> 1.5)."""
    snapped = round(value / step) * step
    snapped = round(snapped, 3)
    return min(edits.HEIGHT_RATE_MAX, max(edits.HEIGHT_RATE_MIN, snapped))


def format_multiplier_vn(value: float) -> str:
    """Format a multiplier like the frontend does: 'x1', 'x1,5', 'x3,5' ..."""
    s = f"{value:.3f}".rstrip("0").rstrip(".")
    return "x" + s.replace(".", ",")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/generate")
def generate(
    height_rate: float = Query(
        1.0, ge=edits.HEIGHT_RATE_MIN, le=edits.HEIGHT_RATE_MAX,
        description="Hệ số heightRate (1.0 - 5.0, bội số của 0.5)"
    ),
):
    snapped_rate = snap_to_step(height_rate)

    try:
        common_pkg = edits.build_common_pkg(insert_back_snippet=True)
        actor_pkg = edits.build_actor530_pkg(height_rate=snapped_rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    game_version = get_game_version()
    base_path = f"Resources/{game_version}/Ages/Prefab_Characters/Prefab_Hero"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_path}/CommonActions_pkg.bytes", common_pkg)
        zf.writestr(f"{base_path}/Actor_530_Actions_pkg.bytes", actor_pkg)
    buf.seek(0)

    multiplier_label = format_multiplier_vn(snapped_rate)
    filename = f"Camera {multiplier_label} - Ninfinity.zip"
    # ASCII-safe fallback (some clients don't parse filename*) + proper UTF-8 name
    ascii_fallback = filename.encode("ascii", "ignore").decode("ascii") or "download.zip"
    from urllib.parse import quote
    content_disposition = (
        f"attachment; filename=\"{ascii_fallback}\"; "
        f"filename*=UTF-8''{quote(filename)}"
    )

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": content_disposition},
    )


# Serve frontend static files (must be mounted last so /api routes take priority)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
