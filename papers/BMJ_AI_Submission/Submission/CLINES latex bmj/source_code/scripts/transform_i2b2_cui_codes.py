#!/usr/bin/env python3
"""
CUI Code Transformation Script for i2b2 CSV Files

This script transforms CUI codes in i2b2 CSV files to other coding systems
following a priority order: ICD10CM -> LNC -> RXNORM -> ICD10PCS -> ICD9CM.

Author: Claude AI Assistant
Created: 2025-01-14
"""

import pandas as pd
import os
import glob
import logging
import re
import argparse
import sys
import time
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
from tqdm import tqdm

# Import the CUI mapping functionality
from cui_to_other_code_local import map_cui_to_codes, get_available_systems, clear_cache

# Configure logging


def setup_logging(log_level: str = 'INFO', log_file: str = 'cui_transformation.log'):
    """Setup logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    return logging.getLogger(__name__)


# Priority order for code systems (as specified in requirements)
# Diagnoses: ICD10CM, ICD9CM
# Procedures: CPT4, HCPCS, ICD10PCS, ICD9PROC
# Medications: RxNorm, NDC
# Laboratory Tests and Vital Signs: LOINC
PRIORITY_SYSTEMS = ['ICD10CM', 'LNC', 'RXNORM', 'ICD10PCS', 'ICD9CM', 'HCPCS', 'CPT', 'SNOMEDCT_US']


def extract_cui_from_concept_cd(concept_cd: str) -> Optional[str]:
    """
    Extract CUI code from concept_cd column format.

    Parameters:
    -----------
    concept_cd : str
        Input string in format "C3524387||description"

    Returns:
    --------
    Optional[str]
        Extracted CUI code or None if invalid format
    """
    if not isinstance(concept_cd, str) or not concept_cd.strip():
        return None

    # Split by || separator
    parts = concept_cd.split('||')
    if len(parts) < 1:
        return None

    cui_candidate = parts[0].strip()

    # Validate CUI format: C followed by 7 digits
    if re.match(r'^C\d{7}$', cui_candidate):
        return cui_candidate

    return None


def find_best_code_mapping(cui: str, priority_systems: List[str], logger) -> Tuple[str, str]:
    """
    Find the best code mapping for a CUI following priority order.

    Parameters:
    -----------
    cui : str
        CUI code to map
    priority_systems : List[str]
        List of systems in priority order
    logger : logging.Logger
        Logger instance

    Returns:
    --------
    Tuple[str, str]
        (mapped_code, system_type) or (original_cui, 'CUI') if no mapping found
    """
    try:
        # Get mapping results for all priority systems
        mapping_result = map_cui_to_codes(
            [cui], priority_systems, include_metadata=False)

        # Check each system in priority order
        for system in priority_systems:
            system_mappings = mapping_result[
                (mapping_result['TARGET_SYSTEM'] == system) &
                (mapping_result['MAPPING_STATUS'] == 'FOUND')
            ]

            if not system_mappings.empty:
                # Return the first successful mapping
                target_code = system_mappings.iloc[0]['TARGET_CODE']
                logger.debug(f"Mapped {cui} -> {target_code} ({system})")
                return target_code, system

        # No mapping found in any system
        logger.debug(f"No mapping found for {cui}, keeping original")
        return cui, 'CUI'

    except Exception as e:
        logger.error(f"Error mapping CUI {cui}: {str(e)}")
        return cui, 'CUI'


def batch_map_cuis(cuis: List[str], priority_systems: List[str], logger, batch_size: int = 1000) -> Dict[str, Tuple[str, str]]:
    """
    Batch process CUI mappings for better performance.

    Parameters:
    -----------
    cuis : List[str]
        List of CUI codes to map
    priority_systems : List[str]
        List of systems in priority order
    logger : logging.Logger
        Logger instance
    batch_size : int
        Size of batches for processing

    Returns:
    --------
    Dict[str, Tuple[str, str]]
        Dictionary mapping CUI to (mapped_code, system_type)
    """
    code_mappings = {}

    # Process CUIs in batches
    for i in range(0, len(cuis), batch_size):
        batch_cuis = cuis[i:i+batch_size]
        logger.debug(
            f"Processing CUI batch {i//batch_size + 1}/{(len(cuis) + batch_size - 1)//batch_size}")

        try:
            # Get mapping results for the entire batch
            mapping_result = map_cui_to_codes(
                batch_cuis, priority_systems, include_metadata=False)

            # Process each CUI in the batch
            for cui in batch_cuis:
                cui_found = False

                # Check each system in priority order
                for system in priority_systems:
                    system_mappings = mapping_result[
                        (mapping_result['CUI'] == cui) &
                        (mapping_result['TARGET_SYSTEM'] == system) &
                        (mapping_result['MAPPING_STATUS'] == 'FOUND')
                    ]

                    if not system_mappings.empty:
                        # Use the first successful mapping
                        target_code = system_mappings.iloc[0]['TARGET_CODE']
                        code_mappings[cui] = (target_code, system)
                        cui_found = True
                        break

                # If no mapping found in any system
                if not cui_found:
                    code_mappings[cui] = (cui, 'CUI')

        except Exception as e:
            logger.error(f"Error in batch mapping: {str(e)}")
            # Fallback to individual processing for this batch
            for cui in batch_cuis:
                code_mappings[cui] = find_best_code_mapping(
                    cui, priority_systems, logger)

    return code_mappings


def transform_csv_file(input_path: str, output_path: str, logger, show_progress: bool = True) -> Dict[str, int]:
    """
    Transform a single CSV file by converting CUI codes.

    Parameters:
    -----------
    input_path : str
        Path to input CSV file
    output_path : str
        Path to output CSV file
    logger : logging.Logger
        Logger instance
    show_progress : bool
        Whether to show progress bar

    Returns:
    --------
    Dict[str, int]
        Statistics about the transformation
    """
    stats = {
        'total_rows': 0,
        'processed_rows': 0,
        'successful_conversions': 0,
        'failed_conversions': 0,
        'conversion_by_system': {system: 0 for system in PRIORITY_SYSTEMS + ['CUI']}
    }

    try:
        logger.info(f"Processing file: {input_path}")

        # Read CSV file
        df = pd.read_csv(input_path)
        stats['total_rows'] = len(df)

        # Check if concept_cd column exists
        if 'concept_cd' not in df.columns:
            raise ValueError(f"concept_cd column not found in {input_path}")

        # Initialize the new code_type column
        df['code_type'] = 'CUI'  # Default value

        # Extract all unique CUIs for batch processing
        unique_concept_cds = df['concept_cd'].dropna().unique()
        cui_mapping = {}

        logger.info(
            f"Extracting CUIs from {len(unique_concept_cds)} unique concept_cd values")

        # Extract CUIs and build mapping dictionary
        for concept_cd in unique_concept_cds:
            cui = extract_cui_from_concept_cd(concept_cd)
            if cui:
                cui_mapping[concept_cd] = cui

        # Get all unique CUIs for batch mapping
        unique_cuis = list(set(cui_mapping.values()))

        if unique_cuis:
            logger.info(f"Processing {len(unique_cuis)} unique CUIs")

            # Use batch processing for better performance
            code_mappings = batch_map_cuis(
                unique_cuis, PRIORITY_SYSTEMS, logger)
        else:
            code_mappings = {}

        # Apply transformations to the DataFrame
        progress_iterator = tqdm(df.iterrows(), total=len(
            df), desc="Transforming rows") if show_progress else df.iterrows()

        for idx, row in progress_iterator:
            stats['processed_rows'] += 1
            concept_cd = row['concept_cd']

            if pd.isna(concept_cd):
                continue

            cui = cui_mapping.get(concept_cd)
            if cui and cui in code_mappings:
                mapped_code, system_type = code_mappings[cui]

                # Update the row
                df.at[idx, 'concept_cd'] = mapped_code
                df.at[idx, 'code_type'] = system_type

                # Update statistics
                stats['conversion_by_system'][system_type] += 1
                if system_type != 'CUI':
                    stats['successful_conversions'] += 1
                else:
                    stats['failed_conversions'] += 1
            else:
                stats['failed_conversions'] += 1

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save transformed CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Saved transformed file: {output_path}")

        return stats

    except Exception as e:
        logger.error(f"Error processing file {input_path}: {str(e)}")
        raise


def process_all_files(input_dir: str, output_dir: str, logger, show_progress: bool = True) -> Dict[str, Any]:
    """
    Process all CSV files in the input directory.

    Parameters:
    -----------
    input_dir : str
        Input directory path
    output_dir : str
        Output directory path
    logger : logging.Logger
        Logger instance
    show_progress : bool
        Whether to show progress bar

    Returns:
    --------
    Dict[str, Any]
        Overall processing statistics
    """
    # Find all CSV files
    csv_pattern = os.path.join(input_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        raise ValueError(f"No CSV files found in {input_dir}")

    logger.info(f"Found {len(csv_files)} CSV files to process")

    # Initialize overall statistics
    overall_stats = {
        'total_files': len(csv_files),
        'processed_files': 0,
        'total_rows': 0,
        'successful_conversions': 0,
        'failed_conversions': 0,
        'conversion_by_system': {system: 0 for system in PRIORITY_SYSTEMS + ['CUI']},
        'file_stats': {},
        'processing_time': 0
    }

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()

    # Process each file with progress bar
    file_iterator = tqdm(
        csv_files, desc="Processing files") if show_progress else csv_files

    for input_file in file_iterator:
        try:
            # Generate output file path
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_dir, filename)

            if show_progress:
                file_iterator.set_description(f"Processing {filename}")

            logger.info(
                f"Processing file {overall_stats['processed_files'] + 1}/{len(csv_files)}: {filename}")

            # Transform the file
            file_stats = transform_csv_file(
                input_file, output_file, logger, show_progress=False)

            # Update overall statistics
            overall_stats['processed_files'] += 1
            overall_stats['total_rows'] += file_stats['total_rows']
            overall_stats['successful_conversions'] += file_stats['successful_conversions']
            overall_stats['failed_conversions'] += file_stats['failed_conversions']

            for system, count in file_stats['conversion_by_system'].items():
                overall_stats['conversion_by_system'][system] += count

            overall_stats['file_stats'][filename] = file_stats

            logger.info(
                f"Completed {filename}: {file_stats['successful_conversions']}/{file_stats['processed_rows']} successful conversions")

        except Exception as e:
            logger.error(f"Failed to process file {input_file}: {str(e)}")
            continue

    overall_stats['processing_time'] = time.time() - start_time
    return overall_stats


def generate_report(overall_stats: Dict[str, Any], output_dir: str, logger) -> None:
    """
    Generate a detailed processing report.

    Parameters:
    -----------
    overall_stats : Dict[str, Any]
        Overall processing statistics
    output_dir : str
        Output directory path
    logger : logging.Logger
        Logger instance
    """
    report_path = os.path.join(output_dir, "transformation_report.txt")

    with open(report_path, 'w') as f:
        f.write("=== CUI Code Transformation Report ===\n\n")
        f.write(
            f"Processing completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"Total processing time: {overall_stats['processing_time']:.2f} seconds\n\n")

        f.write("=== Overall Statistics ===\n")
        f.write(f"Total files: {overall_stats['total_files']}\n")
        f.write(f"Processed files: {overall_stats['processed_files']}\n")
        f.write(f"Total rows: {overall_stats['total_rows']}\n")
        f.write(
            f"Successful conversions: {overall_stats['successful_conversions']}\n")
        f.write(f"Failed conversions: {overall_stats['failed_conversions']}\n")

        success_rate = (overall_stats['successful_conversions'] / overall_stats['total_rows'] * 100
                        if overall_stats['total_rows'] > 0 else 0)
        f.write(f"Success rate: {success_rate:.2f}%\n\n")

        f.write("=== Conversion by System ===\n")
        for system, count in overall_stats['conversion_by_system'].items():
            percentage = (count / overall_stats['total_rows'] * 100
                          if overall_stats['total_rows'] > 0 else 0)
            f.write(f"{system}: {count} ({percentage:.2f}%)\n")

        f.write("\n=== File-by-File Statistics ===\n")
        for filename, file_stats in overall_stats['file_stats'].items():
            f.write(f"\n{filename}:\n")
            f.write(f"  Total rows: {file_stats['total_rows']}\n")
            f.write(
                f"  Successful conversions: {file_stats['successful_conversions']}\n")
            f.write(
                f"  Failed conversions: {file_stats['failed_conversions']}\n")
            file_success_rate = (file_stats['successful_conversions'] / file_stats['total_rows'] * 100
                                 if file_stats['total_rows'] > 0 else 0)
            f.write(f"  Success rate: {file_success_rate:.2f}%\n")

    logger.info(f"Detailed report saved to: {report_path}")


def test_functionality(logger) -> bool:
    """
    Test basic functionality of the script.

    Parameters:
    -----------
    logger : logging.Logger
        Logger instance

    Returns:
    --------
    bool
        True if tests pass, False otherwise
    """
    logger.info("Running functionality tests...")

    try:
        # Test CUI extraction
        test_concept_cd = "C0281361||pancreatic adenocarcinoma"
        extracted_cui = extract_cui_from_concept_cd(test_concept_cd)
        assert extracted_cui == "C0281361", f"Expected C0281361, got {extracted_cui}"

        # Test invalid CUI extraction
        invalid_concept_cd = "INVALID||test"
        extracted_invalid = extract_cui_from_concept_cd(invalid_concept_cd)
        assert extracted_invalid is None, f"Expected None for invalid CUI, got {extracted_invalid}"

        # Test available systems
        available_systems = get_available_systems()
        assert isinstance(available_systems,
                          list), "Available systems should be a list"
        assert len(available_systems) > 0, "Should have available systems"

        logger.info("All functionality tests passed!")
        return True

    except Exception as e:
        logger.error(f"Functionality test failed: {str(e)}")
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Transform CUI codes in i2b2 CSV files to other coding systems"
    )

    parser.add_argument(
        '--input-dir', '-i',
        default="../new_outputs/gpt4o_output_i2b2",
        help="Input directory containing i2b2 CSV files (default: new_outputs/gpt4o_output_i2b2)"
    )

    parser.add_argument(
        '--output-dir', '-o',
        default="../new_outputs/gpt4o_output_i2b2_after_transform",
        help="Output directory for transformed files (default: new_outputs/gpt4o_output_i2b2_after_transform)"
    )

    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        '--log-file',
        default='cui_transformation.log',
        help="Log file path (default: cui_transformation.log)"
    )

    parser.add_argument(
        '--no-progress',
        action='store_true',
        help="Disable progress bars"
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help="Run functionality tests and exit"
    )

    parser.add_argument(
        '--priority-systems',
        nargs='+',
        default=PRIORITY_SYSTEMS,
        help=f"Priority order of coding systems (default: {' '.join(PRIORITY_SYSTEMS)})"
    )

    return parser.parse_args()


def main() -> None:
    """
    Main function to execute the CUI transformation process.
    """
    args = parse_arguments()
    logger = setup_logging(args.log_level, args.log_file)

    # Run tests if requested
    if args.test:
        success = test_functionality(logger)
        sys.exit(0 if success else 1)

    logger.info("=== CUI Code Transformation Process Started ===")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Priority systems: {args.priority_systems}")
    logger.info(
        f"Progress bars: {'Disabled' if args.no_progress else 'Enabled'}")

    try:
        # Check if input directory exists
        if not os.path.exists(args.input_dir):
            raise ValueError(
                f"Input directory does not exist: {args.input_dir}")

        # Run functionality tests first
        if not test_functionality(logger):
            raise RuntimeError("Functionality tests failed")

        # Process all files
        overall_stats = process_all_files(
            args.input_dir,
            args.output_dir,
            logger,
            show_progress=not args.no_progress
        )

        # Generate summary report
        logger.info("=== Transformation Summary ===")
        logger.info(f"Total files: {overall_stats['total_files']}")
        logger.info(f"Processed files: {overall_stats['processed_files']}")
        logger.info(f"Total rows: {overall_stats['total_rows']}")
        logger.info(
            f"Successful conversions: {overall_stats['successful_conversions']}")
        logger.info(
            f"Failed conversions: {overall_stats['failed_conversions']}")
        logger.info(
            f"Processing time: {overall_stats['processing_time']:.2f} seconds")

        success_rate = (overall_stats['successful_conversions'] / overall_stats['total_rows'] * 100
                        if overall_stats['total_rows'] > 0 else 0)
        logger.info(f"Success rate: {success_rate:.2f}%")

        logger.info("Conversion by system:")
        for system, count in overall_stats['conversion_by_system'].items():
            percentage = (count / overall_stats['total_rows'] * 100
                          if overall_stats['total_rows'] > 0 else 0)
            logger.info(f"  {system}: {count} ({percentage:.2f}%)")

        # Generate detailed report
        generate_report(overall_stats, args.output_dir, logger)

        # Clear cache to free memory
        clear_cache()

        logger.info("=== CUI Code Transformation Process Completed ===")

    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
