import logging
import os
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import Base, engine
from app.api.routes import (
    auth, contacts, campaigns, chatbot,
    analytics, team, whatsapp
)
from app.api.routes import (
    message_log, auto_replies, templates,
    subscription_requests, settings as settings_route,
    inbox, media, interactive_menus
)

# ── DB Tables ─────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = "WhatsChat AI — WhatsApp Marketing Platform API",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.CORS_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Static files (uploaded media) ────────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,                   prefix="/api")
app.include_router(contacts.router,               prefix="/api")
app.include_router(campaigns.router,              prefix="/api")
app.include_router(chatbot.router,                prefix="/api")
app.include_router(analytics.router,              prefix="/api")
app.include_router(team.router,                   prefix="/api")
app.include_router(whatsapp.router,               prefix="/api")
app.include_router(message_log.router,            prefix="/api")
app.include_router(auto_replies.router,           prefix="/api")
app.include_router(templates.router,              prefix="/api")
app.include_router(subscription_requests.router,  prefix="/api")
app.include_router(settings_route.router,         prefix="/api")
app.include_router(inbox.router,                  prefix="/api")
app.include_router(media.router,                  prefix="/api")
app.include_router(interactive_menus.router,       prefix="/api")


@app.get("/")
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
        "status":  "running ✅"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}