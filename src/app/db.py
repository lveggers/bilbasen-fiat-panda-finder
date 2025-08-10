"""Database connection and operations for the Bilbasen Fiat Panda Finder."""

from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, create_engine, Session, select, func, desc, asc
from sqlalchemy.sql import text

from .config import settings
from .models import Listing, ListingCreate, ListingUpdate
from .logging_conf import get_logger

logger = get_logger("db")

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before use
)


def create_db_and_tables():
    """Create database and all tables."""
    logger.info("Creating database tables")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session


class ListingCRUD:
    """CRUD operations for Listing model."""

    @staticmethod
    def create_listing(session: Session, listing: ListingCreate) -> Listing:
        """Create a new listing."""
        db_listing = Listing.model_validate(listing)
        session.add(db_listing)
        session.commit()
        session.refresh(db_listing)
        logger.info(f"Created listing: {db_listing.id}")
        return db_listing

    @staticmethod
    def get_listing(session: Session, listing_id: int) -> Optional[Listing]:
        """Get a listing by ID."""
        return session.get(Listing, listing_id)

    @staticmethod
    def get_listing_by_url(session: Session, url: str) -> Optional[Listing]:
        """Get a listing by URL."""
        statement = select(Listing).where(Listing.url == url)
        return session.exec(statement).first()

    @staticmethod
    def get_listings(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "score",
        order_desc: bool = True,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_km: Optional[int] = None,
        max_km: Optional[int] = None,
    ) -> List[Listing]:
        """Get listings with optional filtering and pagination."""
        statement = select(Listing)

        # Apply filters
        if min_price is not None:
            statement = statement.where(Listing.price_dkk >= min_price)
        if max_price is not None:
            statement = statement.where(Listing.price_dkk <= max_price)
        if min_year is not None:
            statement = statement.where(Listing.year >= min_year)
        if max_year is not None:
            statement = statement.where(Listing.year <= max_year)
        if min_km is not None:
            statement = statement.where(Listing.kilometers >= min_km)
        if max_km is not None:
            statement = statement.where(Listing.kilometers <= max_km)

        # Apply ordering
        if hasattr(Listing, order_by):
            order_column = getattr(Listing, order_by)
            if order_desc:
                statement = statement.order_by(desc(order_column))
            else:
                statement = statement.order_by(asc(order_column))

        # Apply pagination
        statement = statement.offset(skip).limit(limit)

        return session.exec(statement).all()

    @staticmethod
    def get_top_listings(session: Session, limit: int = 10) -> List[Listing]:
        """Get top listings by score."""
        statement = (
            select(Listing)
            .where(Listing.score.is_not(None))
            .order_by(desc(Listing.score))
            .limit(limit)
        )
        return session.exec(statement).all()

    @staticmethod
    def update_listing(
        session: Session, listing_id: int, listing_update: ListingUpdate
    ) -> Optional[Listing]:
        """Update a listing."""
        db_listing = session.get(Listing, listing_id)
        if not db_listing:
            return None

        listing_data = listing_update.model_dump(exclude_unset=True)
        for key, value in listing_data.items():
            setattr(db_listing, key, value)

        session.add(db_listing)
        session.commit()
        session.refresh(db_listing)
        logger.info(f"Updated listing: {listing_id}")
        return db_listing

    @staticmethod
    def delete_listing(session: Session, listing_id: int) -> bool:
        """Delete a listing."""
        db_listing = session.get(Listing, listing_id)
        if not db_listing:
            return False

        session.delete(db_listing)
        session.commit()
        logger.info(f"Deleted listing: {listing_id}")
        return True

    @staticmethod
    def upsert_listing(session: Session, listing: ListingCreate) -> Listing:
        """Insert or update a listing based on URL."""
        existing = ListingCRUD.get_listing_by_url(session, listing.url)
        if existing:
            # Update existing listing
            update_data = ListingUpdate(**listing.model_dump())
            return ListingCRUD.update_listing(session, existing.id, update_data)
        else:
            # Create new listing
            return ListingCRUD.create_listing(session, listing)

    @staticmethod
    def get_score_stats(session: Session) -> Dict[str, Any]:
        """Get score distribution statistics."""
        # Basic stats
        stats_query = select(
            func.min(Listing.score).label("min_score"),
            func.max(Listing.score).label("max_score"),
            func.avg(Listing.score).label("mean_score"),
            func.count(Listing.score).label("total_count"),
        ).where(Listing.score.is_not(None))

        result = session.exec(stats_query).first()

        if not result or result.total_count == 0:
            return {
                "min_score": 0,
                "max_score": 0,
                "mean_score": 0.0,
                "total_listings": 0,
                "score_ranges": {},
            }

        # Score distribution by ranges
        ranges_query = text(
            """
            SELECT 
                CASE 
                    WHEN score < 20 THEN '0-19'
                    WHEN score < 40 THEN '20-39'
                    WHEN score < 60 THEN '40-59'
                    WHEN score < 80 THEN '60-79'
                    ELSE '80-100'
                END as score_range,
                COUNT(*) as count
            FROM listing 
            WHERE score IS NOT NULL 
            GROUP BY score_range
            ORDER BY score_range
        """
        )

        ranges_result = session.exec(ranges_query).all()
        score_ranges = {row[0]: row[1] for row in ranges_result}

        return {
            "min_score": result.min_score or 0,
            "max_score": result.max_score or 0,
            "mean_score": float(result.mean_score) if result.mean_score else 0.0,
            "total_listings": result.total_count,
            "score_ranges": score_ranges,
        }

    @staticmethod
    def get_all_scores(session: Session) -> List[int]:
        """Get all scores for plotting."""
        statement = select(Listing.score).where(Listing.score.is_not(None))
        results = session.exec(statement).all()
        return [score for score in results if score is not None]

    @staticmethod
    def count_listings(session: Session) -> int:
        """Count total number of listings."""
        statement = select(func.count(Listing.id))
        return session.exec(statement).one()

    @staticmethod
    def cleanup_old_listings(session: Session, days: int = 7) -> int:
        """Remove listings older than specified days."""
        cutoff_query = text(
            """
            DELETE FROM listing 
            WHERE fetched_at < datetime('now', '-{} days')
        """.format(
                days
            )
        )

        result = session.exec(cutoff_query)
        session.commit()
        logger.info(f"Cleaned up {result.rowcount} old listings")
        return result.rowcount
