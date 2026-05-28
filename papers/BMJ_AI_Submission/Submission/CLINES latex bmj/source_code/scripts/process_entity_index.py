import pandas as pd
import re
from difflib import SequenceMatcher
import argparse


def find_entity_positions_sequential(note_text, df):
    print(f"Processing {len(df)} mentions sequentially...")

    # Create a mapping between normalized and original positions
    normalized_note = ''
    pos_mapping = {}
    orig_pos = 0
    norm_pos = 0

    # Build normalized text and position mapping
    for char in note_text:
        if not char.isspace():
            normalized_note += char
            pos_mapping[norm_pos] = orig_pos
            norm_pos += 1
        orig_pos += 1

    # Initialize position columns
    df['start_pos'] = -1
    df['end_pos'] = -1

    # Keep track of where we left off in the text
    current_position = 0

    # Process each mention sequentially
    for idx, row in df.iterrows():
        mention = str(row['mention'])
        print(f"Processing mention {idx+1}/{len(df)}: '{mention}'")

        if pd.isna(mention):
            print("  Skipped: mention is NA")
            continue

        # Normalize mention
        normalized_mention = ''.join(
            char for char in mention if not char.isspace())

        # First try searching from current_position
        mention_pos = normalized_note[current_position:].find(
            normalized_mention)

        # If not found, try searching from the beginning
        if mention_pos == -1:
            mention_pos = normalized_note.find(normalized_mention)
            if mention_pos != -1:
                print(
                    f"Found mention '{mention}' from beginning instead of sequential position")
        else:
            mention_pos += current_position  # Adjust position relative to the full text

        if mention_pos == -1:
            print("  Not found in text")
            continue

        try:
            start_pos = pos_mapping[mention_pos]

            # Find the end position by counting non-space characters
            mention_chars = 0
            end_pos = start_pos
            while mention_chars < len(normalized_mention) and end_pos < len(note_text):
                if not note_text[end_pos].isspace():
                    mention_chars += 1
                end_pos += 1

            # Verify the match
            found_text = note_text[start_pos:end_pos]
            normalized_found = ''.join(
                char for char in found_text if not char.isspace())
            if normalized_found.lower() == normalized_mention.lower():
                df.at[idx, 'start_pos'] = start_pos
                df.at[idx, 'end_pos'] = end_pos
                # Update current position to continue search after this mention
                current_position = mention_pos + len(normalized_mention)
            else:
                print(
                    f"Bad match: Found '{normalized_found}' instead of '{normalized_mention}'")

        except (KeyError, IndexError) as e:
            print(f"Error processing mention '{mention}': {str(e)}")
            continue

    return df


