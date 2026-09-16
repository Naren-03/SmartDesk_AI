from fastapi import FastAPI


app = FastAPI()


@app.get("/safe")
def safe_endpoint():
    return {"message": "This is a safe endpoint."}

