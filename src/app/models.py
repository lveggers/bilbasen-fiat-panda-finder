"""Database models for the Bilbasen Fiat Panda Finder."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Listing(SQLModel, table=True):
    """Car listing model."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500, description="Listing title")
    url: str = Field(max_length=1000, unique=True, description="Listing URL")
    price_dkk: Optional[int] = Field(default=None, description="Price in Danish Kroner")
    year: Optional[int] = Field(default=None, description="Car year")
    kilometers: Optional[int] = Field(default=None, description="Kilometers driven")
    condition_str: Optional[str] = Field(default=None, max_length=100, description="Condition as text")
    condition_score: Optional[float] = Field(default=None, description="Condition score (0-1)")
    score: Optional[int] = Field(default=None, description="Overall score (0-100)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When the listing was fetched")
    
    # Additional fields that might be useful
    brand: Optional[str] = Field(default=None, max_length=50, description="Car brand")
    model: Optional[str] = Field(default=None, max_length=50, description="Car model")
    fuel_type: Optional[str] = Field(default=None, max_length=50, description="Fuel type")
    transmission: Optional[str] = Field(default=None, max_length=50, description="Transmission type")
    body_type: Optional[str] = Field(default=None, max_length=50, description="Body type")
    location: Optional[str] = Field(default=None, max_length=100, description="Listing location")
    dealer_name: Optional[str] = Field(default=None, max_length=200, description="Dealer name")
    
    # Scoring intermediate values (for debugging)
    price_score: Optional[float] = Field(default=None, description="Normalized price score (0-1)")
    year_score: Optional[float] = Field(default=None, description="Normalized year score (0-1)")
    kilometers_score: Optional[float] = Field(default=None, description="Normalized kilometers score (0-1)")
    
    class Config:
        """Model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def __repr__(self) -> str:
        """String representation of the listing."""
        return f"<Listing(id={self.id}, title='{self.title[:50]}...', price={self.price_dkk}, score={self.score})>"


class ListingCreate(SQLModel):
    """Schema for creating a new listing."""
    
    title: str
    url: str
    price_dkk: Optional[int] = None
    year: Optional[int] = None
    kilometers: Optional[int] = None
    condition_str: Optional[str] = None
    condition_score: Optional[float] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    location: Optional[str] = None
    dealer_name: Optional[str] = None


class ListingUpdate(SQLModel):
    """Schema for updating a listing."""
    
    title: Optional[str] = None
    price_dkk: Optional[int] = None
    year: Optional[int] = None
    kilometers: Optional[int] = None
    condition_str: Optional[str] = None
    condition_score: Optional[float] = None
    score: Optional[int] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    location: Optional[str] = None
    dealer_name: Optional[str] = None
    price_score: Optional[float] = None
    year_score: Optional[float] = None
    kilometers_score: Optional[float] = None


class ListingRead(SQLModel):
    """Schema for reading a listing."""
    
    id: int
    title: str
    url: str
    price_dkk: Optional[int]
    year: Optional[int]
    kilometers: Optional[int]
    condition_str: Optional[str]
    condition_score: Optional[float]
    score: Optional[int]
    fetched_at: datetime
    brand: Optional[str]
    model: Optional[str]
    fuel_type: Optional[str]
    transmission: Optional[str]
    body_type: Optional[str]
    location: Optional[str]
    dealer_name: Optional[str]
    price_score: Optional[float]
    year_score: Optional[float]
    kilometers_score: Optional[float]


class ScoreDistribution(SQLModel):
    """Schema for score distribution statistics."""
    
    min_score: int
    max_score: int
    mean_score: float
    median_score: float
    std_score: float
    score_ranges: dict  # e.g., {"0-20": 5, "21-40": 10, ...}
    total_listings: int