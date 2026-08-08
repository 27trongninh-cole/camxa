import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import edits

app = FastAPI(title="PKG Editor")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
VERSION_PATH = Path(__file__).parent / "data" / "version.txt"


def get_game_version() -> str:
    return VERSION_PATH.read_text(encoding="utf-8").strip()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/version")
def version():
    return {"game_version": get_game_version()}


@app.get("/api/generate")
def generate(
    insert_back_snippet: bool = Query(True, description="Chèn Track vào Back.xml"),
    height_rate: float = Query(
        1.0, ge=edits.HEIGHT_RATE_MIN, le=edits.HEIGHT_RATE_MAX,
        description="Hệ số heightRate (1.000 - 5.000)"
    ),
):
    try:
        common_pkg = edits.build_common_pkg(insert_back_snippet=insert_back_snippet)
        actor_pkg = edits.build_actor530_pkg(height_rate=height_rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    version = get_game_version()
    base_path = f"Resources/{version}/Ages/Prefab_Characters/Prefab_Hero"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_path}/CommonActions_pkg.bytes", common_pkg)
        zf.writestr(f"{base_path}/Actor_530_Actions_pkg.bytes", actor_pkg)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=pkg_edited.zip"},
    )


# Serve frontend static files (must be mounted last so /api routes take priority)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
