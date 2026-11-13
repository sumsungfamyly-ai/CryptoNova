import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "backend"), ROOT):  # package may live in backend/ or directly in the repo root
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from novaapi.main import app  # ASGI app served by Vercel's Python runtime
except Exception as e:  # start-up failure: show WHY on /health instead of a blank 500
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    if hasattr(e, "errors"):  # settings validation: names of the bad variables only, never their values
        try:
            reason = "invalid environment variables: " + ", ".join(sorted({str(x["loc"][0]) for x in e.errors()}))
        except Exception:
            reason = type(e).__name__
    else:
        reason = f"{type(e).__name__}: {e}"[:400]
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def startup_error(path: str):
        return JSONResponse({"status": "startup_error", "error": reason,
                             "hint": "Откройте Vercel -> Logs. Часто причина: не установлен пакет или неверная переменная окружения."}, status_code=500)
