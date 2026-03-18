from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import chat, appointments, voice
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kyron Medical Assistant API")

_extra_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"] + [
    o.strip() for o in _extra_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(appointments.router)
app.include_router(voice.router)


@app.on_event("startup")
async def startup():
    try:
        logger.info("Kyron Medical Assistant API starting up...")
        routes = [
            f"{route.methods} {route.path}"
            for route in app.routes
            if hasattr(route, "methods")
        ]
        for route in routes:
            logger.info(f"  Route: {route}")
        logger.info("API ready!")
    except Exception as exc:
        logger.error(f"Startup logging error: {exc}")


@app.get("/")
async def root():
    return {"message": "Kyron Medical Assistant API", "status": "running"}
