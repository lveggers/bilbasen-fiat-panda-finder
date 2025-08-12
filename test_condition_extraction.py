#!/usr/bin/env python3
"""Test the condition extraction fix."""

from src.app.scraper.json_extractor import BilbasenJSONExtractor

def test_condition_extraction():
    """Test that condition extraction now works with labels."""
    
    extractor = BilbasenJSONExtractor()
    
    # Test different condition descriptions
    test_cases = [
        {"description": "Bilen er i topstand og nysynet", "expected": "Topstand"},
        {"description": "Flot og velholdt bil", "expected": "Flot stand"},
        {"description": "Bilen har nogle skader og rust", "expected": "Skader"},
        {"description": "Defekt motor", "expected": "Defekt"},
        {"description": "Almindelig bil uden specielle bemærkninger", "expected": "Almindelig"},
        {"description": "", "expected": "Ukendt"}
    ]
    
    print("=== Testing Condition Extraction ===")
    for i, case in enumerate(test_cases, 1):
        result = extractor._parse_condition_from_description(case["description"])
        
        print(f"Test {i}:")
        print(f"  Description: '{case['description']}'")
        print(f"  Expected: {case['expected']}")
        print(f"  Got: {result['label']} (score: {result['score']:.2f})")
        print(f"  {'[PASS]' if result['label'] == case['expected'] else '[FAIL]'}")
        print()

if __name__ == "__main__":
    test_condition_extraction()