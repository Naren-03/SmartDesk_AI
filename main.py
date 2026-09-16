from fastapi import FastAPI
from routes.api.v1.users import router as user_router

app = FastAPI()




app.include_router(user_router, prefix="/api/v1/users", tags=["users"])

@app.get("/safe")
def safe_endpoint():
    return {"message": "This is a safe endpoint."}


