"""Pytest configuration and fixtures for the Bilbasen Fiat Panda Finder tests."""

import pytest
import tempfile
import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
import pandas as pd
from typing import Generator, Dict, Any

from src.app.config import settings
from src.app.db import get_session
from src.app.server import app
from src.app.models import Listing, ListingCreate
from src.app.logging_conf import setup_logging


@pytest.fixture(scope="session")
def setup_test_logging():
    """Setup logging for tests."""
    setup_logging()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    # Create engine with temporary database
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Clean up
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def test_session(temp_db) -> Generator[Session, None, None]:
    """Create a test database session."""
    with Session(temp_db) as session:
        yield session


@pytest.fixture
def test_client(test_session) -> TestClient:
    """Create a test client with dependency override."""
    
    def get_test_session():
        return test_session
    
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_listings_data() -> list[Dict[str, Any]]:
    """Sample listing data for testing."""
    return [
        {
            "title": "Fiat Panda 1.2 69 Easy",
            "url": "https://bilbasen.dk/brugt/bil/fiat/panda/12345",
            "price_dkk": 85000,
            "year": 2020,
            "kilometers": 45000,
            "condition_str": "Velholdt",
            "condition_score": 0.8,
            "brand": "Fiat",
            "model": "Panda",
            "fuel_type": "Benzin",
            "transmission": "Manuel",
            "location": "København",
            "dealer_name": "Auto Hansen"
        },
        {
            "title": "Fiat Panda 1.0 70 Easy",
            "url": "https://bilbasen.dk/brugt/bil/fiat/panda/12346",
            "price_dkk": 65000,
            "year": 2018,
            "kilometers": 78000,
            "condition_str": "God stand",
            "condition_score": 0.7,
            "brand": "Fiat",
            "model": "Panda",
            "fuel_type": "Benzin",
            "transmission": "Manuel",
            "location": "Aarhus",
            "dealer_name": "Bil Center"
        },
        {
            "title": "Fiat Panda 1.2 69 Lounge",
            "url": "https://bilbasen.dk/brugt/bil/fiat/panda/12347",
            "price_dkk": 120000,
            "year": 2022,
            "kilometers": 15000,
            "condition_str": "Nysynet",
            "condition_score": 1.0,
            "brand": "Fiat",
            "model": "Panda",
            "fuel_type": "Benzin",
            "transmission": "Automatik",
            "location": "Odense",
            "dealer_name": "Premium Auto"
        },
        {
            "title": "Fiat Panda 0.9 TwinAir",
            "url": "https://bilbasen.dk/brugt/bil/fiat/panda/12348",
            "price_dkk": 45000,
            "year": 2015,
            "kilometers": 125000,
            "condition_str": "Brugt",
            "condition_score": 0.5,
            "brand": "Fiat",
            "model": "Panda",
            "fuel_type": "Benzin",
            "transmission": "Manuel",
            "location": "Aalborg",
            "dealer_name": "Budget Biler"
        },
        {
            "title": "Fiat Panda 1.3 MultiJet",
            "url": "https://bilbasen.dk/brugt/bil/fiat/panda/12349",
            "price_dkk": 55000,
            "year": 2016,
            "kilometers": 98000,
            "condition_str": "Pæn",
            "condition_score": 0.75,
            "brand": "Fiat",
            "model": "Panda",
            "fuel_type": "Diesel",
            "transmission": "Manuel",
            "location": "Esbjerg",
            "dealer_name": "Diesel Specialisten"
        }
    ]


@pytest.fixture
def sample_listings(test_session, sample_listings_data) -> list[Listing]:
    """Create sample listings in the test database."""
    listings = []
    
    for data in sample_listings_data:
        listing_create = ListingCreate(**data)
        listing = Listing.model_validate(listing_create)
        test_session.add(listing)
        listings.append(listing)
    
    test_session.commit()
    
    # Refresh to get IDs
    for listing in listings:
        test_session.refresh(listing)
    
    return listings


@pytest.fixture
def sample_dataframe(sample_listings_data) -> pd.DataFrame:
    """Create a sample DataFrame for scoring tests."""
    return pd.DataFrame(sample_listings_data)


@pytest.fixture
def mock_scraper_response():
    """Mock response data for scraper tests."""
    return {
        "search_results_html": """
        <div data-testid="search-results">
            <div class="bb-listing-clickable">
                <a href="/brugt/bil/fiat/panda/12345">
                    <h3>Fiat Panda 1.2 Easy</h3>
                    <div class="bb-listing-price">85.000 kr.</div>
                    <div class="bb-listing-year">2020</div>
                    <div class="bb-listing-km">45.000 km</div>
                    <div class="bb-listing-location">København</div>
                </a>
            </div>
            <div class="bb-listing-clickable">
                <a href="/brugt/bil/fiat/panda/12346">
                    <h3>Fiat Panda 1.0 Easy</h3>
                    <div class="bb-listing-price">65.000 kr.</div>
                    <div class="bb-listing-year">2018</div>
                    <div class="bb-listing-km">78.000 km</div>
                    <div class="bb-listing-location">Aarhus</div>
                </a>
            </div>
        </div>
        """,
        "detail_page_html": """
        <h1>Fiat Panda 1.2 69 Easy</h1>
        <div class="price">85.000 kr.</div>
        <div class="year">2020</div>
        <div class="kilometers">45.000 km</div>
        <div class="condition">Velholdt</div>
        <div class="brand">Fiat</div>
        <div class="model">Panda</div>
        <div class="fuel-type">Benzin</div>
        <div class="transmission">Manuel</div>
        <div class="dealer-name">Auto Hansen</div>
        <div class="location">København</div>
        """
    }


@pytest.fixture
def danish_condition_samples() -> Dict[str, float]:
    """Sample Danish condition texts with expected scores."""
    return {
        "Nysynet": 1.0,
        "Topstand": 0.95,
        "Velholdt": 0.8,
        "God stand": 0.75,
        "Pæn": 0.8,
        "Brugt": 0.55,
        "Normal": 0.5,
        "Slidte": 0.35,
        "Reparationsobjekt": 0.1,
        "Defekt": 0.0,
        "": 0.5,  # Empty string should default to 0.5
        None: 0.5,  # None should default to 0.5
    }


# Skip markers for different test categories
pytest_plugins = []

# Custom markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may use database)"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests (testing HTTP endpoints)"
    )
    config.addinivalue_line(
        "markers", "scraper: marks tests as scraper tests (may make HTTP requests)"
    )
    config.addinivalue_line(
        "markers", "live: marks tests that require live internet connection"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (taking > 1s)"
    )


# Test utilities
class TestUtils:
    """Utility functions for tests."""
    
    @staticmethod
    def assert_listing_equal(listing1: Listing, listing2: Listing, ignore_fields=None):
        """Assert two listings are equal, ignoring specified fields."""
        ignore_fields = ignore_fields or ['id', 'fetched_at']
        
        for field in listing1.model_fields:
            if field not in ignore_fields:
                assert getattr(listing1, field) == getattr(listing2, field), f"Field {field} mismatch"
    
    @staticmethod
    def create_test_listing(**kwargs) -> ListingCreate:
        """Create a test listing with default values."""
        defaults = {
            "title": "Test Fiat Panda",
            "url": "https://bilbasen.dk/test/12345",
            "price_dkk": 75000,
            "year": 2019,
            "kilometers": 60000,
            "condition_str": "God stand",
            "condition_score": 0.7,
            "brand": "Fiat",
            "model": "Panda"
        }
        defaults.update(kwargs)
        return ListingCreate(**defaults)


@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtils