import os
import pandas as pd
import torch
from model import Retriever
import json
from datetime import datetime


def load_csv_files(original_dir, reviewed_dir):
    """Load and pair original and reviewed CSV files."""
    file_pairs = []

    # Get all subdirectories in reviewed_dir
    reviewed_datasets = [d for d in os.listdir(
        reviewed_dir) if os.path.isdir(os.path.join(reviewed_dir, d))]

    print(f"\nFound {len(reviewed_datasets)} datasets in {reviewed_dir}")

    for dataset in reviewed_datasets:
        reviewed_dataset_dir = os.path.join(reviewed_dir, dataset)
        reviewed_files = [f for f in os.listdir(
            reviewed_dataset_dir) if f.endswith('_reviewed.csv')]

        print(f"\nProcessing dataset: {dataset}")
        print(f"Found {len(reviewed_files)} reviewed files")

        for reviewed_file in reviewed_files:
            # Extract the number from reviewed file (e.g., "21" from "21_reviewed.csv")
            file_number = reviewed_file.split('_')[0]

            # Construct original file name (e.g., "coral_annotated_breastca_21_for_review.csv")
            original_file = os.path.join(
                original_dir, f"{dataset}_{file_number}_for_review.csv")

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


def compare_entities(original_df, reviewed_df):
    """Compare entities between original and reviewed files based on positions."""
    changes = []
    new_entities = []

    # Create position-based index for original entities
    original_positions = {}
    for _, row in original_df.iterrows():
        if pd.notna(row.get('start_pos')) and pd.notna(row.get('end_pos')):
            pos_key = (row['start_pos'], row['end_pos'])
            original_positions[pos_key] = row

    # Compare reviewed entities with original
    for _, reviewed_row in reviewed_df.iterrows():
        if pd.notna(reviewed_row.get('start_pos')) and pd.notna(reviewed_row.get('end_pos')):
            pos_key = (reviewed_row['start_pos'], reviewed_row['end_pos'])

            if pos_key in original_positions:
                # Compare codes for matching positions
                original_row = original_positions[pos_key]
                if original_row['code'] != reviewed_row['code']:
                    changes.append({
                        'position': pos_key,
                        'mention': reviewed_row['mention'],
                        'original_code': original_row['code'],
                        'reviewed_code': reviewed_row['code']
                    })
            else:
                # New entity found
                new_entities.append({
                    'position': pos_key,
                    'mention': reviewed_row['mention'],
                    'code': reviewed_row['code']
                })

    return changes, new_entities


def get_umls_info(mentions, retriever):
    """Get UMLS CUI codes and standard terms for a list of mentions."""
    # Use retriever to get UMLS codes
    linking_results = retriever.embedding_retrieval_all(mentions, batch_size=4)

    umls_info = []
    for mention, result in zip(mentions, linking_results):
        # Parse the JSON string result
        mapped_code = json.loads(result)
        cui = list(mapped_code.keys())[0]
        standard_term = mapped_code[cui][0]
        semantic_type = mapped_code[cui][1]

        umls_info.append({
            'mention': mention,
            'cui': cui,
            'standard_term': standard_term,
            'semantic_type': semantic_type
        })

    return umls_info


def update_csv_with_umls(reviewed_df, changes, new_entities, retriever):
    """Update reviewed CSV with UMLS information only for changed and new entities."""
    # Get mentions from changes and new entities
    changed_mentions = [c['mention'] for c in changes]
    new_mentions = [e['mention'] for e in new_entities]
    all_mentions = changed_mentions + new_mentions

    if not all_mentions:
        return reviewed_df

    # Get UMLS info for all mentions
    umls_info = get_umls_info(all_mentions, retriever)

    # Create a mapping from mention to UMLS info
    umls_map = {info['mention']: info for info in umls_info}

    # Update code and type columns only for changed and new entities
    for idx, row in reviewed_df.iterrows():
        mention = row['mention']
        if mention in umls_map:
            info = umls_map[mention]
            reviewed_df.at[idx,
                           'code'] = f"{info['cui']}||{info['standard_term']}"
            reviewed_df.at[idx, 'type'] = info['semantic_type']

    return reviewed_df


