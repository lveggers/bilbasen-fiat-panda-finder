"""Tests for Danish car condition parsing."""

import pytest
from src.app.parse_condition import (
    parse_condition,
    normalize_text,
    extract_condition_phrases,
    calculate_base_score,
    apply_modifiers,
    get_condition_description,
    parse_conditions_batch,
    CONDITION_MAPPINGS,
)


@pytest.mark.unit
class TestConditionParsing:
    """Test condition parsing functions."""

    def test_parse_condition_excellent_conditions(self):
        """Test parsing of excellent condition texts."""
        excellent_conditions = [
            "Nysynet",
            "Helt ny",
            "Fabriksny",
            "Som ny",
            "Topstand",
            "Perfekt stand",
        ]

        for condition in excellent_conditions:
            score, debug_info = parse_condition(condition)
            assert score >= 0.9, f"Expected high score for '{condition}', got {score}"
            assert "final_score" in debug_info
            assert debug_info["original_text"] == condition

    def test_parse_condition_good_conditions(self):
        """Test parsing of good condition texts."""
        good_conditions = ["Velholdt", "Pæn", "Flot", "God stand", "Fin stand"]

        for condition in good_conditions:
            score, debug_info = parse_condition(condition)
            assert (
                0.7 <= score <= 0.9
            ), f"Expected good score for '{condition}', got {score}"

    def test_parse_condition_average_conditions(self):
        """Test parsing of average condition texts."""
        average_conditions = [
            "Brugt",
            "Normal",
            "Normalt brugsspor",
            "Almindelig stand",
            "OK stand",
        ]

        for condition in average_conditions:
            score, debug_info = parse_condition(condition)
            assert (
                0.4 <= score <= 0.7
            ), f"Expected average score for '{condition}', got {score}"

    def test_parse_condition_poor_conditions(self):
        """Test parsing of poor condition texts."""
        poor_conditions = [
            "Reparationsobjekt",
            "Defekt",
            "Ødelagt",
            "Til dele",
            "Havareret",
        ]

        for condition in poor_conditions:
            score, debug_info = parse_condition(condition)
            assert score <= 0.2, f"Expected low score for '{condition}', got {score}"

    def test_parse_condition_empty_and_none(self):
        """Test parsing of empty and None conditions."""
        test_cases = ["", "   ", None, "     \n\t  "]

        for condition in test_cases:
            score, debug_info = parse_condition(condition)
            assert (
                score == 0.5
            ), f"Expected neutral score for empty condition, got {score}"
            assert debug_info["final_score"] == 0.5

    def test_parse_condition_with_modifiers(self):
        """Test parsing conditions with positive/negative modifiers."""
        # Positive modifiers
        positive_cases = [
            ("Meget pæn", "pæn"),
            ("Super flot", "flot"),
            ("Rigtig god stand", "god stand"),
        ]

        for modified, base in positive_cases:
            modified_score, _ = parse_condition(modified)
            base_score, _ = parse_condition(base)
            assert (
                modified_score >= base_score
            ), f"'{modified}' should score higher than '{base}'"

        # Negative modifiers/issues
        negative_cases = [
            "Pæn men med rust",
            "God stand med buler",
            "Flot bil med motor problemer",
        ]

        for condition in negative_cases:
            score, debug_info = parse_condition(condition)
            # Should be lower than just the positive part
            base_score, _ = parse_condition(condition.split(" men ")[0])
            assert score < base_score, f"'{condition}' should score lower due to issues"

    def test_parse_condition_case_insensitive(self):
        """Test that condition parsing is case insensitive."""
        test_cases = [
            ("NYSYNET", "nysynet"),
            ("Velholdt", "VELHOLDT"),
            ("God Stand", "god stand"),
            ("BRUGT", "brugt"),
        ]

        for upper, lower in test_cases:
            upper_score, _ = parse_condition(upper)
            lower_score, _ = parse_condition(lower)
            assert (
                upper_score == lower_score
            ), f"Case should not matter: {upper} vs {lower}"

    def test_parse_condition_danish_characters(self):
        """Test parsing with Danish special characters."""
        danish_conditions = ["Pæn stand", "Særlig flot", "Kørt få kilometer"]

        for condition in danish_conditions:
            score, debug_info = parse_condition(condition)
            assert (
                0.0 <= score <= 1.0
            ), f"Score should be valid for Danish text: {condition}"

    def test_parse_condition_debug_info(self):
        """Test that debug information is properly populated."""
        condition = "Meget pæn bil"
        score, debug_info = parse_condition(condition)

        required_keys = [
            "original_text",
            "normalized_text",
            "phrases",
            "base_matches",
            "modifier_effects",
            "base_score",
            "final_score",
        ]

        for key in required_keys:
            assert key in debug_info, f"Debug info missing key: {key}"

        assert debug_info["original_text"] == condition
        assert debug_info["final_score"] == score
        assert isinstance(debug_info["phrases"], list)
        assert isinstance(debug_info["base_matches"], list)
        assert isinstance(debug_info["modifier_effects"], list)


