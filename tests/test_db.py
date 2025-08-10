"""Tests for database operations."""

import pytest
from datetime import datetime, timedelta
from sqlmodel import Session

from src.app.db import ListingCRUD, create_db_and_tables
from src.app.models import Listing, ListingCreate, ListingUpdate


@pytest.mark.integration
class TestDatabaseSetup:
    """Test database setup and initialization."""

    def test_create_db_and_tables(self, temp_db):
        """Test database table creation."""
        # Should not raise any exceptions
        create_db_and_tables()

        # Check that tables exist by trying to query
        with Session(temp_db) as session:
            result = session.exec(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [row[0] for row in result]

            assert "listing" in table_names


@pytest.mark.integration
class TestListingCRUD:
    """Test CRUD operations for Listing model."""

    def test_create_listing(self, test_session, test_utils):
        """Test creating a new listing."""
        listing_data = test_utils.create_test_listing()

        created_listing = ListingCRUD.create_listing(test_session, listing_data)

        assert created_listing.id is not None
        assert created_listing.title == listing_data.title
        assert created_listing.url == listing_data.url
        assert created_listing.price_dkk == listing_data.price_dkk
        assert created_listing.fetched_at is not None

    def test_get_listing_by_id(self, test_session, sample_listings):
        """Test retrieving a listing by ID."""
        original_listing = sample_listings[0]

        retrieved_listing = ListingCRUD.get_listing(test_session, original_listing.id)

        assert retrieved_listing is not None
        assert retrieved_listing.id == original_listing.id
        assert retrieved_listing.title == original_listing.title

    def test_get_listing_by_id_not_found(self, test_session):
        """Test retrieving a non-existent listing."""
        result = ListingCRUD.get_listing(test_session, 99999)

        assert result is None

    def test_get_listing_by_url(self, test_session, sample_listings):
        """Test retrieving a listing by URL."""
        original_listing = sample_listings[0]

        retrieved_listing = ListingCRUD.get_listing_by_url(
            test_session, original_listing.url
        )

        assert retrieved_listing is not None
        assert retrieved_listing.url == original_listing.url
        assert retrieved_listing.id == original_listing.id

    def test_get_listing_by_url_not_found(self, test_session):
        """Test retrieving a listing by non-existent URL."""
        result = ListingCRUD.get_listing_by_url(
            test_session, "https://nonexistent.com/listing"
        )

        assert result is None

    def test_get_listings_basic(self, test_session, sample_listings):
        """Test retrieving listings with default parameters."""
        listings = ListingCRUD.get_listings(test_session)

        assert len(listings) == len(sample_listings)
        assert all(isinstance(listing, Listing) for listing in listings)

    def test_get_listings_with_pagination(self, test_session, sample_listings):
        """Test retrieving listings with pagination."""
        # Get first 2 listings
        page1 = ListingCRUD.get_listings(test_session, skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2 listings
        page2 = ListingCRUD.get_listings(test_session, skip=2, limit=2)
        assert len(page2) == 2

        # Should be different listings
        page1_ids = {listing.id for listing in page1}
        page2_ids = {listing.id for listing in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_listings_with_price_filter(self, test_session, sample_listings):
        """Test retrieving listings with price filters."""
        # Filter for expensive listings (>= 80000)
        expensive_listings = ListingCRUD.get_listings(test_session, min_price=80000)

        assert all(
            listing.price_dkk >= 80000
            for listing in expensive_listings
            if listing.price_dkk
        )
        assert len(expensive_listings) < len(sample_listings)

        # Filter for cheap listings (<= 60000)
        cheap_listings = ListingCRUD.get_listings(test_session, max_price=60000)

        assert all(
            listing.price_dkk <= 60000
            for listing in cheap_listings
            if listing.price_dkk
        )

    def test_get_listings_with_year_filter(self, test_session, sample_listings):
        """Test retrieving listings with year filters."""
        # Filter for newer cars (>= 2020)
        new_cars = ListingCRUD.get_listings(test_session, min_year=2020)

        assert all(listing.year >= 2020 for listing in new_cars if listing.year)

        # Filter for older cars (<= 2018)
        old_cars = ListingCRUD.get_listings(test_session, max_year=2018)

        assert all(listing.year <= 2018 for listing in old_cars if listing.year)

    def test_get_listings_with_km_filter(self, test_session, sample_listings):
        """Test retrieving listings with kilometer filters."""
        # Filter for low mileage (<= 50000)
        low_km = ListingCRUD.get_listings(test_session, max_km=50000)

        assert all(
            listing.kilometers <= 50000 for listing in low_km if listing.kilometers
        )

        # Filter for high mileage (>= 100000)
        high_km = ListingCRUD.get_listings(test_session, min_km=100000)

        assert all(
            listing.kilometers >= 100000 for listing in high_km if listing.kilometers
        )

    def test_get_listings_with_ordering(self, test_session, sample_listings):
        """Test retrieving listings with different ordering."""
        # Order by price ascending
        price_asc = ListingCRUD.get_listings(
            test_session, order_by="price_dkk", order_desc=False
        )

        prices = [listing.price_dkk for listing in price_asc if listing.price_dkk]
        assert prices == sorted(prices)

        # Order by year descending
        year_desc = ListingCRUD.get_listings(
            test_session, order_by="year", order_desc=True
        )

        years = [listing.year for listing in year_desc if listing.year]
        assert years == sorted(years, reverse=True)

    def test_get_top_listings(self, test_session, sample_listings):
        """Test retrieving top listings by score."""
        # First, add some scores to the listings
        for i, listing in enumerate(sample_listings):
            listing.score = 100 - (i * 10)  # Decreasing scores
        test_session.commit()

        top_listings = ListingCRUD.get_top_listings(test_session, limit=3)

        assert len(top_listings) == 3

        # Should be ordered by score descending
        scores = [listing.score for listing in top_listings]
        assert scores == sorted(scores, reverse=True)
        assert scores[0] >= scores[1] >= scores[2]

    def test_update_listing(self, test_session, sample_listings):
        """Test updating a listing."""
        original_listing = sample_listings[0]

        update_data = ListingUpdate(title="Updated Title", price_dkk=999999, score=95)

        updated_listing = ListingCRUD.update_listing(
            test_session, original_listing.id, update_data
        )

        assert updated_listing is not None
        assert updated_listing.title == "Updated Title"
        assert updated_listing.price_dkk == 999999
        assert updated_listing.score == 95

        # Other fields should remain unchanged
        assert updated_listing.url == original_listing.url
        assert updated_listing.year == original_listing.year

    def test_update_listing_not_found(self, test_session):
        """Test updating a non-existent listing."""
        update_data = ListingUpdate(title="New Title")

        result = ListingCRUD.update_listing(test_session, 99999, update_data)

        assert result is None

    def test_delete_listing(self, test_session, sample_listings):
        """Test deleting a listing."""
        original_count = len(sample_listings)
        listing_to_delete = sample_listings[0]

        success = ListingCRUD.delete_listing(test_session, listing_to_delete.id)

        assert success is True

        # Verify it's deleted
        deleted_listing = ListingCRUD.get_listing(test_session, listing_to_delete.id)
        assert deleted_listing is None

        # Verify count decreased
        remaining_listings = ListingCRUD.get_listings(test_session)
        assert len(remaining_listings) == original_count - 1

    def test_delete_listing_not_found(self, test_session):
        """Test deleting a non-existent listing."""
        success = ListingCRUD.delete_listing(test_session, 99999)

        assert success is False

    def test_upsert_listing_create(self, test_session, test_utils):
        """Test upserting a new listing (should create)."""
        listing_data = test_utils.create_test_listing(
            url="https://bilbasen.dk/new/listing"
        )

        result = ListingCRUD.upsert_listing(test_session, listing_data)

        assert result.id is not None
        assert result.url == listing_data.url
        assert result.title == listing_data.title

    def test_upsert_listing_update(self, test_session, sample_listings):
        """Test upserting an existing listing (should update)."""
        existing_listing = sample_listings[0]

        # Create update with same URL but different title
        listing_data = ListingCreate(
            title="Updated via Upsert",
            url=existing_listing.url,  # Same URL
            price_dkk=999999,
        )

        result = ListingCRUD.upsert_listing(test_session, listing_data)

        assert result.id == existing_listing.id  # Same ID
        assert result.title == "Updated via Upsert"
        assert result.price_dkk == 999999
        assert result.url == existing_listing.url

    def test_count_listings(self, test_session, sample_listings):
        """Test counting total listings."""
        count = ListingCRUD.count_listings(test_session)

        assert count == len(sample_listings)

    def test_count_listings_empty_db(self, test_session):
        """Test counting listings in empty database."""
        count = ListingCRUD.count_listings(test_session)

        assert count == 0


@pytest.mark.integration
class TestScoreStatistics:
    """Test score statistics and analytics."""

    def test_get_score_stats_with_data(self, test_session, sample_listings):
        """Test getting score statistics with data."""
        # Add scores to listings
        scores = [85, 70, 95, 45, 60]
        for listing, score in zip(sample_listings, scores):
            listing.score = score
        test_session.commit()

        stats = ListingCRUD.get_score_stats(test_session)

        assert stats["min_score"] == 45
        assert stats["max_score"] == 95
        assert stats["mean_score"] == 71.0  # Average of scores
        assert stats["total_listings"] == len(scores)

        # Check score ranges
        ranges = stats["score_ranges"]
        assert isinstance(ranges, dict)
        assert ranges["40-59"] == 1  # Score 45
        assert ranges["60-79"] == 2  # Scores 70, 60
        assert ranges["80-100"] == 2  # Scores 85, 95

    def test_get_score_stats_empty_db(self, test_session):
        """Test getting score statistics with no data."""
        stats = ListingCRUD.get_score_stats(test_session)

        assert stats["min_score"] == 0
        assert stats["max_score"] == 0
        assert stats["mean_score"] == 0.0
        assert stats["total_listings"] == 0
        assert stats["score_ranges"] == {}

    def test_get_all_scores(self, test_session, sample_listings):
        """Test getting all scores for plotting."""
        # Add scores to listings
        expected_scores = [85, 70, 95, 45, 60]
        for listing, score in zip(sample_listings, expected_scores):
            listing.score = score
        test_session.commit()

        all_scores = ListingCRUD.get_all_scores(test_session)

        assert len(all_scores) == len(expected_scores)
        assert set(all_scores) == set(expected_scores)

    def test_get_all_scores_with_nulls(self, test_session, sample_listings):
        """Test getting scores when some are null."""
        # Add scores to some listings, leave others null
        scores_to_add = [85, None, 95, None, 60]
        for listing, score in zip(sample_listings, scores_to_add):
            if score is not None:
                listing.score = score
        test_session.commit()

        all_scores = ListingCRUD.get_all_scores(test_session)

        # Should only include non-null scores
        expected_non_null = [85, 95, 60]
        assert len(all_scores) == len(expected_non_null)
        assert set(all_scores) == set(expected_non_null)


@pytest.mark.integration
class TestDataCleanup:
    """Test data cleanup operations."""

    def test_cleanup_old_listings(self, test_session, sample_listings):
        """Test cleaning up old listings."""
        # Make some listings old
        old_date = datetime.utcnow() - timedelta(days=10)

        # Make first 2 listings old
        for listing in sample_listings[:2]:
            listing.fetched_at = old_date
        test_session.commit()

        # Cleanup listings older than 7 days
        deleted_count = ListingCRUD.cleanup_old_listings(test_session, days=7)

        assert deleted_count == 2

        # Verify they're gone
        remaining_listings = ListingCRUD.get_listings(test_session)
        assert len(remaining_listings) == len(sample_listings) - 2

    def test_cleanup_old_listings_none_to_delete(self, test_session, sample_listings):
        """Test cleanup when no listings are old enough."""
        # All listings should be recent (created in fixtures)
        deleted_count = ListingCRUD.cleanup_old_listings(test_session, days=1)

        assert deleted_count == 0

        # All listings should still be there
        remaining_listings = ListingCRUD.get_listings(test_session)
        assert len(remaining_listings) == len(sample_listings)


@pytest.mark.integration
class TestDatabaseConstraints:
    """Test database constraints and error handling."""

    def test_unique_url_constraint(self, test_session, test_utils):
        """Test that URL uniqueness is enforced."""
        url = "https://bilbasen.dk/unique/test"

        # Create first listing
        listing1_data = test_utils.create_test_listing(url=url, title="First")
        listing1 = ListingCRUD.create_listing(test_session, listing1_data)

        assert listing1.id is not None

        # Try to create second listing with same URL
        listing2_data = test_utils.create_test_listing(url=url, title="Second")

        with pytest.raises(Exception):  # Should raise integrity error
            ListingCRUD.create_listing(test_session, listing2_data)

    def test_listing_fields_validation(self, test_session):
        """Test field validation and constraints."""
        # Test with minimal required fields
        minimal_data = ListingCreate(
            title="Minimal Test", url="https://bilbasen.dk/minimal"
        )

        listing = ListingCRUD.create_listing(test_session, minimal_data)

        assert listing.id is not None
        assert listing.title == "Minimal Test"
        assert listing.url == "https://bilbasen.dk/minimal"
        assert listing.price_dkk is None
        assert listing.year is None
        assert listing.fetched_at is not None  # Should be auto-set
