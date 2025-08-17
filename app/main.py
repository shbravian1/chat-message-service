# app/main.py

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.models.database import Base, get_engine
from app.api.routes import router
from app.utils.rate_limit import add_rate_limiting
import logging
import traceback
import time
import uuid
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Chat Storage API",
    description="Simple chat storage system with OpenAI integration",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
add_rate_limiting(app)

# Include routes
app.include_router(router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


@app.on_event("startup")
async def startup_event():
    # Wait for database with retries
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create engine and test connection
            engine = get_engine(settings.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()

            # Create tables if connection successful
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database connected and tables created successfully")
            break

        except OperationalError as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"❌ Failed to connect to database after {max_retries} attempts")
                raise
            logger.warning(
                f"⏳ Database connection attempt {retry_count}/{max_retries} failed. Retrying in 2 seconds...")
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Unexpected error during startup: {str(e)}")
            raise


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Log request
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Request {request_id} completed in {process_time:.3f}s "
        f"with status {response.status_code}"
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.get("/")
async def root():
    return {"message": "Chat Storage API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    try:
        # Check database connection
        engine = get_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return {
            "status": "healthy",
            "database": "connected",
            "service": "Chat Storage API"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
