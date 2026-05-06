from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .runtime import get_repository
from .routes import router

app = FastAPI(
    title="LandfillSentry Ops API",
    version="0.8.0",
    description="LandfillSentry operations API for watchlist triage, evidence review, and export.",
)

app.include_router(router)

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_UI_ROOT = PROJECT_ROOT / "frontend ui"
if WEB_ROOT.exists():
    app.mount("/ui", StaticFiles(directory=str(WEB_ROOT)), name="ui")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/ops")
def ops_console() -> FileResponse:
    return FileResponse(
        WEB_ROOT / "ops.html",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


DESIGN_PAGES = {
    "watchlist": ("Watchlist Dashboard", FRONTEND_UI_ROOT / "watchlist_dashboard" / "code.html"),
    "map-1": ("Watchlist Map View 1", FRONTEND_UI_ROOT / "watchlist_dashboard_map_view_1" / "code.html"),
    "map-2": ("Watchlist Map View 2", FRONTEND_UI_ROOT / "watchlist_dashboard_map_view_2" / "code.html"),
    "site-detail": ("Site Detail Analysis", FRONTEND_UI_ROOT / "site_detail_analysis" / "code.html"),
    "triage": ("Incident Triage Console", FRONTEND_UI_ROOT / "incident_triage_console" / "code.html"),
    "evidence-export": ("Evidence Pack Export", FRONTEND_UI_ROOT / "evidence_pack_export" / "code.html"),
}


@app.get("/ops/design", response_class=HTMLResponse)
def ops_design_index() -> HTMLResponse:
    links = "\n".join(
        f'<li><a href="/ops/design/{slug}">{title}</a></li>'
        for slug, (title, _path) in DESIGN_PAGES.items()
    )
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LandfillSentry UI Design Pages</title>
    <style>
      body {{ margin: 0; min-height: 100vh; background: #0b1326; color: #dae2fd; font-family: Inter, Segoe UI, sans-serif; }}
      main {{ max-width: 760px; margin: 0 auto; padding: 56px 24px; }}
      a {{ color: #38bdf8; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      li {{ margin: 14px 0; padding: 14px; background: #121b2f; border: 1px solid #334155; border-radius: 6px; }}
      .back {{ display: inline-block; margin-bottom: 24px; color: #94a3b8; }}
    </style>
  </head>
  <body>
    <main>
      <a class="back" href="/ops">Back to live console</a>
      <h1>LandfillSentry UI Design Pages</h1>
      <p>Pixel-oriented static mockups from the original <code>frontend ui</code> folder.</p>
      <ul>{links}<li><a href="/ops/design/orbital-precision">Orbital Precision Design Notes</a></li></ul>
    </main>
  </body>
</html>"""
    )


@app.get("/ops/design/orbital-precision")
def orbital_precision_design() -> FileResponse:
    return FileResponse(FRONTEND_UI_ROOT / "orbital_precision" / "DESIGN.md", media_type="text/plain")


@app.get("/ops/design/{page_slug}")
def ops_design_page(page_slug: str) -> FileResponse:
    page = DESIGN_PAGES.get(page_slug)
    if not page:
        return FileResponse(WEB_ROOT / "ops.html")
    return FileResponse(page[1])


@app.on_event("startup")
def startup() -> None:
    # Ensure DB schema is initialized on boot.
    get_repository()
