"""Scoring algorithm for car listings with winsorization and normalization."""

import pandas as pd
from typing import Dict, Optional
from scipy.stats import mstats

from .config import settings
from .logging_conf import get_logger

logger = get_logger("scoring")


class ListingScorer:
    """Score car listings based on price, year, kilometers, and condition."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize the scorer with custom or default weights.

        Args:
            weights: Dictionary with keys 'price', 'year', 'kilometers', 'condition'
        """
        self.weights = weights or settings.get_scoring_weights()
        self.lower_percentile = settings.winsorize_lower_percentile
        self.upper_percentile = settings.winsorize_upper_percentile

        # Validate weights
        total_weight = sum(self.weights.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        logger.info(f"Initialized scorer with weights: {self.weights}")

    def score_listings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score all listings in the dataframe.

        Args:
            df: DataFrame with columns 'price_dkk', 'year', 'kilometers', 'condition_score'

        Returns:
            DataFrame with added scoring columns and final 'score'
        """
        if df.empty:
            logger.warning("Empty dataframe provided for scoring")
            return df

        logger.info(f"Scoring {len(df)} listings")

        # Work on a copy to avoid modifying original
        scored_df = df.copy()

        # Score each component
        scored_df = self._score_price(scored_df)
        scored_df = self._score_year(scored_df)
        scored_df = self._score_kilometers(scored_df)
        scored_df = self._score_condition(scored_df)

        # Calculate final weighted score
        scored_df = self._calculate_final_score(scored_df)

        logger.info(
            f"Scoring completed. Score range: {scored_df['score'].min():.1f} - {scored_df['score'].max():.1f}"
        )

        return scored_df

    def _score_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score price component (lower is better, so invert)."""
        if "price_dkk" not in df.columns:
            logger.warning("No price_dkk column found, setting price_score to 0.5")
            df["price_score"] = 0.5
            return df

        # Filter out null prices
        price_mask = df["price_dkk"].notna()
        if not price_mask.any():
            logger.warning("No valid prices found, setting all price_score to 0.5")
            df["price_score"] = 0.5
            return df

        prices = df.loc[price_mask, "price_dkk"].astype(float)

        # Winsorize to handle outliers
        winsorized_prices = mstats.winsorize(
            prices, limits=(self.lower_percentile, 1 - self.upper_percentile)
        )

        # Min-max normalize to [0, 1]
        min_price = winsorized_prices.min()
        max_price = winsorized_prices.max()

        if min_price == max_price:
            # All prices are the same after winsorization
            normalized_prices = pd.Series(0.5, index=prices.index)
        else:
            normalized_prices = (winsorized_prices - min_price) / (
                max_price - min_price
            )
            # Invert because lower price is better
            normalized_prices = 1.0 - normalized_prices

        # Assign scores
        df["price_score"] = 0.5  # Default for missing prices
        df.loc[price_mask, "price_score"] = normalized_prices

        logger.debug(
            f"Price scoring: {len(prices)} valid prices, range {min_price:.0f}-{max_price:.0f} DKK"
        )

        return df

    def _score_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score year component (newer is better)."""
        if "year" not in df.columns:
            logger.warning("No year column found, setting year_score to 0.5")
            df["year_score"] = 0.5
            return df

        # Filter out null years
        year_mask = df["year"].notna()
        if not year_mask.any():
            logger.warning("No valid years found, setting all year_score to 0.5")
            df["year_score"] = 0.5
            return df

        years = df.loc[year_mask, "year"].astype(int)

        # Winsorize to handle outliers
        winsorized_years = mstats.winsorize(
            years, limits=(self.lower_percentile, 1 - self.upper_percentile)
        )

        # Min-max normalize to [0, 1]
        min_year = winsorized_years.min()
        max_year = winsorized_years.max()

        if min_year == max_year:
            # All years are the same after winsorization
            normalized_years = pd.Series(0.5, index=years.index)
        else:
            normalized_years = (winsorized_years - min_year) / (max_year - min_year)
            # Don't invert because newer (higher) year is better

        # Assign scores
        df["year_score"] = 0.5  # Default for missing years
        df.loc[year_mask, "year_score"] = normalized_years

        logger.debug(
            f"Year scoring: {len(years)} valid years, range {min_year}-{max_year}"
        )

        return df

    def _score_kilometers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score kilometers component (fewer km is better, so invert)."""
        if "kilometers" not in df.columns:
            logger.warning(
                "No kilometers column found, setting kilometers_score to 0.5"
            )
            df["kilometers_score"] = 0.5
            return df

        # Filter out null kilometers
        km_mask = df["kilometers"].notna()
        if not km_mask.any():
            logger.warning(
                "No valid kilometers found, setting all kilometers_score to 0.5"
            )
            df["kilometers_score"] = 0.5
            return df

        kilometers = df.loc[km_mask, "kilometers"].astype(float)

        # Winsorize to handle outliers
        winsorized_km = mstats.winsorize(
            kilometers, limits=(self.lower_percentile, 1 - self.upper_percentile)
        )

        # Min-max normalize to [0, 1]
        min_km = winsorized_km.min()
        max_km = winsorized_km.max()

        if min_km == max_km:
            # All kilometers are the same after winsorization
            normalized_km = pd.Series(0.5, index=kilometers.index)
        else:
            normalized_km = (winsorized_km - min_km) / (max_km - min_km)
            # Invert because fewer kilometers is better
            normalized_km = 1.0 - normalized_km

        # Assign scores
        df["kilometers_score"] = 0.5  # Default for missing kilometers
        df.loc[km_mask, "kilometers_score"] = normalized_km

        logger.debug(
            f"Kilometers scoring: {len(kilometers)} valid km values, range {min_km:.0f}-{max_km:.0f}"
        )

        return df

    def _score_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score condition component (already normalized to 0-1)."""
        if "condition_score" not in df.columns:
            logger.warning("No condition_score column found, setting to 0.5")
            df["condition_score"] = 0.5
        else:
            # Fill missing condition scores with neutral value
            df["condition_score"] = df["condition_score"].fillna(0.5)

            # Ensure values are in [0, 1] range
            df["condition_score"] = df["condition_score"].clip(0.0, 1.0)

        # Condition score is already normalized, so no additional processing needed
        logger.debug(
            f"Condition scoring: range {df['condition_score'].min():.2f}-{df['condition_score'].max():.2f}"
        )

        return df

    def _calculate_final_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate weighted final score from component scores."""
        # Ensure all component score columns exist with defaults
        for component in [
            "price_score",
            "year_score",
            "kilometers_score",
            "condition_score",
        ]:
            if component not in df.columns:
                df[component] = 0.5

        # Calculate weighted average
        df["score_raw"] = (
            df["price_score"] * self.weights["price"]
            + df["year_score"] * self.weights["year"]
            + df["kilometers_score"] * self.weights["kilometers"]
            + df["condition_score"] * self.weights["condition"]
        )

        # Convert to 0-100 scale and round
        df["score"] = (df["score_raw"] * 100).round().astype(int)

        # Ensure scores are in valid range
        df["score"] = df["score"].clip(0, 100)

        return df


def create_scorer(custom_weights: Optional[Dict[str, float]] = None) -> ListingScorer:
    """
    Factory function to create a ListingScorer.

    Args:
        custom_weights: Optional custom weights for scoring components

    Returns:
        Configured ListingScorer instance
    """
    return ListingScorer(custom_weights)


def score_listings_dataframe(
    df: pd.DataFrame, custom_weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Convenience function to score listings in a DataFrame.

    Args:
        df: DataFrame with listing data
        custom_weights: Optional custom weights for scoring

    Returns:
        DataFrame with added scoring columns
    """
    scorer = create_scorer(custom_weights)
    return scorer.score_listings(df)
