#!/usr/bin/env python3
import os
import subprocess
import glob
import pandas as pd
import argparse
from pathlib import Path
import sys
import re

# Base paths
BASE_PATH = "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data"
DATA_PATHS = {
    "4CE": os.path.join(BASE_PATH, "data/4CE"),
    "breastca": os.path.join(BASE_PATH, "data/coral_annotated_breastca"),
    "pdac": os.path.join(BASE_PATH, "data/coral_annotated_pdac")
}
MODEL_OUTPUTS = {
    "deepseek": os.path.join(BASE_PATH, "outputs/deepseek_output"),
    "gpt4o": os.path.join(BASE_PATH, "outputs/gpt4o_output"),
    "llama": os.path.join(BASE_PATH, "outputs/llama-405b_output")
}
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
OUTPUT_PATH = os.path.join(BASE_PATH, "outputs")

# Create output directories if they don't exist
POSITION_OUTPUT_DIR = os.path.join(OUTPUT_PATH, "with_positions")
MERGED_OUTPUT_DIR = os.path.join(OUTPUT_PATH, "merged")
FINAL_OUTPUT_DIR = os.path.join(OUTPUT_PATH, "final")

for directory in [POSITION_OUTPUT_DIR, MERGED_OUTPUT_DIR, FINAL_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)


def run_command(command):
    """Run a shell command and print its output"""
    print(f"Running: {command}")
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
    return process.returncode


def find_matching_note(csv_file, data_paths):
    """Find the corresponding note file for a CSV result file"""
    # Extract the note identifier from the CSV filename
    filename = os.path.basename(csv_file)
    print(f"\nTrying to find note for: {filename}")

    # Extract the part between prefix and "_default"
    match = re.search(r'(.+)_default\.csv$', filename)
    if not match:
        print(
            f"Filename {filename} doesn't match expected pattern with '_default.csv'")
        return None

    full_prefix = match.group(1)  # Everything before "_default.csv"
    print(f"  Extracted prefix: {full_prefix}")

    if filename.startswith("4CE"):
        # For 4CE files: if 4CE_BCH_1_default.csv, note is BCH_1.txt
        if "_" in full_prefix:
            # Remove the first part (4CE_)
            note_id = full_prefix.split("_", 1)[1]  # Get "BCH_1"
            print(f"  4CE file detected, looking for note: {note_id}.txt")
            for path in glob.glob(os.path.join(DATA_PATHS["4CE"], f"{note_id}.txt")):
                print(f"  Found note file: {path}")
                return path
            print(f"  No matching note found in {DATA_PATHS['4CE']}")

    elif "breastca" in filename:
        # For breast cancer files: if coral_annotated_breastca_32_default.csv, note is 32.txt
        match = re.search(
            r'coral_annotated_breastca_(\d+)_default\.csv$', filename)
        if match:
            note_id = match.group(1)  # Get the number part
            note_path = os.path.join(DATA_PATHS["breastca"], f"{note_id}.txt")
            print(
                f"  Breast cancer file detected, looking for note: {note_id}.txt")
            if os.path.exists(note_path):
                print(f"  Found note file: {note_path}")
                return note_path
            print(f"  Note file not found: {note_path}")

    elif "pdac" in filename:
        # For pdac files: if coral_annotated_pdac_15_default.csv, note is 15.txt
        match = re.search(
            r'coral_annotated_pdac_(\d+)_default\.csv$', filename)
        if match:
            note_id = match.group(1)  # Get the number part
            note_path = os.path.join(DATA_PATHS["pdac"], f"{note_id}.txt")
            print(f"  PDAC file detected, looking for note: {note_id}.txt")
            if os.path.exists(note_path):
                print(f"  Found note file: {note_path}")
                return note_path
            print(f"  Note file not found: {note_path}")

    # If we couldn't match with specific patterns, try a more general approach
    print(f"  Using fallback method to find note for {filename}")
    for dataset_name, dataset_path in data_paths.items():
        print(f"  Searching in {dataset_path}")
        for note_file in glob.glob(os.path.join(dataset_path, "*.txt")):
            note_basename = os.path.basename(note_file)
            # Check if the note filename appears in the CSV filename
            if note_basename.split('.')[0] in filename:
                print(f"  Found note file using fallback: {note_file}")
                return note_file

    print(f"  Could not find matching note for {csv_file}")
    return None