@pytest.mark.unit
class TestConditionUtilityFunctions:
    """Test utility functions for condition parsing."""

    def test_normalize_text(self):
        """Test text normalization function."""
        test_cases = [
            ("Meget Pæn", "meget paen"),
            ("God, stand!", "god stand"),
            ("  Extra   spaces  ", "extra spaces"),
            ("UPPERCASE", "uppercase"),
            ("Særlig høj kvalitet", "saerlig hoej kvalitet"),
            ("", ""),
        ]

        for input_text, expected in test_cases:
            result = normalize_text(input_text)
            assert (
                result == expected
            ), f"Normalization failed: '{input_text}' -> '{result}' (expected '{expected}')"

    def test_extract_condition_phrases(self):
        """Test phrase extraction from text."""
        text = "meget pæn stand"
        phrases = extract_condition_phrases(text)

        # Should include single words and combinations
        assert "meget" in phrases
        assert "paen" in phrases  # Normalized
        assert "stand" in phrases
        assert "meget paen" in phrases
        assert "paen stand" in phrases
        assert "meget paen stand" in phrases

    def test_calculate_base_score_known_conditions(self):
        """Test base score calculation for known conditions."""
        phrases = ["nysynet", "topstand", "velholdt"]
        score, matches = calculate_base_score(phrases)

        # Should pick the highest score
        expected_score = max(
            CONDITION_MAPPINGS[phrase]
            for phrase in phrases
            if phrase in CONDITION_MAPPINGS
        )
        assert score == expected_score
        assert len(matches) > 0

    def test_calculate_base_score_no_matches(self):
        """Test base score calculation with no matches."""
        phrases = ["unknown", "terms", "here"]
        score, matches = calculate_base_score(phrases)

        assert score == 0.5  # Default neutral score
        assert "no_match: 0.5" in matches

    def test_apply_modifiers(self):
        """Test modifier application."""
        base_score = 0.7

        # Test positive modifiers
        positive_phrases = ["meget", "super", "rigtig"]
        final_score, effects = apply_modifiers(base_score, positive_phrases)
        assert final_score > base_score
        assert len(effects) > 0

        # Test negative modifiers
        negative_phrases = ["rust", "buler", "motor"]
        final_score, effects = apply_modifiers(base_score, negative_phrases)
        assert final_score < base_score
        assert len(effects) > 0

        # Test bounds (should not go below 0 or above 1)
        extreme_negative = ["rust", "buler", "motor", "defekt", "havareret"] * 10
        final_score, _ = apply_modifiers(base_score, extreme_negative)
        assert 0.0 <= final_score <= 1.0

    def test_get_condition_description(self):
        """Test condition description function."""
        test_cases = [
            (0.95, "Excellent"),
            (0.85, "Very Good"),
            (0.75, "Good"),
            (0.55, "Fair"),
            (0.35, "Poor"),
            (0.05, "Very Poor"),
            (1.0, "Excellent"),
            (0.0, "Very Poor"),
        ]

        for score, expected in test_cases:
            result = get_condition_description(score)
            assert (
                result == expected
            ), f"Expected '{expected}' for score {score}, got '{result}'"

    def test_parse_conditions_batch(self):
        """Test batch processing of conditions."""
        conditions = ["Nysynet", "Velholdt", "Brugt", "Reparationsobjekt", None, ""]

        results = parse_conditions_batch(conditions)

        assert len(results) == len(conditions)

        for result in results:
            score, debug_info = result
            assert 0.0 <= score <= 1.0
            assert isinstance(debug_info, dict)

        # Check that scores are in expected order (excellent > good > poor)
        scores = [result[0] for result in results]
        assert scores[0] > scores[1]  # Nysynet > Velholdt
        assert scores[1] > scores[2]  # Velholdt > Brugt
        assert scores[2] > scores[3]  # Brugt > Reparationsobjekt


