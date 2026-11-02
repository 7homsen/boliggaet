from fastapi import FastAPI

from app.api import game, health

app = FastAPI(title="Boliggaet")
app.include_router(health.router)
app.include_router(game.router)