def process_entity_positions():
    """Step 1: Process each model's CSV to add entity positions and agent type"""
    print("\n=== STEP 1: Processing Entity Positions ===")

    for model_name, model_path in MODEL_OUTPUTS.items():
        print(f"\nProcessing {model_name} outputs...")

        # Get all CSV files for this model
        csv_files = glob.glob(os.path.join(model_path, "*.csv"))

        for csv_file in csv_files:
            print(f"Processing {csv_file}...")

            # Find the corresponding note file
            note_file = find_matching_note(csv_file, DATA_PATHS)
            if not note_file:
                print(
                    f"Skipping {csv_file} - could not find matching note file")
                continue

            # Generate output filename
            output_filename = f"{os.path.splitext(os.path.basename(csv_file))[0]}_{model_name}_with_positions.csv"
            output_file = os.path.join(POSITION_OUTPUT_DIR, output_filename)

            # Run process_entity_index.py
            cmd = f"python {SCRIPTS_PATH}/process_entity_index.py --note_path '{note_file}' --csv_path '{csv_file}' --output_path '{output_file}' --agent_type {model_name} --use_sequential"
            run_command(cmd)


def merge_model_outputs():
    """Step 2: Merge the three model outputs for each note"""
    print("\n=== STEP 2: Merging Model Outputs ===")

    # Group files by note
    note_groups = {}

    position_files = glob.glob(os.path.join(
        POSITION_OUTPUT_DIR, "*_with_positions.csv"))

    for file in position_files:
        filename = os.path.basename(file)

        # Extract note identifier (remove model name and suffix)
        if "4CE" in filename:
            parts = filename.split('_')
            if len(parts) >= 4:
                note_id = '_'.join(parts[:3])  # 4CE_BCH_1
                if note_id not in note_groups:
                    note_groups[note_id] = []
                note_groups[note_id].append(file)
        elif "breastca" in filename or "pdac" in filename:
            parts = filename.split('_')
            if len(parts) >= 5:
                note_id = '_'.join(parts[:4])  # coral_annotated_breastca_21
                if note_id not in note_groups:
                    note_groups[note_id] = []
                note_groups[note_id].append(file)
        else:
            # Try a more general approach
            parts = filename.split('_')
            if len(parts) > 2:
                # Remove the last two parts (model_name and with_positions)
                note_id = '_'.join(parts[:-2])
                if note_id not in note_groups:
                    note_groups[note_id] = []
                note_groups[note_id].append(file)

    # Process each group
    for note_id, files in note_groups.items():
        if len(files) < 2:
            print(
                f"Skipping {note_id} - need at least 2 files to merge, found {len(files)}")
            continue

        print(f"Merging outputs for {note_id}...")
        output_file = os.path.join(MERGED_OUTPUT_DIR, f"{note_id}_merged.csv")

        # Start with first file
        merged_file = files[0]

        # Merge remaining files one by one
        for file in files[1:]:
            cmd = f"python {SCRIPTS_PATH}/merge_csv.py {merged_file} {file} {output_file}"
            run_command(cmd)
            merged_file = output_file


def filter_duplicates():
    """Step 3: Filter duplicates by term_index and remove position=-1 entries"""
    print("\n=== STEP 3: Filtering Duplicates ===")

    merged_files = glob.glob(os.path.join(MERGED_OUTPUT_DIR, "*_merged.csv"))

    for file in merged_files:
        output_file = os.path.join(
            FINAL_OUTPUT_DIR, f"{os.path.basename(file).replace('_merged.csv', '_for_review.csv')}")
        print(f"Processing {file}...")

        cmd = f"python {SCRIPTS_PATH}/merge_csv_by_term_index.py --file {file} --output {output_file}"
        run_command(cmd)


def main():
    parser = argparse.ArgumentParser(
        description='Process entity extraction results from multiple models.')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4], default=4,
                        help='Which step to run (1: process positions, 2: merge outputs, 3: filter duplicates, 4: all steps)')

    args = parser.parse_args()

    # Add scripts directory to path
    sys.path.append(SCRIPTS_PATH)

    if args.step == 1 or args.step == 4:
        process_entity_positions()

    if args.step == 2 or args.step == 4:
        merge_model_outputs()

    if args.step == 3 or args.step == 4:
        filter_duplicates()

    print("\nProcessing completed!")


if __name__ == "__main__":
    main()
