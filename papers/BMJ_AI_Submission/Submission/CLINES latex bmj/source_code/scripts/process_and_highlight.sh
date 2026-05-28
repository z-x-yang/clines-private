CSV_PATH="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/Test_example_jak2_note_default.csv"
EHR_TXT_PATH="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/Test/example_jak2_note.txt"
AGENT_TYPE="gpt4o"
OUTPUT_CSV_PATH="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/Test_example_jak2_note_with_positions.csv"
OUTPUT_HTML_PATH="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/notes/example_jak2_note.html"

python process_entity_index.py --csv_path $CSV_PATH --note_path $EHR_TXT_PATH --output_path $OUTPUT_CSV_PATH --agent_type $AGENT_TYPE
python highlight_term.py --merged_csv $OUTPUT_CSV_PATH --ehr_txt $EHR_TXT_PATH --output_html $OUTPUT_HTML_PATH
