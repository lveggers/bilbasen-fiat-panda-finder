"""Parse and score car conditions from Danish text."""

import re
from typing import Dict, Optional, Tuple
from .logging_conf import get_logger

logger = get_logger("parse_condition")

# Danish condition mappings to scores (0.0 to 1.0, higher is better)
CONDITION_MAPPINGS = {
    # Excellent conditions (0.9 - 1.0)
    "nysynet": 1.0,
    "helt ny": 1.0,
    "fabriksny": 1.0,
    "som ny": 0.95,
    "topstand": 0.95,
    "perfekt stand": 0.95,
    "upåklagelig": 0.9,
    "fremragende": 0.9,
    # Very good conditions (0.8 - 0.89)
    "nyserviceret": 0.85,
    "meget pæn": 0.85,
    "virkelig pæn": 0.85,
    "super flot": 0.85,
    "flot": 0.8,
    "pæn": 0.8,
    "velholdt": 0.8,
    # Good conditions (0.6 - 0.79)
    "god stand": 0.75,
    "fin stand": 0.75,
    "god": 0.7,
    "fin": 0.7,
    "tilfredsstillende": 0.65,
    "ok stand": 0.65,
    "acceptabel": 0.6,
    "brugbar": 0.6,
    # Average conditions (0.4 - 0.59)
    "brugt": 0.55,
    "almindelig brugt": 0.55,
    "normal": 0.5,
    "normalt brugsspor": 0.5,
    "almindelig stand": 0.5,
    "middelstand": 0.45,
    "gennemsnitlig": 0.45,
    "brugsport": 0.4,
    # Poor conditions (0.2 - 0.39)
    "slidte": 0.35,
    "tærskel": 0.35,
    "slidt": 0.3,
    "mangler": 0.3,
    "skal repareres": 0.25,
    "trænger til": 0.25,
    "dårlig stand": 0.2,
    "dårlig": 0.2,
    # Very poor conditions (0.0 - 0.19)
    "reparationsobjekt": 0.1,
    "til dele": 0.05,
    "defekt": 0.0,
    "ødelagt": 0.0,
    "havareret": 0.0,
    "skrotet": 0.0,
}

# Additional keywords that modify scores
POSITIVE_MODIFIERS = {
    "meget": 0.05,
    "super": 0.05,
    "rigtig": 0.05,
    "særlig": 0.05,
    "ekstra": 0.05,
    "utrolig": 0.05,
}

NEGATIVE_MODIFIERS = {
    "lidt": -0.05,
    "noget": -0.05,
    "ret": -0.05,
    "temmelig": -0.1,
    "meget": -0.1,  # Context-dependent, but often negative when combined with poor conditions
}

# Common phrases that indicate specific issues
ISSUE_PHRASES = {
    "rust": -0.1,
    "buler": -0.05,
    "ridser": -0.03,
    "slitage": -0.05,
    "motor": -0.15,  # Engine issues are serious
    "gear": -0.1,
    "bremser": -0.1,
    "elektronik": -0.08,
    "aircon": -0.03,
    "aircondition": -0.03,
}


