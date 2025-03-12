#!/bin/bash

# Set script to exit immediately if any command fails
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define the input file path
INPUT_FILE="outputs/review/coral_breastcancer_21_for_review.csv"
OUTPUT_FILE="outputs/review/coral_breastcancer_21_merged.csv"

# Check if the input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${YELLOW}Error: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

# Print information about the process
echo -e "${GREEN}Processing file: $INPUT_FILE${NC}"
echo -e "${GREEN}Output will be saved to: $OUTPUT_FILE${NC}"

# Run the Python script to process the file
echo -e "${GREEN}Running merge script...${NC}"
python scripts/merge_csv_by_term_index.py --file "$INPUT_FILE" --output "$OUTPUT_FILE"

# Check if the output file was created successfully
if [ -f "$OUTPUT_FILE" ]; then
    echo -e "${GREEN}Processing completed successfully!${NC}"
    echo -e "${GREEN}Output file: $OUTPUT_FILE${NC}"
    
    # Count the number of rows in the input and output files (excluding header)
    INPUT_ROWS=$(tail -n +2 "$INPUT_FILE" | wc -l)
    OUTPUT_ROWS=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
    
    echo -e "${GREEN}Input file rows: $INPUT_ROWS${NC}"
    echo -e "${GREEN}Output file rows: $OUTPUT_ROWS${NC}"
    echo -e "${GREEN}Rows reduced by: $(($INPUT_ROWS - $OUTPUT_ROWS))${NC}"
else
    echo -e "${YELLOW}Error: Output file was not created.${NC}"
    exit 1
fi

echo -e "${GREEN}Done!${NC}" 