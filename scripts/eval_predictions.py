import os
import pandas as pd
import json
from datetime import datetime


def load_csv_files(prediction_dir, groundtruth_dir):
    """Load and pair original and reviewed CSV files."""
    file_pairs = []

    # Get all subdirectories in groundtruth_dir
    reviewed_datasets = [d for d in os.listdir(
        groundtruth_dir) if os.path.isdir(os.path.join(groundtruth_dir, d))]

    print(f"\nFound {len(reviewed_datasets)} datasets in {groundtruth_dir}")

    for dataset in reviewed_datasets:
        reviewed_dataset_dir = os.path.join(groundtruth_dir, dataset)
        reviewed_files = [f for f in os.listdir(
            reviewed_dataset_dir) if f.endswith('_reviewed.csv')]

        print(f"\nProcessing dataset: {dataset}")
        print(f"Found {len(reviewed_files)} reviewed files")

        for reviewed_file in reviewed_files:
            # Extract the number from reviewed file (e.g., "21" from "21_reviewed.csv")
            file_number = reviewed_file.split('_')[0]

            # Construct original file name (e.g., "coral_annotated_breastca_21_for_review.csv")
            original_file = os.path.join(
                prediction_dir, f"{dataset}_{file_number}_for_review.csv")

            if os.path.exists(original_file):
                file_pairs.append((
                    original_file,
                    os.path.join(reviewed_dataset_dir, reviewed_file)
                ))
                print(
                    f"✓ Matched: {reviewed_file} -> {os.path.basename(original_file)}")
            else:
                print(f"✗ No matching original file for: {reviewed_file}")

    return file_pairs
