#!/usr/bin/env python3
import os
import pandas as pd
import glob


def merge_csv_by_term_index(input_file, output_file=None):
    """
    Merge rows in a CSV file with the same term_index, prioritizing values based on agent_type.

    Args:
        input_file (str): Path to the input CSV file
        output_file (str, optional): Path to the output CSV file. If None, will use input_file with '_merged' suffix.

    Returns:
        str: Path to the output file
    """
    # Define the priority order for agent_type
    priority_order = ["annotation", "gpt4o", "llama", "deepseek", "genie"]

    # Read the CSV file
    print(f"Reading file: {input_file}")
    df = pd.read_csv(input_file)

    # Create a mapping of agent_type to priority value (lower is higher priority)
    priority_map = {agent: i for i, agent in enumerate(priority_order)}

    # Assign a priority value to each row (default to a high number for unknown agent types)
    df['priority'] = df['agent_type'].apply(
        lambda x: priority_map.get(x, len(priority_order)))

    # Get all column names except the ones we don't want to consider for grouping
    value_columns = [col for col in df.columns if col not in [
        'Unnamed: 0', 'term_index', 'priority', 'agent_type']]

    # Initialize the result DataFrame with unique term_index values
    result = pd.DataFrame({'term_index': df['term_index'].unique()})

    # For each term_index and each column, select the value based on our rules
    for term_idx in result['term_index']:
        # Get all rows for this term_index
        group = df[df['term_index'] == term_idx]

        # For each column, find the non-null values
        for col in value_columns:
            non_null_values = group[~group[col].isna()]

            if len(non_null_values) == 0:
                # No non-null values, leave as NaN
                result.loc[result['term_index'] == term_idx, col] = None
            elif len(non_null_values) == 1:
                # Only one non-null value, use it regardless of agent_type
                result.loc[result['term_index'] == term_idx,
                           col] = non_null_values[col].iloc[0]
            else:
                # Multiple non-null values, use priority to select
                # Sort by priority and take the first value
                result.loc[result['term_index'] == term_idx, col] = non_null_values.sort_values('priority')[
                    col].iloc[0]

        # Set the agent_type to the highest priority agent that contributed any value
        highest_priority_agent = group.sort_values(
            'priority')['agent_type'].iloc[0]
        result.loc[result['term_index'] == term_idx,
                   'agent_type'] = highest_priority_agent

    # Remove rows where start_pos=-1
    if 'start_pos' in result.columns:
        original_count = len(result)
        result = result[result['start_pos'] != -1]
        removed_count = original_count - len(result)
        print(f"Removed {removed_count} rows where start_pos=-1")

    # Determine the output file path if not provided
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_merged{ext}"

    # Save the result to a new CSV file
    print(f"Saving merged data to: {output_file}")
    result.to_csv(output_file, index=False)

    print(f"Original row count: {len(df)}")
    print(f"Merged row count: {len(result)}")

    return output_file


def process_all_for_review_files(directory='.'):
    """
    Find and process all CSV files with 'for_review' in their names in the given directory.

    Args:
        directory (str): Directory to search for files
    """
    # Find all CSV files with 'for_review' in their names
    pattern = os.path.join(directory, '**', '*for_review*.csv')
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"No files matching '*for_review*.csv' found in {directory}")
        return

    print(f"Found {len(files)} files to process:")
    for file in files:
        print(f"  - {file}")

    # Process each file
    for file in files:
        try:
            output_file = merge_csv_by_term_index(file)
            print(f"Successfully processed: {file} -> {output_file}")
            print("-" * 50)
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Merge CSV rows by term_index with priority based on agent_type.')
    parser.add_argument('--directory', '-d', default='outputs/review',
                        help='Directory to search for CSV files (default: outputs/review)')
    parser.add_argument('--file', '-f',
                        help='Process a specific CSV file instead of searching for files')
    parser.add_argument('--output', '-o',
                        help='Output file path (only used with --file)')

    args = parser.parse_args()

    if args.file:
        # Process a specific file
        merge_csv_by_term_index(args.file, args.output)
    else:
        # Process all matching files in the directory
        process_all_for_review_files(args.directory)
