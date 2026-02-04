"""
FastAPI Application Factory

This module provides the create_app factory function that initializes the
FastAPI application with all routers, middleware, and event handlers.

This is the main application entry point that configures:
- All API routers (health, metrics, OCR, root)
- Middleware (CORS, error handlers, rate limiting, logging)
- Startup and shutdown event handlers
- OpenAPI metadata and documentation

Validates: Requirements 1.4, 4.7, 8.1, 8.2, 8.3
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import time
from typing import AsyncGenerator

from app.config import Settings, get_settings
from app.utils.logger import setup_logging, get_logger
from app.middleware.error_handler import register_exception_handlers
from app.middleware.rate_limiter import (
    get_rate_limiter,
    rate_limit_exceeded_handler
)

# Import routers
from app.routers import health, metrics, ocr, root

# Import services for cleanup
from app.routers.ocr import _ocr_service_instance, _model_registry_instance


# Get logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application.
    This includes initializing resources on startup and cleaning up
    resources on shutdown.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control is yielded to the application during its lifetime
        
    Validates: Requirements 10.4
    """
    # Startup
    settings = get_settings()
    logger.info(
        "Application starting up",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment
    )
    
    # Log configuration (without sensitive data)
    logger.info(
        "Configuration loaded",
        ocr_model=settings.ocr_model_id,
        rate_limit=f"{settings.rate_limit_per_minute}/minute",
        max_file_size=f"{settings.max_file_size_mb}MB",
        ocr_timeout=f"{settings.ocr_timeout_seconds}s",
        log_level=settings.log_level
    )
    
    logger.info(
        "Dynamic model discovery enabled",
        info="Models will be fetched on first request or when errors occur"
    )
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    
    # Close model registry HTTP client
    global _model_registry_instance
    if _model_registry_instance is not None:
        try:
            await _model_registry_instance.close()
            logger.info("Model registry HTTP client closed")
        except Exception as e:
            logger.error(
                "Error closing model registry",
                error=str(e),
                exc_info=True
            )
    
    # Close OCR service HTTP client
    global _ocr_service_instance
    if _ocr_service_instance is not None:
        try:
            await _ocr_service_instance.close()
            logger.info("OCR service HTTP client closed")
        except Exception as e:
            logger.error(
                "Error closing OCR service",
                error=str(e),
                exc_info=True
            )
    
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    This factory function creates a FastAPI application instance with:
    - All routers included (health, metrics, OCR, root)
    - Middleware configured (CORS, error handlers, rate limiting)
    - Startup and shutdown event handlers
    - OpenAPI metadata and documentation
    
    Returns:
        FastAPI: Configured FastAPI application instance
        
    Example:
        >>> app = create_app()
        >>> # Run with: uvicorn app.main:app --reload
        
    Validates: Requirements 1.4, 4.7, 8.1, 8.2, 8.3
    """
    # Get settings
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file
    )
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        ## Handwriting OCR Service
        
        A modern, production-ready FastAPI backend service for handwriting OCR processing.
        
        ### Features
        
        - **Asynchronous Processing**: High-performance async I/O operations
        - **Rate Limiting**: IP-based rate limiting to prevent abuse
        - **Comprehensive Error Handling**: Structured error responses with detailed logging
        - **Health Monitoring**: Real-time health checks and system resource monitoring
        - **Performance Metrics**: Detailed metrics collection and reporting
        - **Input Validation**: Robust file validation and sanitization
        - **Security**: CORS, file size limits, and input sanitization
        - **OpenAPI Documentation**: Interactive API documentation with examples
        
        ### Endpoints
        
        - `GET /`: API information and available endpoints
        - `GET /health`: Comprehensive health check
        - `GET /metrics`: Performance metrics and statistics
        - `POST /read-handwriting`: Extract handwritten text from images
        - `GET /docs`: Interactive Swagger UI documentation
        - `GET /redoc`: ReDoc documentation
        
        ### Rate Limits
        
        - OCR endpoint: 10 requests per minute per IP
        - Metrics endpoint: 60 requests per minute per IP
        - Health endpoint: 120 requests per minute per IP
        
        ### Supported Image Formats
        
        - JPEG
        - PNG
        - WebP
        
        ### Maximum File Size
        
        10MB per image
        
        ### Authentication
        
        Currently no authentication required. API key authentication can be added in future versions.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "API Support",
            "email": "support@example.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"]
    )
    
    # Setup rate limiter
    limiter = get_rate_limiter(settings)
    app.state.limiter = limiter
    
    # Register rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Register error handlers
    register_exception_handlers(app)
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """
        Log all incoming requests and responses.
        
        This middleware logs request details and response times for monitoring
        and debugging purposes.
        """
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Incoming request",
            method=request.method,
            path=str(request.url.path),
            client_host=request.client.host if request.client else None
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response
    
    # Include routers
    app.include_router(
        root.router,
        tags=["Root"]
    )
    
    app.include_router(
        health.router,
        tags=["Health"]
    )
    
    app.include_router(
        metrics.router,
        tags=["Metrics"]
    )
    
    # Apply rate limiting to OCR router
    @limiter.limit(f"{settings.rate_limit_per_minute}/minute")
    async def rate_limited_ocr_endpoint(request: Request):
        """Rate limited OCR endpoint wrapper."""
        pass
    
    app.include_router(
        ocr.router,
        tags=["OCR"]
    )
    
    logger.info(
        "FastAPI application created successfully",
        routers=["root", "health", "metrics", "ocr"],
        middleware=["CORS", "error_handlers", "rate_limiter", "request_logger"]
    )
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    # Run with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
