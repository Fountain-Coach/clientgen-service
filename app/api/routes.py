from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Client Generator Service is up and running."}
