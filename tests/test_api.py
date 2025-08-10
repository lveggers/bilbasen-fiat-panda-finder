"""Tests for FastAPI endpoints."""

import pytest


@pytest.mark.api
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check endpoint returns correct status."""
        response = test_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Bilbasen Web Server"
        assert "version" in data

    def test_api_health_check(self, test_client):
        """Test API health check endpoint."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Bilbasen Fiat Panda Finder"
        assert "version" in data


@pytest.mark.api
class TestListingsEndpoints:
    """Test listing-related endpoints."""

    def test_get_listings_empty(self, test_client):
        """Test getting listings when database is empty."""
        response = test_client.get("/api/v1/listings")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_listings_with_data(self, test_client, sample_listings):
        """Test getting listings with sample data."""
        response = test_client.get("/api/v1/listings")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(sample_listings)

        # Check first listing structure
        if data:
            listing = data[0]
            required_fields = ["id", "title", "url", "fetched_at"]
            for field in required_fields:
                assert field in listing

    def test_get_listings_pagination(self, test_client, sample_listings):
        """Test listings pagination."""
        # Test first page
        response = test_client.get("/api/v1/listings?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test second page
        response = test_client.get("/api/v1/listings?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_get_listings_price_filter(self, test_client, sample_listings):
        """Test listings with price filters."""
        # Filter for expensive listings
        response = test_client.get("/api/v1/listings?min_price=80000")

        assert response.status_code == 200
        data = response.json()

        for listing in data:
            if listing["price_dkk"]:
                assert listing["price_dkk"] >= 80000

        # Filter for cheap listings
        response = test_client.get("/api/v1/listings?max_price=60000")

        assert response.status_code == 200
        data = response.json()

        for listing in data:
            if listing["price_dkk"]:
                assert listing["price_dkk"] <= 60000

    def test_get_listings_year_filter(self, test_client, sample_listings):
        """Test listings with year filters."""
        response = test_client.get("/api/v1/listings?min_year=2020")

        assert response.status_code == 200
        data = response.json()

        for listing in data:
            if listing["year"]:
                assert listing["year"] >= 2020

    def test_get_listings_invalid_params(self, test_client):
        """Test listings endpoint with invalid parameters."""
        # Test invalid limit
        response = test_client.get("/api/v1/listings?limit=2000")  # Over max

        assert response.status_code == 422  # Validation error

        # Test negative skip
        response = test_client.get("/api/v1/listings?skip=-1")

        assert response.status_code == 422

    def test_get_listing_by_id(self, test_client, sample_listings):
        """Test getting a specific listing by ID."""
        listing_id = sample_listings[0].id

        response = test_client.get(f"/api/v1/listings/{listing_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == listing_id
        assert "title" in data
        assert "url" in data

    def test_get_listing_by_id_not_found(self, test_client):
        """Test getting a non-existent listing."""
        response = test_client.get("/api/v1/listings/99999")

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_top_listings_empty(self, test_client):
        """Test top listings when database is empty."""
        response = test_client.get("/api/v1/top10")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_top_listings_with_scores(
        self, test_client, sample_listings, test_session
    ):
        """Test top listings with scored data."""
        # Add scores to sample listings
        scores = [85, 70, 95, 45, 60]
        for listing, score in zip(sample_listings, scores):
            listing.score = score
        test_session.commit()

        response = test_client.get("/api/v1/top10")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Should be ordered by score descending
        if len(data) > 1:
            scores = [listing["score"] for listing in data if listing["score"]]
            assert scores == sorted(scores, reverse=True)

    def test_get_top_listings_custom_limit(
        self, test_client, sample_listings, test_session
    ):
        """Test top listings with custom limit."""
        # Add scores
        for i, listing in enumerate(sample_listings):
            listing.score = 100 - (i * 10)
        test_session.commit()

        response = test_client.get("/api/v1/top10?limit=3")

        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3


@pytest.mark.api
class TestScoreEndpoints:
    """Test score-related endpoints."""

    def test_get_scores_empty(self, test_client):
        """Test score statistics with empty database."""
        response = test_client.get("/api/v1/scores")

        assert response.status_code == 200

        data = response.json()
        assert data["total_listings"] == 0
        assert data["min_score"] == 0
        assert data["max_score"] == 0

    def test_get_scores_with_data(self, test_client, sample_listings, test_session):
        """Test score statistics with sample data."""
        # Add scores to sample listings
        scores = [85, 70, 95, 45, 60]
        for listing, score in zip(sample_listings, scores):
            listing.score = score
        test_session.commit()

        response = test_client.get("/api/v1/scores")

        assert response.status_code == 200

        data = response.json()
        assert data["total_listings"] == len(scores)
        assert data["min_score"] == min(scores)
        assert data["max_score"] == max(scores)
        assert data["mean_score"] == sum(scores) / len(scores)

        assert "score_ranges" in data
        assert isinstance(data["score_ranges"], dict)

    def test_get_score_distribution(self, test_client, sample_listings, test_session):
        """Test score distribution endpoint."""
        # Add scores
        scores = [85, 70, 95, 45, 60]
        for listing, score in zip(sample_listings, scores):
            listing.score = score
        test_session.commit()

        response = test_client.get("/api/v1/scores/distribution")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(scores)
        assert set(data) == set(scores)

    def test_get_score_breakdown(self, test_client, sample_listings, test_session):
        """Test detailed score breakdown."""
        # Add scores
        for i, listing in enumerate(sample_listings):
            listing.score = 80 - (i * 10)
        test_session.commit()

        response = test_client.get("/api/v1/scores/breakdown")

        assert response.status_code == 200

        data = response.json()
        assert "total_listings" in data
        assert "statistics" in data
        assert "score_ranges" in data
        assert "top_10" in data

        assert data["total_listings"] > 0
        assert isinstance(data["top_10"], list)


@pytest.mark.api
class TestUtilityEndpoints:
    """Test utility endpoints."""

    def test_get_stats(self, test_client, sample_listings):
        """Test database statistics endpoint."""
        response = test_client.get("/api/v1/stats")

        assert response.status_code == 200

        data = response.json()
        assert "total_listings" in data
        assert "score_statistics" in data
        assert "search_term" in data
        assert "scoring_weights" in data

        assert data["total_listings"] == len(sample_listings)
        assert isinstance(data["scoring_weights"], dict)

    def test_rescore_listings(self, test_client, sample_listings):
        """Test rescoring endpoint."""
        response = test_client.post("/api/v1/rescore")

        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "updated_count" in data
        assert isinstance(data["updated_count"], int)

    @pytest.mark.slow
    def test_scrape_sync_endpoint(self, test_client):
        """Test synchronous scraping endpoint."""
        # This is a slow test as it may actually attempt scraping
        response = test_client.post(
            "/api/v1/scrape/sync?max_pages=1&include_details=false"
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "scraped_count" in data
            assert "stored_count" in data


@pytest.mark.api
class TestWebUIEndpoints:
    """Test web UI endpoints."""

    def test_dashboard_page(self, test_client):
        """Test main dashboard page."""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check for key elements in HTML
        content = response.text
        assert "Bilbasen Fiat Panda Finder" in content
        assert "dashboard" in content.lower() or "Dashboard" in content

    def test_listings_page(self, test_client):
        """Test listings page."""
        response = test_client.get("/listings")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        assert "listings" in content.lower() or "Listings" in content

    def test_about_page(self, test_client):
        """Test about page."""
        response = test_client.get("/about")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        assert "about" in content.lower() or "About" in content
        assert "scoring" in content.lower()

    def test_dashboard_api_data(self, test_client, sample_listings, test_session):
        """Test dashboard API data endpoint."""
        # Add scores to listings
        for i, listing in enumerate(sample_listings):
            listing.score = 90 - (i * 10)
        test_session.commit()

        response = test_client.get("/api/dashboard-data")

        assert response.status_code == 200

        data = response.json()
        assert "top_listings" in data
        assert "score_stats" in data
        assert "all_scores" in data
        assert "total_listings" in data

        assert isinstance(data["top_listings"], list)
        assert isinstance(data["all_scores"], list)
        assert data["total_listings"] > 0

    def test_404_page(self, test_client):
        """Test custom 404 page."""
        response = test_client.get("/nonexistent-page")

        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]


@pytest.mark.api
class TestErrorHandling:
    """Test API error handling."""

    def test_invalid_json_request(self, test_client):
        """Test handling of invalid JSON in request body."""
        response = test_client.post(
            "/api/v1/scrape/sync",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_required_fields(self, test_client):
        """Test handling of missing required fields."""
        # Test with missing or invalid query parameters
        response = test_client.get("/api/v1/listings?limit=invalid")

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_database_error_handling(self, test_client, test_session):
        """Test handling of database errors."""
        # Close the session to simulate database error
        test_session.close()

        response = test_client.get("/api/v1/listings")

        # Should handle gracefully, may return 500 or work if connection pool handles it
        assert response.status_code in [200, 500]

    def test_large_pagination_request(self, test_client):
        """Test handling of very large pagination requests."""
        response = test_client.get("/api/v1/listings?skip=1000000&limit=1000")

        # Should handle gracefully - limit is capped at 1000 in validation
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


@pytest.mark.api
class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema is available."""
        response = test_client.get("/openapi.json")

        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Check some expected paths are documented
        paths = schema["paths"]
        assert "/api/v1/listings" in paths
        assert "/api/v1/health" in paths
        assert "/api/v1/top10" in paths

    def test_docs_page(self, test_client):
        """Test Swagger UI docs page."""
        response = test_client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        assert "swagger" in content.lower() or "openapi" in content.lower()

    def test_redoc_page(self, test_client):
        """Test ReDoc documentation page."""
        response = test_client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        assert "redoc" in content.lower()


@pytest.mark.api
@pytest.mark.slow
class TestScrapingEndpoints:
    """Test scraping endpoints (may be slow)."""

    def test_background_scraping_trigger(self, test_client):
        """Test triggering background scraping."""
        response = test_client.post(
            "/api/v1/scrape", json={"max_pages": 1, "include_details": False}
        )

        # Should successfully start background task
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_scraping_with_invalid_params(self, test_client):
        """Test scraping with invalid parameters."""
        response = test_client.post(
            "/api/v1/scrape",
            json={"max_pages": 50, "include_details": True},  # Too many pages
        )

        assert response.status_code == 422  # Validation error
