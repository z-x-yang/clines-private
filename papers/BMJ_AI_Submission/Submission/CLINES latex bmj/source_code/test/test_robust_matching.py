#!/usr/bin/env python3
"""
Test script for the enhanced robust entity matching algorithm in CLINES.
This script tests the new matching capabilities with various edge cases.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ehr_processing_pipeline.ner_processor import NERProcessor
import logging

# Configure logging for testing
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class MockModel:
    """Mock model for testing purposes"""
    pass

class MockPrompt:
    """Mock prompt for testing purposes"""
    pass

def test_robust_matching():
    """Test the robust matching algorithm with various scenarios"""
    
    # Initialize NER processor with mock objects
    processor = NERProcessor(MockModel(), MockPrompt(), MockPrompt())
    
    # Test case 1: Basic matching
    print("=== Test Case 1: Basic Matching ===")
    original_text = "Patient has diabetes mellitus type 2 and hypertension."
    ner_output = "Patient has <DISEASE>diabetes mellitus type 2</DISEASE> and <DISEASE>hypertension</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 2: Space differences
    print("\n=== Test Case 2: Space Differences ===")
    original_text = "Patient has diabetes  mellitus   type 2."
    ner_output = "Patient has <DISEASE>diabetes mellitus type 2</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 3: Case differences
    print("\n=== Test Case 3: Case Differences ===")
    original_text = "Patient has DIABETES MELLITUS TYPE 2."
    ner_output = "Patient has <DISEASE>diabetes mellitus type 2</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 4: Punctuation differences
    print("\n=== Test Case 4: Punctuation Differences ===")
    original_text = "Patient has diabetes-mellitus, type-2."
    ner_output = "Patient has <DISEASE>diabetes mellitus type 2</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 5: Mixed case and space issues
    print("\n=== Test Case 5: Mixed Case and Space Issues ===")
    original_text = "PATIENT  HAS   Diabetes   Mellitus   TYPE   2."
    ner_output = "Patient has <DISEASE>diabetes mellitus type 2</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 6: Multiple entities with overlapping issues
    print("\n=== Test Case 6: Multiple Entities with Complex Issues ===")
    original_text = "Patient has DIABETES-MELLITUS, and   severe  HYPERTENSION."
    ner_output = "Patient has <DISEASE>diabetes mellitus</DISEASE>, and <DISEASE>hypertension</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 7: Special characters and numbers
    print("\n=== Test Case 7: Special Characters and Numbers ===")
    original_text = "Patient has COVID-19 infection and vitamin-D deficiency."
    ner_output = "Patient has <DISEASE>COVID 19</DISEASE> infection and <DISEASE>vitamin D deficiency</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 8: Hyphen-specific tests
    print("\n=== Test Case 8: Hyphen-Specific Patterns ===")
    original_text = "Patient diagnosed with non-small-cell lung cancer."
    ner_output = "Patient diagnosed with <DISEASE>non small cell lung cancer</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 9: Medical abbreviations with numbers
    print("\n=== Test Case 9: Medical Abbreviations with Numbers ===")
    original_text = "Patient has Type-2 diabetes and Stage-3 CKD."
    ner_output = "Patient has <DISEASE>Type 2 diabetes</DISEASE> and <DISEASE>Stage 3 CKD</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 10: Complex medical terminology
    print("\n=== Test Case 10: Complex Medical Terminology ===")
    original_text = "Patient has gastro-esophageal reflux disease (GERD)."
    ner_output = "Patient has <DISEASE>gastroesophageal reflux disease</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    print("\n=== All Tests Completed ===")
    
    # Display strategy statistics
    print("\n=== Strategy Performance Report ===")
    processor.log_strategy_statistics()
    stats = processor.get_strategy_statistics()
    
    print(f"\nDetailed Statistics:")
    print(f"- Total entities: {stats['total_entities']}")
    print(f"- Successful matches: {stats['successful_matches']}")
    print(f"- Overall success rate: {stats['overall_success_rate']:.1f}%")
    
    print(f"\nStrategy breakdown:")
    for strategy in ['context_exact', 'context_fuzzy', 'direct_search', 'chunk_fallback', 'simple_fallback']:
        attempts = stats[strategy]['attempts']
        successes = stats[strategy]['successes']
        rate = stats[strategy]['success_rate']
        print(f"- {strategy.replace('_', ' ').title()}: {successes}/{attempts} ({rate:.1f}%)")

if __name__ == "__main__":
    test_robust_matching() 