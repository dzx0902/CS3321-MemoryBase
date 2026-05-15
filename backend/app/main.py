from fastapi import FastAPI

app = FastAPI(title="MemoryBase API")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "memorybase"}
