from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import templates, storytelling, pptx

app = FastAPI(title="PPMaker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(templates.router, prefix="/api/v1")
app.include_router(storytelling.router, prefix="/api/v1")
app.include_router(pptx.router, prefix="/api/v1")
