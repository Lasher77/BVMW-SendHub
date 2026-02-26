from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, departments, settings, campaigns, schedule, users

app = FastAPI(
    title="BVMW SendHub",
    description="Interne Web-App zur Planung & Freigabe von Email-Aussendungen.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(settings.router)
app.include_router(campaigns.router)
app.include_router(schedule.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
