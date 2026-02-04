"""
API Routers Package

Contains all API endpoint route handlers:
- health: Health check endpoints
- metrics: Performance metrics endpoints
- ocr: OCR processing endpoints
- root: Root API information endpoint
"""

from app.routers.health import router as health_router

__all__ = ["health_router"]