def main():
    print(
        f"\nStarting comparison at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize UMLS retriever with CPU
    print("\nInitializing UMLS retriever...")
    use_gpu = False
    retriever = Retriever(
        'cambridgeltl/SapBERT-from-PubMedBERT-fulltext', use_gpu=use_gpu, use_faiss_gpu=use_gpu)
    retriever.load_dictionary_all('./umls_dictionary.txt')
    retriever.embed_dictionary()
    retriever.faiss_setup()
    print("✓ UMLS retriever initialized (CPU mode)")

    # Directories containing CSV files
    original_dir = 'outputs/final'
    reviewed_dir = 'outputs/reviewed'
    output_dir = 'outputs/reviewed_updated'  # New directory for updated files

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get file pairs
    file_pairs = load_csv_files(original_dir, reviewed_dir)

    if not file_pairs:
        print("\nNo matching file pairs found. Exiting.")
        return

    # Statistics for summary
    total_files = len(file_pairs)
    total_changes = 0
    total_new = 0
    processed_files = 0

    # Process each file pair
    for original_file, reviewed_file in file_pairs:
        processed_files += 1
        print(f"\nProcessing file pair [{processed_files}/{total_files}]:")
        print(f"Original: {original_file}")
        print(f"Reviewed: {reviewed_file}")

        # Load CSVs
        original_df = pd.read_csv(original_file)
        reviewed_df = pd.read_csv(reviewed_file)
        print(
            f"✓ Loaded {len(original_df)} original and {len(reviewed_df)} reviewed entities")

        # Compare entities
        changes, new_entities = compare_entities(original_df, reviewed_df)
        total_changes += len(changes)
        total_new += len(new_entities)

        # Update reviewed CSV with UMLS information only for changes and new entities
        if changes or new_entities:
            print(
                "\nUpdating reviewed CSV with UMLS information for changes and new entities...")
            updated_df = update_csv_with_umls(
                reviewed_df, changes, new_entities, retriever)

            # Get the relative path from reviewed_dir to maintain directory structure
            rel_path = os.path.relpath(reviewed_file, reviewed_dir)
            # Get the directory part of the path
            rel_dir = os.path.dirname(rel_path)
            # Create the output subdirectory if it doesn't exist
            output_subdir = os.path.join(output_dir, rel_dir)
            os.makedirs(output_subdir, exist_ok=True)

            # Save updated CSV maintaining the directory structure
            output_file = os.path.join(output_subdir, os.path.basename(
                reviewed_file).replace('_reviewed.csv', '_updated.csv'))
            updated_df.to_csv(output_file, index=False)
            print(f"✓ Saved updated CSV to: {output_file}")

        # Get UMLS info for changes and new entities
        if changes:
            print(f"\nFound {len(changes)} changed entities:")
            changed_mentions = [c['mention'] for c in changes]
            changed_umls = get_umls_info(changed_mentions, retriever)

            for change, umls in zip(changes, changed_umls):
                print(f"\nMention: {change['mention']}")
                print(f"Position: {change['position']}")
                print(f"Original code: {change['original_code']}")
                print(f"Reviewed code: {change['reviewed_code']}")
                print(f"UMLS CUI: {umls['cui']}")
                print(f"Standard term: {umls['standard_term']}")
                print(f"Semantic type: {umls['semantic_type']}")

        if new_entities:
            print(f"\nFound {len(new_entities)} new entities:")
            new_mentions = [e['mention'] for e in new_entities]
            new_umls = get_umls_info(new_mentions, retriever)

            for entity, umls in zip(new_entities, new_umls):
                print(f"\nMention: {entity['mention']}")
                print(f"Position: {entity['position']}")
                print(f"Code: {entity['code']}")
                print(f"UMLS CUI: {umls['cui']}")
                print(f"Standard term: {umls['standard_term']}")
                print(f"Semantic type: {umls['semantic_type']}")

    # Print summary
    print("\n" + "="*50)
    print("PROCESSING SUMMARY")
    print("="*50)
    print(f"Total files processed: {total_files}")
    print(f"Total changed entities: {total_changes}")
    print(f"Total new entities: {total_new}")
    print(f"Average changes per file: {total_changes/total_files:.2f}")
    print(f"Average new entities per file: {total_new/total_files:.2f}")
    print(f"Updated files saved to: {output_dir}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)


if __name__ == '__main__':
    main()
