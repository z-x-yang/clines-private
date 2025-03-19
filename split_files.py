#!/usr/bin/env python3
import os
import shutil
import csv
import pandas as pd
from collections import defaultdict

# Define paths
input_dir = 'outputs/final2'
output_base_dir = 'outputs/split'
txt_dirs = {
    '4CE': 'data/4CE',
    'coral_breastca': 'data/coral_annotated_breastca',
    'coral_pdac': 'data/coral_annotated_pdac'
}

# Create output directories if they don't exist
for i in range(1, 5):
    part_dir = os.path.join(output_base_dir, f'part{i}')
    os.makedirs(os.path.join(part_dir, '4CE'), exist_ok=True)
    os.makedirs(os.path.join(part_dir, 'coral'), exist_ok=True)

# Get all CSV files and count their rows
csv_files = []
for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        filepath = os.path.join(input_dir, filename)

        # Count rows in the CSV file
        with open(filepath, 'r', encoding='utf-8') as f:
            row_count = sum(1 for _ in f) - 1  # Subtract 1 for header

        # Initialize source and source_detail
        source = 'unknown'
        source_detail = 'unknown'

        # Determine source (4CE or coral)
        if filename.startswith('4CE'):
            source = '4CE'
            source_detail = '4CE'
        elif 'coral' in filename:
            if 'breastca' in filename:
                source_detail = 'coral_breastca'
            else:
                source_detail = 'coral_pdac'
            source = 'coral'

        csv_files.append({
            'filename': filename,
            'filepath': filepath,
            'row_count': row_count,
            'source': source,
            'source_detail': source_detail
        })

# Sort files by row count in descending order
csv_files.sort(key=lambda x: x['row_count'], reverse=True)

# Initialize 4 parts with 0 rows each
parts = [[] for _ in range(4)]
part_rows = [0] * 4

# Distribute files using a greedy approach (assign to the part with the fewest rows)
for file_info in csv_files:
    # Find the part with the fewest rows
    min_rows_idx = part_rows.index(min(part_rows))

    # Add the file to that part
    parts[min_rows_idx].append(file_info)
    part_rows[min_rows_idx] += file_info['row_count']

# Copy files to their respective directories and collect statistics
stats = []
for part_idx, part_files in enumerate(parts):
    part_num = part_idx + 1
    part_dir = os.path.join(output_base_dir, f'part{part_num}')

    # Initialize statistics for this part
    part_stats = {
        'part': part_num,
        'total_csv_count': len(part_files),
        'total_row_count': part_rows[part_idx],
        '4CE_csv_count': 0,
        '4CE_row_count': 0,
        'coral_csv_count': 0,
        'coral_row_count': 0
    }

    # Process each file in this part
    for file_info in part_files:
        filename = file_info['filename']
        source = file_info['source']
        row_count = file_info['row_count']

        # Update statistics
        if source == '4CE':
            part_stats['4CE_csv_count'] += 1
            part_stats['4CE_row_count'] += row_count

            # Copy CSV file
            dest_dir = os.path.join(part_dir, '4CE')
            shutil.copy2(file_info['filepath'],
                         os.path.join(dest_dir, filename))

            # Find and copy corresponding TXT file
            txt_filename = None
            if 'report' in filename:
                # For report files: 4CE_report01_default_for_review.csv -> report01.txt
                report_num = filename.split('_')[1]
                txt_filename = f"{report_num}.txt"
            elif 'UPMC' in filename:
                # For UPMC files: 4CE_UPMC_Note1_for_review.csv -> UPMC_Note1.txt
                note_id = filename.split('_')[2]
                txt_filename = f"UPMC_{note_id}.txt"
            elif any(site in filename for site in ['BCH', 'KUMC', 'ICSM', 'COL']):
                # For site files: 4CE_BCH_1_for_review.csv -> BCH_1.txt
                site = filename.split('_')[1]
                num = filename.split('_')[2]
                txt_filename = f"{site}_{num}.txt"
            else:
                # For hash files: 4CE_d18395bd05b9c997c1aceffdbcf8e5e3c_default_for_review.csv -> d18395bd05b9c997c1aceffdbcf8e5e3c.txt
                hash_id = filename.split('_')[1]
                txt_filename = f"{hash_id}.txt"

            if txt_filename and os.path.exists(os.path.join(txt_dirs['4CE'], txt_filename)):
                shutil.copy2(
                    os.path.join(txt_dirs['4CE'], txt_filename),
                    os.path.join(dest_dir, txt_filename)
                )

        elif source == 'coral':
            part_stats['coral_csv_count'] += 1
            part_stats['coral_row_count'] += row_count

            # Copy CSV file
            dest_dir = os.path.join(part_dir, 'coral')
            shutil.copy2(file_info['filepath'],
                         os.path.join(dest_dir, filename))

            # Find and copy corresponding TXT file
            source_detail = file_info['source_detail']
            txt_filename = None
            txt_dir = None

            if 'breastca' in filename:
                # For breast cancer files: coral_annotated_breastca_32_for_review.csv -> 32.txt
                num = filename.split('_')[3]
                txt_filename = f"{num}.txt"
                txt_dir = txt_dirs['coral_breastca']
            elif 'pdac' in filename:
                # For pdac files: coral_annotated_pdac_15_for_review.csv -> 15.txt
                num = filename.split('_')[3]
                txt_filename = f"{num}.txt"
                txt_dir = txt_dirs['coral_pdac']

            if txt_filename and txt_dir and os.path.exists(os.path.join(txt_dir, txt_filename)):
                shutil.copy2(
                    os.path.join(txt_dir, txt_filename),
                    os.path.join(dest_dir, txt_filename)
                )

    stats.append(part_stats)

# Print statistics
print("\nStatistics for each part:")
print("=" * 80)
for part_stat in stats:
    print(f"Part {part_stat['part']}:")
    print(f"  Total CSV files: {part_stat['total_csv_count']}")
    print(f"  Total rows: {part_stat['total_row_count']}")
    print(
        f"  4CE CSV files: {part_stat['4CE_csv_count']} (rows: {part_stat['4CE_row_count']})")
    print(
        f"  Coral CSV files: {part_stat['coral_csv_count']} (rows: {part_stat['coral_row_count']})")
    print("-" * 80)

print("\nSummary:")
print(f"Total CSV files: {sum(stat['total_csv_count'] for stat in stats)}")
print(f"Total rows: {sum(stat['total_row_count'] for stat in stats)}")
print(
    f"Files have been split into 4 parts in the directory: {output_base_dir}")
