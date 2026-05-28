#!/usr/bin/env python3
"""
Test script for duplicate entity handling in robust matching algorithm.
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

def test_duplicate_entities():
    """Test the robust matching algorithm with duplicate entities"""
    
    # Initialize NER processor with mock objects
    processor = NERProcessor(MockModel(), MockPrompt(), MockPrompt())
    
    # Test case 1: Two identical entities in different positions
    print("=== Test Case 1: Two Identical Entities ===")
    original_text = "Patient has diabetes in family history and also has diabetes himself."
    ner_output = "Patient has <DISEASE>diabetes</DISEASE> in family history and also has <DISEASE>diabetes</DISEASE> himself."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Original text: {original_text}")
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Check if positions are different
    if len(positions) >= 2:
        pos1, pos2 = positions[0], positions[1]
        if pos1 == pos2:
            print("❌ PROBLEM: Both entities mapped to same position!")
        else:
            print(f"✅ GOOD: Entities mapped to different positions")
            print(f"   First 'diabetes' at {pos1}: '{original_text[pos1[0]:pos1[1]]}'")
            print(f"   Second 'diabetes' at {pos2}: '{original_text[pos2[0]:pos2[1]]}'")
    
    # Test case 2: Three identical entities
    print("\n=== Test Case 2: Three Identical Entities ===")
    original_text = "Diabetes runs in family. Patient has diabetes. Father also had diabetes."
    ner_output = "Diabetes runs in family. Patient has <DISEASE>diabetes</DISEASE>. Father also had <DISEASE>diabetes</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Original text: {original_text}")
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Check all positions
    unique_positions = set(positions)
    if len(unique_positions) < len(positions):
        print("❌ PROBLEM: Some entities mapped to same position!")
    else:
        print("✅ GOOD: All entities mapped to different positions")
    
    # Test case 3: Similar but different entities
    print("\n=== Test Case 3: Similar Entities ===")
    original_text = "Patient has diabetes mellitus and diabetes insipidus."
    ner_output = "Patient has <DISEASE>diabetes mellitus</DISEASE> and <DISEASE>diabetes insipidus</DISEASE>."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Original text: {original_text}")
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Test case 4: Overlapping entities
    print("\n=== Test Case 4: Overlapping Entities ===")
    original_text = "Patient has severe diabetes mellitus type 2."
    ner_output = "Patient has severe <DISEASE>diabetes</DISEASE> <DISEASE>diabetes mellitus</DISEASE> type 2."
    
    entities, tags, updated_string, positions = processor.parse_ner_result_text(
        ner_output, original_text, 0)
    
    print(f"Original text: {original_text}")
    print(f"Entities: {entities}")
    print(f"Positions: {positions}")
    
    # Check for overlapping positions
    if len(positions) >= 2:
        pos1, pos2 = positions[0], positions[1]
        if (pos1[0] < pos2[1] and pos2[0] < pos1[1]) and pos1 != (-1, -1) and pos2 != (-1, -1):
            print("⚠️  WARNING: Entities have overlapping positions!")
        else:
            print("✅ GOOD: No overlapping positions")
    
    print("\n=== Duplicate Entity Tests Completed ===")

if __name__ == "__main__":
    test_duplicate_entities() 