#!/usr/bin/env python3
"""
Generate unique patient_num and encounter_num for i2b2 CSV files.

This script processes i2b2 format CSV files in a specified directory,
generates unique patient_num and encounter_num for each file,
and overwrites the original files with updated IDs.
"""

import pandas as pd
import random
import logging
import sys
from pathlib import Path
from typing import List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PATIENT_NUM_MIN = 100000
PATIENT_NUM_MAX = 999999
ENCOUNTER_NUM_MIN = 1000000
ENCOUNTER_NUM_MAX = 9999999


def scan_csv_files(directory: str) -> List[str]:
    """
    Scan directory for i2b2 CSV files.
    
    Args:
        directory: Target directory path
        
    Returns:
        List of CSV file paths
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    csv_files = list(directory_path.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in {directory}")
    
    return [str(file) for file in csv_files]


def generate_unique_ids(used_patient_ids: Set[int], used_encounter_ids: Set[int]) -> Tuple[int, int]:
    """
    Generate unique patient_num and encounter_num.
    
    Args:
        used_patient_ids: Set of already used patient IDs
        used_encounter_ids: Set of already used encounter IDs
        
    Returns:
        Tuple of (patient_num, encounter_num)
    """
    # Generate unique patient_num
    while True:
        patient_num = random.randint(PATIENT_NUM_MIN, PATIENT_NUM_MAX)
        if patient_num not in used_patient_ids:
            used_patient_ids.add(patient_num)
            break
    
    # Generate unique encounter_num
    while True:
        encounter_num = random.randint(ENCOUNTER_NUM_MIN, ENCOUNTER_NUM_MAX)
        if encounter_num not in used_encounter_ids:
            used_encounter_ids.add(encounter_num)
            break
    
    return patient_num, encounter_num


def update_csv_file(file_path: str, patient_num: int, encounter_num: int) -> None:
    """
    Update CSV file with new patient_num and encounter_num.
    
    Args:
        file_path: Path to CSV file
        patient_num: New patient number
        encounter_num: New encounter number
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Verify expected columns exist
        if 'patient_num' not in df.columns or 'encounter_num' not in df.columns:
            raise ValueError(f"Missing required columns in {file_path}")
        
        # Update IDs
        df['patient_num'] = patient_num
        df['encounter_num'] = encounter_num
        
        # Write back to file (overwrite)
        df.to_csv(file_path, index=False)
        
        logger.info(f"Updated {file_path}: patient_num={patient_num}, encounter_num={encounter_num}")
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        raise


def main(target_directory: str) -> None:
    """
    Main function to process all CSV files in target directory.
    
    Args:
        target_directory: Directory containing i2b2 CSV files
    """
    logger.info("Starting patient_num and encounter_num generation")
    
    try:
        # Scan for CSV files
        csv_files = scan_csv_files(target_directory)
        
        if not csv_files:
            logger.warning("No CSV files found in directory")
            return
        
        # Track used IDs for uniqueness
        used_patient_ids: Set[int] = set()
        used_encounter_ids: Set[int] = set()
        
        # Process each file
        for i, file_path in enumerate(csv_files, 1):
            logger.info(f"Processing file {i}/{len(csv_files)}: {Path(file_path).name}")
            
            # Generate unique IDs
            patient_num, encounter_num = generate_unique_ids(used_patient_ids, used_encounter_ids)
            
            # Update CSV file
            update_csv_file(file_path, patient_num, encounter_num)
        
        logger.info(f"Successfully processed {len(csv_files)} files")
        logger.info(f"Generated {len(used_patient_ids)} unique patient IDs")
        logger.info(f"Generated {len(used_encounter_ids)} unique encounter IDs")
        
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Default target directory
    target_dir = "new_outputs/gpt4o_output_i2b2_after_transform"
    
    # Allow command line override
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    
    main(target_dir) 