from fastapi import APIRouter

r = APIRouter()

@r.get("/")

async def test():
    return {"message": "Hello World"}