def find_entity_positions(note_text, df):
    print(f"Processing {len(df)} mentions with context...")

    # Create a mapping between normalized and original positions
    normalized_note = ''
    pos_mapping = {}
    orig_pos = 0
    norm_pos = 0

    # Build normalized text and position mapping
    for char in note_text:
        if not char.isspace():
            normalized_note += char
            pos_mapping[norm_pos] = orig_pos
            norm_pos += 1
        orig_pos += 1

    # 添加新的列来存储位置
    df['start_pos'] = -1
    df['end_pos'] = -1

    # 遍历每个entity
    for idx, row in df.iterrows():
        mention = str(row['mention'])
        context = str(row['context'])
        print(f"Processing mention {idx+1}/{len(df)}: '{mention}'")

        if pd.isna(mention) or pd.isna(context):
            print("  Skipped: mention or context is NA")
            continue

        # 清理context和mention
        normalized_context = ''.join(
            char for char in context if not char.isspace())
        normalized_mention = ''.join(
            char for char in mention if not char.isspace())

        # 先尝试精确匹配
        context_pos = normalized_note.find(normalized_context)

        found_through_context = False
        # 如果精确匹配失败，再尝试模糊匹配
        if context_pos == -1:
            print("  Using fuzzy matching for context...")
            best_ratio = 0
            best_pos = -1
            best_window = ''
            window_size = len(normalized_context)

            for i in range(len(normalized_note) - window_size + 1):
                window = normalized_note[i:i + window_size]
                ratio = SequenceMatcher(
                    None, window, normalized_context).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_pos = i
                    best_window = window

            # 如果匹配度太低，直接尝试查找mention
            if best_ratio < 0.5:
                mention_pos = normalized_note.find(normalized_mention)
                if mention_pos == -1:
                    continue

                try:
                    start_pos = pos_mapping[mention_pos]
                    mention_chars = 0
                    end_pos = start_pos
                    while mention_chars < len(normalized_mention) and end_pos < len(note_text):
                        if not note_text[end_pos].isspace():
                            mention_chars += 1
                        end_pos += 1

                    found_text = note_text[start_pos:end_pos]
                    normalized_found = ''.join(
                        char for char in found_text if not char.isspace())
                    if normalized_found.lower() == normalized_mention.lower():
                        df.at[idx, 'start_pos'] = start_pos
                        df.at[idx, 'end_pos'] = end_pos
                    continue
                except (KeyError, IndexError):
                    continue

            context_pos = best_pos
            normalized_context = best_window
            found_through_context = True

        # 在context中找到mention的位置
        mention_relative_pos = normalized_context.find(normalized_mention)

        if mention_relative_pos == -1:
            mention_pos = normalized_note.find(normalized_mention)
            if mention_pos == -1:
                continue

            try:
                start_pos = pos_mapping[mention_pos]
                mention_chars = 0
                end_pos = start_pos
                while mention_chars < len(normalized_mention) and end_pos < len(note_text):
                    if not note_text[end_pos].isspace():
                        mention_chars += 1
                    end_pos += 1

                found_text = note_text[start_pos:end_pos]
                normalized_found = ''.join(
                    char for char in found_text if not char.isspace())
                if normalized_found.lower() == normalized_mention.lower():
                    df.at[idx, 'start_pos'] = start_pos
                    df.at[idx, 'end_pos'] = end_pos
                continue
            except (KeyError, IndexError):
                continue

        try:
            start_pos = pos_mapping[context_pos + mention_relative_pos]

            # Find the end position by counting non-space characters
            mention_chars = 0
            end_pos = start_pos
            while mention_chars < len(normalized_mention) and end_pos < len(note_text):
                if not note_text[end_pos].isspace():
                    mention_chars += 1
                end_pos += 1

            # 验证找到的位置是否正确
            found_text = note_text[start_pos:end_pos]
            normalized_found = ''.join(
                char for char in found_text if not char.isspace())
            if normalized_found.lower() == normalized_mention.lower():
                df.at[idx, 'start_pos'] = start_pos
                df.at[idx, 'end_pos'] = end_pos
            else:
                mention_pos = normalized_note.find(normalized_mention)
                if mention_pos == -1:
                    continue

                try:
                    mention_pos = normalized_note.find(normalized_mention)
                    if mention_pos == -1:
                        continue

                    try:
                        start_pos = pos_mapping[mention_pos]
                        mention_chars = 0
                        end_pos = start_pos
                        while mention_chars < len(normalized_mention) and end_pos < len(note_text):
                            if not note_text[end_pos].isspace():
                                mention_chars += 1
                            end_pos += 1

                        found_text = note_text[start_pos:end_pos]
                        normalized_found = ''.join(
                            char for char in found_text if not char.isspace())
                        if normalized_found.lower() == normalized_mention.lower():
                            df.at[idx, 'start_pos'] = start_pos
                            df.at[idx, 'end_pos'] = end_pos
                        continue
                    except (KeyError, IndexError):
                        continue
                except (KeyError, IndexError):
                    continue

        except (KeyError, IndexError):
            print("Error:")
            print(normalized_context, normalized_mention)
            continue

    return df


def process_files(note_path, csv_path, output_path, agent_type, use_sequential=False):
    print(f"\nProcessing file: {note_path}")
    print(f"Reading note text and CSV data...")
    # 读取文件
    with open(note_path, 'r', encoding='utf-8') as f:
        note_text = f.read()

    df = pd.read_csv(csv_path)
    df['agent_type'] = agent_type

    print(f"Starting entity position finding...")
    print(f"Using {'sequential' if use_sequential else 'context-based'} method")
    # 根据 flag 选择处理方法
    if use_sequential:
        df = find_entity_positions_sequential(note_text, df)
    else:
        df = find_entity_positions(note_text, df)

    print(f"\nSaving results to: {output_path}")
    # 保存结果
    df.to_csv(output_path, index=False)

    # 打印统计信息
    total = len(df)
    found = len(df[df['start_pos'] != -1])
    print("\nResults Summary:")
    print(f"Total entities: {total}")
    print(f"Found positions: {found}")
    print(f"Success rate: {found/total*100:.2f}%")
    print("Processing complete!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Process clinical notes and find entity positions')
    parser.add_argument('--note_path', type=str,
                        default='/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt',
                        help='Path to the clinical note text file')
    parser.add_argument('--csv_path', type=str,
                        default='/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/coral_annotated_breastca_21_default.csv',
                        help='Path to the input CSV file containing entities')
    parser.add_argument('--output_path', type=str,
                        default='../outputs/coral_breastcancer_gpt4o_with_positions.csv',
                        help='Path to save the output CSV file')
    parser.add_argument('--agent_type', type=str,
                        default='gpt4o',
                        help='Type of agent used for extraction')
    parser.add_argument('--use_sequential', action='store_true',
                        help='Use sequential processing method')

    args = parser.parse_args()

    # Execute processing with parsed arguments
    process_files(args.note_path, args.csv_path, args.output_path,
                  args.agent_type, args.use_sequential)
