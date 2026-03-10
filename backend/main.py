from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.visitors import router as visitors_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(visitors_router, prefix="/api")
from routes.otp import router as otp_router
app.include_router(otp_router, prefix="/api")
from routes.passes import router as passes_router
app.include_router(passes_router, prefix="/api")
from routes.guard import router as guard_router
app.include_router(guard_router, prefix="/api")
from routes.admin import router as admin_router
app.include_router(admin_router, prefix="/api")


@app.get("/")
def root():
    return {"status": "SafeEntry Pro API Running", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