def normalize_text(text: str) -> str:
    """Normalize Danish text for condition parsing."""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower().strip()

    # Remove common punctuation and extra whitespace
    text = re.sub(r'[.,!?;:"\'()]+', " ", text)
    text = re.sub(r"\s+", " ", text)

    # Handle Danish special characters and common variations
    replacements = {
        "æ": "ae",
        "ø": "oe",
        "å": "aa",
        "nysynet": "nysynet",  # Keep as is
        "serviceret": "serviceret",  # Keep as is
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def extract_condition_phrases(text: str) -> list[str]:
    """Extract relevant condition phrases from text."""
    normalized = normalize_text(text)
    words = normalized.split()
    phrases = []

    # Single words
    phrases.extend(words)

    # Two-word combinations
    for i in range(len(words) - 1):
        two_word = f"{words[i]} {words[i+1]}"
        phrases.append(two_word)

    # Three-word combinations for common phrases
    for i in range(len(words) - 2):
        three_word = f"{words[i]} {words[i+1]} {words[i+2]}"
        phrases.append(three_word)

    return phrases


def calculate_base_score(phrases: list[str]) -> Tuple[float, list[str]]:
    """Calculate base condition score from phrases."""
    matches = []
    scores = []

    for phrase in phrases:
        if phrase in CONDITION_MAPPINGS:
            score = CONDITION_MAPPINGS[phrase]
            scores.append(score)
            matches.append(f"{phrase}: {score}")
            logger.debug(f"Matched condition phrase: '{phrase}' -> {score}")

    if not scores:
        return 0.5, ["no_match: 0.5"]  # Default neutral score

    # Use the highest score found (most optimistic interpretation)
    base_score = max(scores)
    return base_score, matches


def apply_modifiers(base_score: float, phrases: list[str]) -> Tuple[float, list[str]]:
    """Apply positive and negative modifiers to base score."""
    modifier_effects = []
    total_modifier = 0.0

    # Check for positive modifiers
    for phrase in phrases:
        if phrase in POSITIVE_MODIFIERS:
            modifier = POSITIVE_MODIFIERS[phrase]
            total_modifier += modifier
            modifier_effects.append(f"positive_modifier '{phrase}': +{modifier}")

    # Check for negative modifiers and issues
    for phrase in phrases:
        if phrase in NEGATIVE_MODIFIERS:
            modifier = NEGATIVE_MODIFIERS[phrase]
            total_modifier += modifier
            modifier_effects.append(f"negative_modifier '{phrase}': {modifier}")

        if phrase in ISSUE_PHRASES:
            modifier = ISSUE_PHRASES[phrase]
            total_modifier += modifier
            modifier_effects.append(f"issue_phrase '{phrase}': {modifier}")

    # Apply modifiers but keep within bounds
    final_score = max(0.0, min(1.0, base_score + total_modifier))

    return final_score, modifier_effects


def parse_condition(condition_text: Optional[str]) -> Tuple[float, Dict[str, any]]:
    """
    Parse Danish car condition text and return a score between 0.0 and 1.0.

    Args:
        condition_text: Danish text describing car condition

    Returns:
        Tuple of (score, debug_info) where:
        - score: float between 0.0 and 1.0 (higher is better)
        - debug_info: dict with parsing details for debugging
    """
    debug_info = {
        "original_text": condition_text,
        "normalized_text": "",
        "phrases": [],
        "base_matches": [],
        "modifier_effects": [],
        "base_score": 0.5,
        "final_score": 0.5,
    }

    # Handle empty or None input
    if not condition_text or not condition_text.strip():
        logger.debug("Empty condition text, using default score 0.5")
        debug_info["final_score"] = 0.5
        return 0.5, debug_info

    try:
        # Normalize and extract phrases
        normalized = normalize_text(condition_text)
        phrases = extract_condition_phrases(normalized)

        debug_info["normalized_text"] = normalized
        debug_info["phrases"] = phrases[:10]  # Limit for readability

        # Calculate base score
        base_score, base_matches = calculate_base_score(phrases)
        debug_info["base_score"] = base_score
        debug_info["base_matches"] = base_matches

        # Apply modifiers
        final_score, modifier_effects = apply_modifiers(base_score, phrases)
        debug_info["final_score"] = final_score
        debug_info["modifier_effects"] = modifier_effects

        logger.debug(f"Parsed condition '{condition_text}' -> {final_score}")
        return final_score, debug_info

    except Exception as e:
        logger.error(f"Error parsing condition '{condition_text}': {e}")
        debug_info["error"] = str(e)
        return 0.5, debug_info


def get_condition_description(score: float) -> str:
    """Get human-readable description for a condition score."""
    if score >= 0.9:
        return "Excellent"
    elif score >= 0.8:
        return "Very Good"
    elif score >= 0.6:
        return "Good"
    elif score >= 0.4:
        return "Fair"
    elif score >= 0.2:
        return "Poor"
    else:
        return "Very Poor"


# Batch processing function
def parse_conditions_batch(
    condition_texts: list[str],
) -> list[Tuple[float, Dict[str, any]]]:
    """Parse multiple condition texts in batch."""
    results = []
    for text in condition_texts:
        score, debug_info = parse_condition(text)
        results.append((score, debug_info))
    return results
