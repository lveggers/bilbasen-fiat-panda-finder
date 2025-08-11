"""Configuration module for the Bilbasen Fiat Panda Finder."""

from typing import Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Search configuration
    search_term: str = Field(
        default="Fiat Panda", description="Car model to search for"
    )
    base_url: str = Field(
        default="https://www.bilbasen.dk", description="Base URL for Bilbasen"
    )
    search_url: str = Field(
        default="https://www.bilbasen.dk/brugt/bil/fiat/panda?includeengroscvr=true&includeleasing=false",
        description="Search URL for Fiat Panda listings",
    )

    # Scraper configuration
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Bilbasen-Fiat-Panda-Finder/1.0",
        description="User agent for web requests",
    )
    headless_browser: bool = Field(
        default=True, description="Run browser in headless mode"
    )

    # Rate limiting
    request_delay_min: float = Field(
        default=1.0, description="Minimum delay between requests (seconds)"
    )
    request_delay_max: float = Field(
        default=3.0, description="Maximum delay between requests (seconds)"
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts for failed requests"
    )
    retry_delay_base: float = Field(
        default=2.0, description="Base delay for exponential backoff"
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./listings.db", description="Database connection URL"
    )

    # Scoring weights (must sum to 1.0)
    score_weight_price: float = Field(
        default=0.4, description="Weight for price in scoring"
    )
    score_weight_year: float = Field(
        default=0.25, description="Weight for year in scoring"
    )
    score_weight_kilometers: float = Field(
        default=0.25, description="Weight for kilometers in scoring"
    )
    score_weight_condition: float = Field(
        default=0.1, description="Weight for condition in scoring"
    )

    # Winsorization percentiles for outlier handling
    winsorize_lower_percentile: float = Field(
        default=0.05, description="Lower percentile for winsorization"
    )
    winsorize_upper_percentile: float = Field(
        default=0.95, description="Upper percentile for winsorization"
    )

    # Server configuration
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")
    server_reload: bool = Field(default=False, description="Enable server auto-reload")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format (json or text)")

    # Test environment
    testing: bool = Field(
        default=False, description="Skip startup scraping during tests"
    )

    def get_search_url(self) -> str:
        """Get the search URL for Fiat Panda listings."""
        return self.search_url

    def get_scoring_weights(self) -> Dict[str, float]:
        """Get scoring weights as a dictionary."""
        return {
            "price": self.score_weight_price,
            "year": self.score_weight_year,
            "kilometers": self.score_weight_kilometers,
            "condition": self.score_weight_condition,
        }

    def validate_scoring_weights(self) -> None:
        """Validate that scoring weights sum to approximately 1.0."""
        total_weight = sum(self.get_scoring_weights().values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")

    def model_post_init(self, __context: Any) -> None:
        """Validate settings after initialization."""
        self.validate_scoring_weights()


# Global settings instance
settings = Settings()
