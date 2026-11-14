"""ASGI entrypoint. If the real app cannot start, serve a readable error page (shown on /health) instead of a blank 500."""
try:
    from novaapi.main import app
except Exception as e:  # start-up failure
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
