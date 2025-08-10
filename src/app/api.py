"""FastAPI endpoints for the Bilbasen Fiat Panda Finder."""

from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
import pandas as pd

from .config import settings
from .db import get_session, ListingCRUD, create_db_and_tables
from .models import ListingRead, ListingCreate, ScoreDistribution
from .scraper.scraper import scrape_bilbasen_listings
from .scoring import score_listings_dataframe, get_score_breakdown
from .logging_conf import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger("api")

# Create FastAPI app
app = FastAPI(
    title="Bilbasen Fiat Panda Finder",
    description="API for finding and scoring Fiat Panda listings on Bilbasen.dk",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting up Bilbasen API")
    create_db_and_tables()
    logger.info("Database tables created/verified")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Bilbasen Fiat Panda Finder",
        "version": "1.0.0"
    }


# Listings endpoints
@app.get("/listings", response_model=List[ListingRead], tags=["Listings"])
async def get_listings(
    skip: int = Query(0, ge=0, description="Number of listings to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of listings to return"),
    order_by: str = Query("score", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price in DKK"),
    max_price: Optional[int] = Query(None, ge=0, description="Maximum price in DKK"),
    min_year: Optional[int] = Query(None, ge=1980, le=2030, description="Minimum year"),
    max_year: Optional[int] = Query(None, ge=1980, le=2030, description="Maximum year"),
    min_km: Optional[int] = Query(None, ge=0, description="Minimum kilometers"),
    max_km: Optional[int] = Query(None, ge=0, description="Maximum kilometers"),
    session: Session = Depends(get_session)
) -> List[ListingRead]:
    """
    Get listings with optional filtering and pagination.
    """
    try:
        listings = ListingCRUD.get_listings(
            session=session,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
            min_price=min_price,
            max_price=max_price,
            min_year=min_year,
            max_year=max_year,
            min_km=min_km,
            max_km=max_km
        )
        
        logger.info(f"Retrieved {len(listings)} listings with filters")
        return [ListingRead.model_validate(listing) for listing in listings]
        
    except Exception as e:
        logger.error(f"Error retrieving listings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve listings")


@app.get("/listings/{listing_id}", response_model=ListingRead, tags=["Listings"])
async def get_listing(
    listing_id: int,
    session: Session = Depends(get_session)
) -> ListingRead:
    """Get a specific listing by ID."""
    try:
        listing = ListingCRUD.get_listing(session, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        return ListingRead.model_validate(listing)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving listing {listing_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve listing")


@app.get("/top10", response_model=List[ListingRead], tags=["Listings"])
async def get_top_listings(
    limit: int = Query(10, ge=1, le=50, description="Number of top listings to return"),
    session: Session = Depends(get_session)
) -> List[ListingRead]:
    """Get top listings by score."""
    try:
        listings = ListingCRUD.get_top_listings(session, limit)
        logger.info(f"Retrieved top {len(listings)} listings")
        
        return [ListingRead.model_validate(listing) for listing in listings]
        
    except Exception as e:
        logger.error(f"Error retrieving top listings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve top listings")


# Score statistics endpoints
@app.get("/scores", tags=["Scores"])
async def get_score_statistics(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get score distribution statistics."""
    try:
        stats = ListingCRUD.get_score_stats(session)
        logger.info("Retrieved score statistics")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving score statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve score statistics")


@app.get("/scores/distribution", tags=["Scores"])
async def get_score_distribution(
    session: Session = Depends(get_session)
) -> List[int]:
    """Get all scores for plotting distribution."""
    try:
        scores = ListingCRUD.get_all_scores(session)
        logger.info(f"Retrieved {len(scores)} scores for distribution")
        
        return scores
        
    except Exception as e:
        logger.error(f"Error retrieving score distribution: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve score distribution")


@app.get("/scores/breakdown", tags=["Scores"])
async def get_detailed_score_breakdown(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get comprehensive score breakdown for analysis."""
    try:
        # Get all listings as DataFrame
        listings = ListingCRUD.get_listings(session, skip=0, limit=10000)
        
        if not listings:
            return {
                "error": "No listings found",
                "total_listings": 0
            }
        
        # Convert to DataFrame
        data = []
        for listing in listings:
            data.append({
                "id": listing.id,
                "title": listing.title,
                "price_dkk": listing.price_dkk,
                "year": listing.year,
                "kilometers": listing.kilometers,
                "condition_score": listing.condition_score,
                "score": listing.score,
                "url": listing.url
            })
        
        df = pd.DataFrame(data)
        breakdown = get_score_breakdown(df)
        
        logger.info("Generated detailed score breakdown")
        return breakdown
        
    except Exception as e:
        logger.error(f"Error generating score breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate score breakdown")


# Scraping endpoints
@app.post("/scrape", tags=["Scraping"])
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    max_pages: int = Query(3, ge=1, le=10, description="Maximum pages to scrape"),
    include_details: bool = Query(True, description="Include detailed listing information"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Trigger background scraping of Bilbasen listings."""
    try:
        # Add scraping task to background
        background_tasks.add_task(
            scrape_and_store_listings,
            max_pages,
            include_details,
            session
        )
        
        logger.info(f"Triggered scraping task: max_pages={max_pages}, include_details={include_details}")
        
        return {
            "message": "Scraping task started",
            "max_pages": max_pages,
            "include_details": include_details,
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error triggering scraping: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger scraping")


@app.post("/scrape/sync", tags=["Scraping"])
async def scrape_sync(
    max_pages: int = Query(2, ge=1, le=5, description="Maximum pages to scrape"),
    include_details: bool = Query(False, description="Include detailed listing information"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Synchronous scraping for immediate results (limited scope)."""
    try:
        logger.info(f"Starting synchronous scraping: max_pages={max_pages}")
        
        # Scrape listings
        scraped_listings = await scrape_bilbasen_listings(max_pages, include_details)
        
        if not scraped_listings:
            return {
                "message": "No listings found",
                "scraped_count": 0,
                "stored_count": 0
            }
        
        # Store in database
        stored_count = 0
        scored_count = 0
        
        for listing_data in scraped_listings:
            try:
                # Store listing (upsert)
                stored_listing = ListingCRUD.upsert_listing(session, listing_data)
                stored_count += 1
                
                # Count if it has a score
                if stored_listing.score is not None:
                    scored_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to store listing {listing_data.url}: {e}")
        
        # Re-score all listings if we have new data
        if stored_count > 0:
            await rescore_all_listings(session)
        
        logger.info(f"Synchronous scraping completed: {stored_count} stored, {scored_count} scored")
        
        return {
            "message": "Scraping completed",
            "scraped_count": len(scraped_listings),
            "stored_count": stored_count,
            "scored_count": scored_count
        }
        
    except Exception as e:
        logger.error(f"Error in synchronous scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


# Utility endpoints
@app.post("/rescore", tags=["Utility"])
async def rescore_listings(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Recalculate scores for all listings."""
    try:
        updated_count = await rescore_all_listings(session)
        
        logger.info(f"Rescored {updated_count} listings")
        
        return {
            "message": "Rescoring completed",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error rescoring listings: {e}")
        raise HTTPException(status_code=500, detail="Failed to rescore listings")


@app.get("/stats", tags=["Utility"])
async def get_database_stats(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get database statistics."""
    try:
        total_listings = ListingCRUD.count_listings(session)
        score_stats = ListingCRUD.get_score_stats(session)
        
        logger.info("Retrieved database statistics")
        
        return {
            "total_listings": total_listings,
            "score_statistics": score_stats,
            "search_term": settings.search_term,
            "scoring_weights": settings.get_scoring_weights()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving database stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database stats")


# Background task functions
async def scrape_and_store_listings(max_pages: int, include_details: bool, session: Session):
    """Background task to scrape and store listings."""
    try:
        logger.info(f"Background scraping started: max_pages={max_pages}")
        
        # Scrape listings
        scraped_listings = await scrape_bilbasen_listings(max_pages, include_details)
        
        if not scraped_listings:
            logger.warning("No listings found in background scraping")
            return
        
        # Store in database
        stored_count = 0
        for listing_data in scraped_listings:
            try:
                ListingCRUD.upsert_listing(session, listing_data)
                stored_count += 1
            except Exception as e:
                logger.warning(f"Failed to store listing in background: {e}")
        
        # Re-score all listings
        if stored_count > 0:
            await rescore_all_listings(session)
        
        logger.info(f"Background scraping completed: {stored_count} listings stored")
        
    except Exception as e:
        logger.error(f"Error in background scraping: {e}")


async def rescore_all_listings(session: Session) -> int:
    """Rescore all listings in the database."""
    try:
        # Get all listings
        all_listings = ListingCRUD.get_listings(session, skip=0, limit=10000)
        
        if not all_listings:
            logger.info("No listings to rescore")
            return 0
        
        # Convert to DataFrame
        data = []
        for listing in all_listings:
            data.append({
                "id": listing.id,
                "price_dkk": listing.price_dkk,
                "year": listing.year,
                "kilometers": listing.kilometers,
                "condition_score": listing.condition_score,
            })
        
        df = pd.DataFrame(data)
        
        # Score the DataFrame
        scored_df = score_listings_dataframe(df)
        
        # Update listings with new scores
        updated_count = 0
        for _, row in scored_df.iterrows():
            try:
                from .models import ListingUpdate
                update_data = ListingUpdate(
                    score=row.get('score'),
                    price_score=row.get('price_score'),
                    year_score=row.get('year_score'),
                    kilometers_score=row.get('kilometers_score')
                )
                
                ListingCRUD.update_listing(session, row['id'], update_data)
                updated_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to update scores for listing {row['id']}: {e}")
        
        logger.info(f"Updated scores for {updated_count} listings")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error rescoring listings: {e}")
        raise