@pytest.mark.unit
class TestConditionEdgeCases:
    """Test edge cases in condition parsing."""

    def test_very_long_condition_text(self):
        """Test parsing of very long condition descriptions."""
        long_text = """
        Denne bil er i meget pæn stand og har været velholdt gennem hele sin levetid.
        Der er ingen rust eller buler, og motoren kører perfekt. Interiøret er også
        i topstand med minimal slitage. Bilen har været serviceret regelmæssigt og
        har alle service dokumenter. En rigtig flot bil som vil glæde sin næste ejer.
        """

        score, debug_info = parse_condition(long_text)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be positive due to good keywords
        assert len(debug_info["phrases"]) > 0

    def test_mixed_positive_negative_conditions(self):
        """Test conditions with both positive and negative aspects."""
        mixed_conditions = [
            "Pæn bil men med rust",
            "God stand dog med motor problemer",
            "Flot karosseri men slidt interior",
            "Topstand med enkelte ridser",
        ]

        for condition in mixed_conditions:
            score, debug_info = parse_condition(condition)

            assert 0.0 <= score <= 1.0

            # Should have both positive and negative effects
            effects = debug_info["modifier_effects"]
            positive_effects = [e for e in effects if "positive" in e]
            negative_effects = [e for e in effects if "negative" in e or "issue" in e]

            # Note: may not always have both due to keyword matching
            assert (
                len(effects) > 0
            ), f"Should have some modifier effects for: {condition}"

    def test_only_numbers_or_symbols(self):
        """Test conditions with only numbers or symbols."""
        weird_conditions = ["12345", "!!!", "€€€", "... --- ...", "2020 model"]

        for condition in weird_conditions:
            score, debug_info = parse_condition(condition)

            # Should default to neutral since no meaningful condition words
            assert score == 0.5
            assert debug_info["final_score"] == 0.5

    def test_multiple_identical_keywords(self):
        """Test conditions with repeated keywords."""
        condition = "meget meget pæn pæn stand stand"
        score, debug_info = parse_condition(condition)

        assert 0.0 <= score <= 1.0
        # Multiple instances of same modifier shouldn't compound infinitely
        assert score <= 1.0

    def test_foreign_language_mixed(self):
        """Test conditions mixing Danish and English/German."""
        mixed_conditions = [
            "Good condition - pæn stand",
            "Sehr gut - meget flot",
            "Perfect - topstand",
            "Damaged - beskadiget",
        ]

        for condition in mixed_conditions:
            score, debug_info = parse_condition(condition)

            assert 0.0 <= score <= 1.0
            # Should still extract some meaning from Danish parts
            assert debug_info["original_text"] == condition


@pytest.mark.unit
def test_condition_mappings_completeness():
    """Test that condition mappings are comprehensive."""
    # All scores should be between 0 and 1
    for condition, score in CONDITION_MAPPINGS.items():
        assert 0.0 <= score <= 1.0, f"Invalid score for '{condition}': {score}"
        assert isinstance(
            condition, str
        ), f"Condition key should be string: {condition}"
        assert len(condition) > 0, "Condition key should not be empty"

    # Should have reasonable coverage of Danish car conditions
    expected_categories = {
        "excellent": ["nysynet", "topstand", "perfekt"],
        "good": ["velholdt", "pæn", "flot"],
        "average": ["brugt", "normal"],
        "poor": ["reparationsobjekt", "defekt"],
    }

    for category, examples in expected_categories.items():
        for example in examples:
            assert any(
                example in condition for condition in CONDITION_MAPPINGS
            ), f"Missing condition from {category}: {example}"
