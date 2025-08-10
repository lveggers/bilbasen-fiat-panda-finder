"""FastAPI server with Jinja2 templates for the Bilbasen Fiat Panda Finder."""

from typing import Dict, Any, List
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
import json

from .api import app as api_app
from .config import settings
from .db import get_session, ListingCRUD
from .models import ListingRead
from .logging_conf import get_logger

logger = get_logger("server")

# Create main FastAPI app that includes the API
app = FastAPI(
    title="Bilbasen Fiat Panda Finder",
    description="Web application for finding and scoring Fiat Panda listings",
    version="1.0.0"
)

# Mount the API routes
app.mount("/api/v1", api_app)

# Mount static files
app.mount("/static", StaticFiles(directory="src/app/ui/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="src/app/ui/templates")

# Web UI routes
@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
async def dashboard(
    request: Request,
    session: Session = Depends(get_session)
):
    """Main dashboard page."""
    try:
        # Get top listings
        top_listings = ListingCRUD.get_top_listings(session, limit=10)
        
        # Get score statistics
        score_stats = ListingCRUD.get_score_stats(session)
        
        # Get all scores for distribution chart
        all_scores = ListingCRUD.get_all_scores(session)
        
        # Prepare data for templates
        context = {
            "request": request,
            "top_listings": [ListingRead.model_validate(listing) for listing in top_listings],
            "score_stats": score_stats,
            "all_scores": all_scores,
            "search_term": settings.search_term,
            "total_listings": len(all_scores),
            "settings": {
                "weights": settings.get_scoring_weights(),
                "search_term": settings.search_term
            }
        }
        
        logger.info(f"Rendered dashboard with {len(top_listings)} top listings")
        return templates.TemplateResponse("index.html", context)
        
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        # Return error page
        context = {
            "request": request,
            "error": str(e),
            "search_term": settings.search_term
        }
        return templates.TemplateResponse("error.html", context)


@app.get("/listings", response_class=HTMLResponse, tags=["Web UI"])
async def listings_page(
    request: Request,
    page: int = 1,
    min_price: int = None,
    max_price: int = None,
    min_year: int = None,
    max_year: int = None,
    min_km: int = None,
    max_km: int = None,
    session: Session = Depends(get_session)
):
    """Listings page with pagination and filters."""
    try:
        page_size = 20
        skip = (page - 1) * page_size
        
        # Get filtered listings
        listings = ListingCRUD.get_listings(
            session=session,
            skip=skip,
            limit=page_size,
            order_by="score",
            order_desc=True,
            min_price=min_price,
            max_price=max_price,
            min_year=min_year,
            max_year=max_year,
            min_km=min_km,
            max_km=max_km
        )
        
        # Get total count for pagination (simplified)
        total_listings = ListingCRUD.count_listings(session)
        total_pages = (total_listings + page_size - 1) // page_size
        
        context = {
            "request": request,
            "listings": [ListingRead.model_validate(listing) for listing in listings],
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "filters": {
                "min_price": min_price,
                "max_price": max_price,
                "min_year": min_year,
                "max_year": max_year,
                "min_km": min_km,
                "max_km": max_km,
            },
            "search_term": settings.search_term
        }
        
        logger.info(f"Rendered listings page {page} with {len(listings)} listings")
        return templates.TemplateResponse("listings.html", context)
        
    except Exception as e:
        logger.error(f"Error rendering listings page: {e}")
        context = {
            "request": request,
            "error": str(e),
            "search_term": settings.search_term
        }
        return templates.TemplateResponse("error.html", context)


@app.get("/about", response_class=HTMLResponse, tags=["Web UI"])
async def about_page(request: Request):
    """About page with project information."""
    context = {
        "request": request,
        "search_term": settings.search_term,
        "scoring_weights": settings.get_scoring_weights(),
        "version": "1.0.0"
    }
    return templates.TemplateResponse("about.html", context)


# API endpoint for HTMX/JavaScript requests
@app.get("/api/dashboard-data", tags=["Web API"])
async def get_dashboard_data(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get dashboard data for dynamic updates."""
    try:
        # Get top listings
        top_listings = ListingCRUD.get_top_listings(session, limit=10)
        
        # Get score statistics
        score_stats = ListingCRUD.get_score_stats(session)
        
        # Get all scores for distribution
        all_scores = ListingCRUD.get_all_scores(session)
        
        return {
            "top_listings": [
                {
                    "id": listing.id,
                    "title": listing.title,
                    "price_dkk": listing.price_dkk,
                    "year": listing.year,
                    "kilometers": listing.kilometers,
                    "score": listing.score,
                    "url": listing.url,
                    "condition_str": listing.condition_str,
                    "location": listing.location
                }
                for listing in top_listings
            ],
            "score_stats": score_stats,
            "all_scores": all_scores,
            "total_listings": len(all_scores)
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


# Health check for the web server
@app.get("/health", tags=["Health"])
async def web_health_check():
    """Web server health check."""
    return {
        "status": "healthy",
        "service": "Bilbasen Web Server",
        "version": "1.0.0"
    }


# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page."""
    context = {
        "request": request,
        "search_term": settings.search_term
    }
    return templates.TemplateResponse("404.html", context, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page."""
    logger.error(f"Server error: {exc}")
    context = {
        "request": request,
        "search_term": settings.search_term,
        "error": "An internal server error occurred."
    }
    return templates.TemplateResponse("error.html", context, status_code=500)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Bilbasen Fiat Panda Finder server")
    uvicorn.run(
        "app.server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
        log_level=settings.log_level.lower()
    )