"""Tests for the scoring module."""

import pytest
import pandas as pd
import numpy as np
from src.app.scoring import ListingScorer, create_scorer, score_listings_dataframe, get_score_breakdown


@pytest.mark.unit
class TestListingScorer:
    """Test the ListingScorer class."""
    
    def test_scorer_initialization_default_weights(self):
        """Test scorer initialization with default weights."""
        scorer = ListingScorer()
        
        assert scorer.weights['price'] == 0.4
        assert scorer.weights['year'] == 0.25
        assert scorer.weights['kilometers'] == 0.25
        assert scorer.weights['condition'] == 0.1
        assert sum(scorer.weights.values()) == pytest.approx(1.0, rel=1e-9)
    
    def test_scorer_initialization_custom_weights(self):
        """Test scorer initialization with custom weights."""
        custom_weights = {
            'price': 0.5,
            'year': 0.2,
            'kilometers': 0.2,
            'condition': 0.1
        }
        
        scorer = ListingScorer(custom_weights)
        
        assert scorer.weights == custom_weights
        assert sum(scorer.weights.values()) == pytest.approx(1.0, rel=1e-9)
    
    def test_scorer_invalid_weights(self):
        """Test scorer with invalid weights that don't sum to 1.0."""
        invalid_weights = {
            'price': 0.5,
            'year': 0.2,
            'kilometers': 0.2,
            'condition': 0.2  # Sum = 1.1
        }
        
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ListingScorer(invalid_weights)
    
    def test_empty_dataframe(self):
        """Test scoring with empty DataFrame."""
        scorer = ListingScorer()
        empty_df = pd.DataFrame()
        
        result = scorer.score_listings(empty_df)
        
        assert result.empty
        assert len(result) == 0
    
    def test_score_price_component(self, sample_dataframe):
        """Test price scoring component."""
        scorer = ListingScorer()
        df = sample_dataframe.copy()
        
        result = scorer._score_price(df)
        
        assert 'price_score' in result.columns
        assert all(0.0 <= score <= 1.0 for score in result['price_score'])
        
        # Lower prices should have higher scores (inverted)
        min_price_idx = result['price_dkk'].idxmin()
        max_price_idx = result['price_dkk'].idxmax()
        
        assert result.loc[min_price_idx, 'price_score'] >= result.loc[max_price_idx, 'price_score']
    
    def test_score_year_component(self, sample_dataframe):
        """Test year scoring component."""
        scorer = ListingScorer()
        df = sample_dataframe.copy()
        
        result = scorer._score_year(df)
        
        assert 'year_score' in result.columns
        assert all(0.0 <= score <= 1.0 for score in result['year_score'])
        
        # Newer years should have higher scores
        min_year_idx = result['year'].idxmin()
        max_year_idx = result['year'].idxmax()
        
        assert result.loc[max_year_idx, 'year_score'] >= result.loc[min_year_idx, 'year_score']
    
    def test_score_kilometers_component(self, sample_dataframe):
        """Test kilometers scoring component."""
        scorer = ListingScorer()
        df = sample_dataframe.copy()
        
        result = scorer._score_kilometers(df)
        
        assert 'kilometers_score' in result.columns
        assert all(0.0 <= score <= 1.0 for score in result['kilometers_score'])
        
        # Lower kilometers should have higher scores (inverted)
        min_km_idx = result['kilometers'].idxmin()
        max_km_idx = result['kilometers'].idxmax()
        
        assert result.loc[min_km_idx, 'kilometers_score'] >= result.loc[max_km_idx, 'kilometers_score']
    
    def test_score_condition_component(self, sample_dataframe):
        """Test condition scoring component."""
        scorer = ListingScorer()
        df = sample_dataframe.copy()
        
        result = scorer._score_condition(df)
        
        assert 'condition_score' in result.columns
        assert all(0.0 <= score <= 1.0 for score in result['condition_score'])
        
        # All condition scores should be preserved (already normalized)
        for i, row in result.iterrows():
            original_score = sample_dataframe.loc[i, 'condition_score']
            assert row['condition_score'] == original_score
    
    def test_missing_data_handling(self):
        """Test handling of missing data in scoring."""
        df = pd.DataFrame({
            'price_dkk': [100000, None, 80000],
            'year': [2020, 2019, None],
            'kilometers': [50000, None, 70000],
            'condition_score': [0.8, 0.7, None]
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        # Should have default scores for missing data
        assert all(0.0 <= score <= 1.0 for score in result['price_score'])
        assert all(0.0 <= score <= 1.0 for score in result['year_score'])
        assert all(0.0 <= score <= 1.0 for score in result['kilometers_score'])
        assert all(0.0 <= score <= 1.0 for score in result['condition_score'])
        
        # Missing data should get default score of 0.5
        assert result.loc[1, 'price_score'] == 0.5  # Missing price
        assert result.loc[2, 'year_score'] == 0.5   # Missing year
        assert result.loc[1, 'kilometers_score'] == 0.5  # Missing km
        assert result.loc[2, 'condition_score'] == 0.5   # Missing condition
    
    def test_final_score_calculation(self, sample_dataframe):
        """Test final score calculation with weights."""
        scorer = ListingScorer()
        result = scorer.score_listings(sample_dataframe)
        
        assert 'score' in result.columns
        assert 'score_raw' in result.columns
        
        # All scores should be integers from 0 to 100
        assert all(isinstance(score, (int, np.integer)) for score in result['score'])
        assert all(0 <= score <= 100 for score in result['score'])
        
        # Verify weighted calculation for first row
        first_row = result.iloc[0]
        expected_raw = (
            first_row['price_score'] * scorer.weights['price'] +
            first_row['year_score'] * scorer.weights['year'] +
            first_row['kilometers_score'] * scorer.weights['kilometers'] +
            first_row['condition_score'] * scorer.weights['condition']
        )
        
        assert first_row['score_raw'] == pytest.approx(expected_raw, rel=1e-9)
        assert first_row['score'] == round(expected_raw * 100)
    
    def test_identical_values_handling(self):
        """Test handling when all values are identical."""
        df = pd.DataFrame({
            'price_dkk': [100000, 100000, 100000],
            'year': [2020, 2020, 2020],
            'kilometers': [50000, 50000, 50000],
            'condition_score': [0.8, 0.8, 0.8]
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        # When all values are identical, scores should be 0.5 (neutral)
        assert all(result['price_score'] == 0.5)
        assert all(result['year_score'] == 0.5)
        assert all(result['kilometers_score'] == 0.5)
        assert all(result['condition_score'] == 0.8)  # Unchanged
        
        # Final scores should be identical
        expected_score = round((0.5 * 0.4 + 0.5 * 0.25 + 0.5 * 0.25 + 0.8 * 0.1) * 100)
        assert all(result['score'] == expected_score)


@pytest.mark.unit
class TestScoringUtilities:
    """Test scoring utility functions."""
    
    def test_create_scorer_default(self):
        """Test create_scorer with default weights."""
        scorer = create_scorer()
        
        assert isinstance(scorer, ListingScorer)
        assert sum(scorer.weights.values()) == pytest.approx(1.0, rel=1e-9)
    
    def test_create_scorer_custom_weights(self):
        """Test create_scorer with custom weights."""
        custom_weights = {
            'price': 0.6,
            'year': 0.2,
            'kilometers': 0.1,
            'condition': 0.1
        }
        
        scorer = create_scorer(custom_weights)
        
        assert isinstance(scorer, ListingScorer)
        assert scorer.weights == custom_weights
    
    def test_score_listings_dataframe(self, sample_dataframe):
        """Test the convenience function for scoring DataFrames."""
        result = score_listings_dataframe(sample_dataframe)
        
        assert 'score' in result.columns
        assert len(result) == len(sample_dataframe)
        assert all(0 <= score <= 100 for score in result['score'])
    
    def test_get_score_breakdown(self, sample_dataframe):
        """Test getting score breakdown statistics."""
        scored_df = score_listings_dataframe(sample_dataframe)
        breakdown = get_score_breakdown(scored_df)
        
        assert 'total_listings' in breakdown
        assert 'scored_listings' in breakdown
        assert 'statistics' in breakdown
        assert 'score_ranges' in breakdown
        assert 'top_10' in breakdown
        
        assert breakdown['total_listings'] == len(sample_dataframe)
        assert breakdown['scored_listings'] > 0
        
        # Statistics should include basic stats
        stats = breakdown['statistics']
        assert 'min' in stats
        assert 'max' in stats
        assert 'mean' in stats
        assert 'median' in stats
        assert 'std' in stats
        
        # Score ranges should be present
        ranges = breakdown['score_ranges']
        assert isinstance(ranges, dict)
        
        # Top 10 should be list of records
        assert isinstance(breakdown['top_10'], list)
        assert len(breakdown['top_10']) <= 10
    
    def test_get_score_breakdown_empty_dataframe(self):
        """Test score breakdown with empty DataFrame."""
        empty_df = pd.DataFrame()
        breakdown = get_score_breakdown(empty_df)
        
        assert 'error' in breakdown
        assert breakdown['total_listings'] == 0


@pytest.mark.unit
class TestScoringEdgeCases:
    """Test edge cases in scoring."""
    
    def test_extreme_outliers(self):
        """Test scoring with extreme outliers."""
        df = pd.DataFrame({
            'price_dkk': [10000, 50000, 1000000],  # Extreme price range
            'year': [1990, 2020, 2023],
            'kilometers': [1000, 50000, 500000],  # Extreme km range
            'condition_score': [0.1, 0.5, 0.9]
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        # Should handle outliers gracefully with winsorization
        assert all(0 <= score <= 100 for score in result['score'])
        assert len(result) == len(df)
    
    def test_single_row_dataframe(self):
        """Test scoring with single row DataFrame."""
        df = pd.DataFrame({
            'price_dkk': [75000],
            'year': [2020],
            'kilometers': [50000],
            'condition_score': [0.8]
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        assert len(result) == 1
        assert 0 <= result.iloc[0]['score'] <= 100
        
        # Single value should get neutral scores for price/year/km
        assert result.iloc[0]['price_score'] == 0.5
        assert result.iloc[0]['year_score'] == 0.5
        assert result.iloc[0]['kilometers_score'] == 0.5
        assert result.iloc[0]['condition_score'] == 0.8
    
    def test_negative_values(self):
        """Test handling of negative values (should be filtered out)."""
        df = pd.DataFrame({
            'price_dkk': [-10000, 50000, 80000],  # Negative price
            'year': [2020, 2019, 1800],  # Year before reasonable range
            'kilometers': [50000, -5000, 70000],  # Negative km
            'condition_score': [0.8, 0.7, -0.1]  # Negative condition (should be clipped)
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        assert len(result) == len(df)
        assert all(0 <= score <= 100 for score in result['score'])
        
        # Negative condition score should be clipped to 0
        assert result.iloc[2]['condition_score'] == 0.0
    
    def test_very_large_dataset(self):
        """Test scoring performance with larger dataset."""
        # Create a larger test dataset
        np.random.seed(42)  # For reproducibility
        n_rows = 1000
        
        df = pd.DataFrame({
            'price_dkk': np.random.randint(20000, 200000, n_rows),
            'year': np.random.randint(2010, 2024, n_rows),
            'kilometers': np.random.randint(5000, 300000, n_rows),
            'condition_score': np.random.uniform(0.0, 1.0, n_rows)
        })
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        assert len(result) == n_rows
        assert all(0 <= score <= 100 for score in result['score'])
        
        # Check that scoring preserves order of rows
        assert list(result.index) == list(df.index)
    
    def test_mixed_data_types(self):
        """Test scoring with mixed/invalid data types."""
        df = pd.DataFrame({
            'price_dkk': [75000, "invalid", 85000, None],
            'year': [2020, 2019, "2018", None],
            'kilometers': [50000, None, 60000, "high"],
            'condition_score': [0.8, 0.7, None, 0.9]
        })
        
        # Convert problematic values to NaN
        df['price_dkk'] = pd.to_numeric(df['price_dkk'], errors='coerce')
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['kilometers'] = pd.to_numeric(df['kilometers'], errors='coerce')
        
        scorer = ListingScorer()
        result = scorer.score_listings(df)
        
        assert len(result) == len(df)
        assert all(0 <= score <= 100 for score in result['score'])
        
        # Invalid/missing values should get default scores
        assert result.iloc[1]['price_score'] == 0.5  # "invalid" price
        assert result.iloc[3]['year_score'] == 0.5    # None year
        assert result.iloc[3]['kilometers_score'] == 0.5  # "high" km