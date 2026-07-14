import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.projects.routes import router as projects_router
from app.tasks.routes import router as tasks_router
from app.users.routes import router as users_router
from app.dashboard.routes import router as dashboard_router
from app.response import success_response, error_response

logger = logging.getLogger(__name__)

app = FastAPI(title="Employee Task Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(dashboard_router)


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=exc.detail),
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(
        status_code=422,
        content=error_response(message="Validation error", error=errors),
    )


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=error_response(message="Internal server error"),
    )


@app.get("/")
def home():
    return success_response(message="API Running")
