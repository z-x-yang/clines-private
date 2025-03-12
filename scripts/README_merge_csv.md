# CSV Merger for Term Index

This script merges rows in CSV files with the same `term_index`, prioritizing values based on the `agent_type` field.

## Merging Logic

The script follows these rules when merging rows with the same `term_index`:

1. For each column, if only one agent has a non-empty value, that value is kept regardless of the agent's priority.
2. If multiple agents have non-empty values for the same column, the value from the highest priority agent is used.
3. If no agent has a value for a column, it remains empty in the merged result.

## Priority Order

When multiple agents have values for the same field, values are prioritized in the following order:
1. annotation
2. gpt4o
3. llama
4. deepseek
5. genie
6. Other agent types (lowest priority)

## Usage

### Process all files in the default directory

```bash
python merge_csv_by_term_index.py
```

This will search for all CSV files with "for_review" in their names in the `outputs/review` directory and process them.

### Process all files in a specific directory

```bash
python merge_csv_by_term_index.py --directory path/to/directory
```

### Process a specific file

```bash
python merge_csv_by_term_index.py --file path/to/file.csv
```

### Process a specific file with a custom output path

```bash
python merge_csv_by_term_index.py --file path/to/file.csv --output path/to/output.csv
```

## Output

For each processed file, a new file will be created with "_merged" added to the filename. For example, `file_for_review.csv` will produce `file_for_review_merged.csv`.

The script will print:
- The number of files found
- The original and merged row counts for each file
- Any errors encountered during processing 