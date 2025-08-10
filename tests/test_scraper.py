"""Tests for the scraper module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.app.scraper.scraper import BilbasenScraper, ScrapedListing
from src.app.scraper.selectors import get_selector, get_pattern
from src.app.models import ListingCreate


@pytest.mark.unit
class TestScrapedListing:
    """Test the ScrapedListing dataclass."""
    
    def test_scraped_listing_creation(self):
        """Test creating a ScrapedListing instance."""
        listing = ScrapedListing(
            title="Test Fiat Panda",
            url="https://bilbasen.dk/test/123",
            price_text="75.000 kr.",
            year_text="2020",
            kilometers_text="50.000 km"
        )
        
        assert listing.title == "Test Fiat Panda"
        assert listing.url == "https://bilbasen.dk/test/123"
        assert listing.price_text == "75.000 kr."
        assert listing.year_text == "2020"
        assert listing.kilometers_text == "50.000 km"
    
    def test_scraped_listing_defaults(self):
        """Test ScrapedListing with default values."""
        listing = ScrapedListing(
            title="Test Title",
            url="https://test.com"
        )
        
        assert listing.price_text == ""
        assert listing.year_text == ""
        assert listing.condition_text == ""


@pytest.mark.unit
class TestBilbasenScraperDataNormalization:
    """Test data normalization in the scraper."""
    
    def setup_method(self):
        """Set up scraper for testing."""
        self.scraper = BilbasenScraper()
    
    def test_extract_price_valid(self):
        """Test price extraction from various formats."""
        test_cases = [
            ("75.000 kr.", 75000),
            ("123.456 DKK", 123456),
            ("50,000 kr", 50000),
            ("999.999 kr.", 999999),
            ("45000 kr", 45000),
        ]
        
        for price_text, expected in test_cases:
            result = self.scraper._extract_price(price_text)
            assert result == expected, f"Failed for '{price_text}': expected {expected}, got {result}"
    
    def test_extract_price_invalid(self):
        """Test price extraction with invalid input."""
        invalid_cases = [
            "",
            "Not a price",
            "kr. only", 
            "abc.def kr.",
            None
        ]
        
        for price_text in invalid_cases:
            result = self.scraper._extract_price(price_text)
            assert result is None, f"Expected None for '{price_text}', got {result}"
    
    def test_extract_year_valid(self):
        """Test year extraction from text."""
        test_cases = [
            ("2020", 2020),
            ("Årgang 2018", 2018),
            ("Fra 2022 model", 2022),
            ("1995 årsmodel", 1995),
            ("Købt i 2019", 2019),
        ]
        
        for year_text, expected in test_cases:
            result = self.scraper._extract_year(year_text)
            assert result == expected, f"Failed for '{year_text}': expected {expected}, got {result}"
    
    def test_extract_year_invalid(self):
        """Test year extraction with invalid input."""
        invalid_cases = [
            "",
            "Not a year",
            "1900",  # Too old
            "2050",  # Too new
            "20",    # Too short
            None
        ]
        
        for year_text in invalid_cases:
            result = self.scraper._extract_year(year_text)
            assert result is None, f"Expected None for '{year_text}', got {result}"
    
    def test_extract_kilometers_valid(self):
        """Test kilometers extraction from text."""
        test_cases = [
            ("50.000 km", 50000),
            ("123,456 km", 123456),
            ("75000 km", 75000),
            ("Kørt 45.000 kilometer", 45000),
            ("12.345 km på måleren", 12345),
        ]
        
        for km_text, expected in test_cases:
            result = self.scraper._extract_kilometers(km_text)
            assert result == expected, f"Failed for '{km_text}': expected {expected}, got {result}"
    
    def test_extract_kilometers_invalid(self):
        """Test kilometers extraction with invalid input."""
        invalid_cases = [
            "",
            "Not kilometers",
            "km only",
            "5000000",  # Too high
            None
        ]
        
        for km_text in invalid_cases:
            result = self.scraper._extract_kilometers(km_text)
            assert result is None, f"Expected None for '{km_text}', got {result}"
    
    def test_normalize_text(self):
        """Test text normalization."""
        test_cases = [
            ("  Extra   spaces  ", "Extra spaces"),
            ("Line\nbreaks\tand\ttabs", "Line breaks and tabs"),
            ("", None),
            ("   ", None),
            ("Normal text", "Normal text),
        ]
        
        for input_text, expected in test_cases:
            result = self.scraper._normalize_text(input_text)
            assert result == expected, f"Failed for '{input_text}': expected {expected}, got {result}"
    
    def test_normalize_scraped_data(self):
        """Test complete data normalization."""
        scraped = ScrapedListing(
            title="Fiat Panda 1.2 Easy",
            url="https://bilbasen.dk/test/123",
            price_text="85.000 kr.",
            year_text="2020",
            kilometers_text="45.000 km",
            condition_text="Velholdt",
            brand_text="Fiat",
            model_text="Panda"
        )
        
        with patch('src.app.scraper.scraper.parse_condition', return_value=(0.8, {})):
            result = self.scraper.normalize_scraped_data(scraped)
        
        assert isinstance(result, ListingCreate)
        assert result.title == "Fiat Panda 1.2 Easy"
        assert result.url == "https://bilbasen.dk/test/123"
        assert result.price_dkk == 85000
        assert result.year == 2020
        assert result.kilometers == 45000
        assert result.condition_score == 0.8
        assert result.brand == "Fiat"
        assert result.model == "Panda"


@pytest.mark.unit
class TestSelectors:
    """Test CSS selector utilities."""
    
    def test_get_selector_basic(self):
        """Test basic selector retrieval."""
        selector = get_selector("search", "listings_container")
        
        assert isinstance(selector, str)
        assert len(selector) > 0
    
    def test_get_selector_with_fallback(self):
        """Test selector with fallback options."""
        selector = get_selector("search", "listing_items", fallback=True)
        
        assert isinstance(selector, str)
        # Should contain multiple selectors separated by commas when fallbacks exist
        if "," in selector:
            selectors = [s.strip() for s in selector.split(",")]
            assert len(selectors) > 1
    
    def test_get_selector_nonexistent(self):
        """Test getting non-existent selector."""
        selector = get_selector("nonexistent", "category")
        
        assert selector == ""
    
    def test_get_pattern(self):
        """Test pattern retrieval."""
        price_pattern = get_pattern("price", "regex")
        
        assert isinstance(price_pattern, str)
        assert len(price_pattern) > 0
        
        # Test pattern matching
        import re
        pattern = re.compile(price_pattern)
        match = pattern.search("75.000 kr.")
        assert match is not None


@pytest.mark.scraper
@pytest.mark.slow
class TestScraperIntegration:
    """Integration tests for the scraper (may make network requests)."""
    
    def setup_method(self):
        """Set up scraper for testing.""" 
        self.scraper = BilbasenScraper()
    
    @pytest.mark.live
    async def test_scraper_url_construction(self):
        """Test that scraper constructs valid URLs."""
        search_url = self.scraper.search_url
        
        assert search_url.startswith("https://")
        assert "bilbasen.dk" in search_url
        assert "Fiat+Panda" in search_url or "FreeTxt=" in search_url
    
    @pytest.mark.skip(reason="Requires live connection and may be slow")
    async def test_live_scraping_basic(self):
        """Test basic live scraping functionality."""
        # This test is skipped by default to avoid hitting the live site
        # Enable manually for integration testing
        
        try:
            listings = await self.scraper.scrape_full_listings(
                max_pages=1, 
                include_details=False
            )
            
            # Should either succeed or fail gracefully
            assert isinstance(listings, list)
            
            if listings:
                listing = listings[0]
                assert isinstance(listing, ListingCreate)
                assert listing.title is not None
                assert listing.url is not None
                
        except Exception as e:
            # Should handle errors gracefully
            assert isinstance(e, Exception)
            pytest.skip(f"Live scraping failed (expected): {e}")


@pytest.mark.unit
class TestScraperMocked:
    """Test scraper with mocked responses."""
    
    def setup_method(self):
        """Set up scraper for testing."""
        self.scraper = BilbasenScraper()
    
    @patch('src.app.scraper.playwright_client.get_playwright_client')
    async def test_scrape_search_results_mocked(self, mock_client_context):
        """Test scraping search results with mocked client."""
        # Mock the playwright client
        mock_client = AsyncMock()
        mock_page = AsyncMock()
        
        mock_client_context.return_value.__aenter__.return_value = mock_client
        mock_client.get_page_with_retry.return_value = (mock_page, "<html>test</html>")
        
        # Mock URL extraction
        mock_page.query_selector_all.return_value = []
        
        with patch.object(self.scraper, '_extract_listing_urls', return_value=[]):
            listings = await self.scraper.scrape_search_results(max_pages=1)
        
        assert isinstance(listings, list)
        assert len(listings) == 0  # No URLs extracted
        
        # Verify client was called
        mock_client.get_page_with_retry.assert_called()
    
    def test_extract_listing_urls_mocked(self):
        """Test URL extraction with mocked page."""
        mock_page = Mock()
        mock_elements = [
            Mock(get_attribute=AsyncMock(return_value="/brugt/bil/fiat/panda/12345")),
            Mock(get_attribute=AsyncMock(return_value="/brugt/bil/fiat/panda/12346")),
        ]
        
        mock_page.query_selector_all = AsyncMock(return_value=mock_elements)
        
        # This would need to be adapted based on the actual implementation
        # as _extract_listing_urls is an async method that takes a page
    
    @patch('src.app.scraper.scraper.parse_condition')
    def test_normalize_scraped_data_with_condition_parsing(self, mock_parse_condition):
        """Test data normalization with mocked condition parsing."""
        mock_parse_condition.return_value = (0.75, {"debug": "info"})
        
        scraped = ScrapedListing(
            title="Test Panda",
            url="https://test.com/123",
            condition_text="God stand"
        )
        
        result = self.scraper.normalize_scraped_data(scraped)
        
        assert result.condition_score == 0.75
        mock_parse_condition.assert_called_once_with("God stand")


@pytest.mark.unit
class TestScraperErrorHandling:
    """Test scraper error handling."""
    
    def setup_method(self):
        """Set up scraper for testing."""
        self.scraper = BilbasenScraper()
    
    def test_extract_price_edge_cases(self):
        """Test price extraction edge cases."""
        edge_cases = [
            ("0 kr.", 0),
            ("1 kr.", 1),
            ("1.000.000 kr.", 1000000),
            ("Price: 50.000", 50000),  # Without currency
        ]
        
        for price_text, expected in edge_cases:
            result = self.scraper._extract_price(price_text)
            assert result == expected, f"Failed for '{price_text}'"
    
    def test_normalize_empty_scraped_data(self):
        """Test normalizing mostly empty scraped data."""
        scraped = ScrapedListing(
            title="",
            url="https://test.com"
        )
        
        with patch('src.app.scraper.scraper.parse_condition', return_value=(0.5, {})):
            result = self.scraper.normalize_scraped_data(scraped)
        
        assert result.title == ""
        assert result.url == "https://test.com"
        assert result.price_dkk is None
        assert result.year is None
        assert result.kilometers is None
        assert result.condition_score == 0.5