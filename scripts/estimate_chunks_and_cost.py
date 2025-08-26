import os
import sys
import json
import csv
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path

import tiktoken
import semchunk


DEFAULT_MODEL_ENCODING = 'gpt-4'
DEFAULT_CHUNK_SIZE = 1024
COST_PER_MERGED_CHUNK_USD = 0.4


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("estimate")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def find_txt_files(notes_dir: str, recursive: bool) -> list[str]:
    base = Path(notes_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Notes directory not found or not a directory: {notes_dir}")
    pattern = "**/*.txt" if recursive else "*.txt"
    return [str(p) for p in base.glob(pattern) if p.is_file()]


def read_text_file(path: str, use_fallback: bool = True) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        if not use_fallback:
            raise
        with open(path, 'r', encoding='latin-1') as f:
            return f.read()


def get_tokenizer(model_encoding: str):
    return tiktoken.encoding_for_model(model_encoding)


def initial_semantic_chunks(text: str, tokenizer, chunk_size: int) -> list[str]:
    chunker = semchunk.chunkerify(tokenizer, chunk_size)
    return list(chunker(text))


def merge_chunks_pipeline_style(items: list[str]) -> list[str]:
    merged: list[str] = [""]
    for item in items:
        if len(merged[-1]) < 200 or len(item) < 300:
            merged[-1] += item
        else:
            merged.append(item)
    # Normalize: if the only merged segment is empty string, treat as zero chunks
    if len(merged) == 1 and merged[0] == "":
        return []
    return merged


def count_tokens(text: str, tokenizer) -> int:
    if not text:
        return 0
    return len(tokenizer.encode(text))


def count_words_en(text: str) -> int:
    # Count sequences of English letters, optionally with internal apostrophes (e.g., don't)
    if not text:
        return 0
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


def estimate_note_stats(path: str, tokenizer, chunk_size: int) -> dict:
    text = read_text_file(path, use_fallback=True)
    num_chars = len(text)
    tokens_total = count_tokens(text, tokenizer)
    word_count = count_words_en(text)

    initial_items = initial_semantic_chunks(text, tokenizer, chunk_size)
    initial_chunk_count = len(initial_items)
    merged_items = merge_chunks_pipeline_style(initial_items)
    merged_chunk_tokens = [count_tokens(c, tokenizer) for c in merged_items]
    merged_chunk_count = len(merged_items)

    estimated_cost = merged_chunk_count * COST_PER_MERGED_CHUNK_USD

    return {
        'note_path': path,
        'num_chars': num_chars,
        'tokens_total': tokens_total,
        'word_count': word_count,
        'initial_chunk_count': initial_chunk_count,
        'merged_chunk_count': merged_chunk_count,
        'merged_chunk_tokens': merged_chunk_tokens,
        'estimated_cost': round(estimated_cost, 4),
    }


def write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ['note_path', 'num_chars', 'word_count', 'tokens_total', 'initial_chunk_count', 'merged_chunk_count', 'estimated_cost']
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fieldnames})


def main():
    parser = argparse.ArgumentParser(description='Estimate merged chunk counts, tokens, and costs for notes directory (.txt).')
    parser.add_argument('--notes_dir', type=str, required=True, help='Directory containing .txt notes')
    parser.add_argument('--chunk_size', type=int, default=DEFAULT_CHUNK_SIZE, help='Semantic chunk size for semchunk (tokens)')
    parser.add_argument('--recursive', action='store_true', help='Recurse into subdirectories for .txt files')
    parser.add_argument('--output_json', type=str, default=None, help='Path to output JSON report')
    parser.add_argument('--output_csv', type=str, default=None, help='Path to output CSV summary')
    parser.add_argument('--model_encoding', type=str, default=DEFAULT_MODEL_ENCODING, help='Model encoding name for tiktoken')

    args = parser.parse_args()
    logger = setup_logger()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_json = args.output_json or os.path.join('logs', f'estimation_{timestamp}.json')
    output_csv = args.output_csv or os.path.join('logs', f'estimation_{timestamp}.csv')

    try:
        files = find_txt_files(args.notes_dir, args.recursive)
    except Exception as e:
        logger.error(f"Failed to list txt files: {e}")
        return 1

    if not files:
        logger.warning("No .txt files found. Exiting.")
        write_json(output_json, {
            'total_notes': 0,
            'total_tokens': 0,
            'total_initial_chunks': 0,
            'total_merged_chunks': 0,
            'total_estimated_cost': 0.0,
            'skipped_notes': 0,
            'notes': []
        })
        write_csv(output_csv, [])
        logger.info(f"Wrote empty reports to {output_json} and {output_csv}")
        return 0

    try:
        tokenizer = get_tokenizer(args.model_encoding)
    except Exception as e:
        logger.error(f"Failed to initialize tokenizer for model '{args.model_encoding}': {e}")
        return 1

    total_tokens = 0
    total_initial_chunks = 0
    total_merged_chunks = 0
    total_estimated_cost = 0.0
    skipped_notes = 0
    total_words = 0

    rows: list[dict] = []

    for path in files:
        try:
            stats = estimate_note_stats(path, tokenizer, args.chunk_size)
            total_tokens += stats['tokens_total']
            total_words += stats['word_count']
            total_initial_chunks += stats['initial_chunk_count']
            total_merged_chunks += stats['merged_chunk_count']
            total_estimated_cost += stats['estimated_cost']
            rows.append(stats)
        except Exception as e:
            skipped_notes += 1
            logger.warning(f"Skipping file due to error: {path} -> {e}")

    denom = len(rows) if rows else 1
    summary = {
        'total_notes': len(rows),
        'total_tokens': total_tokens,
        'total_words': total_words,
        'total_initial_chunks': total_initial_chunks,
        'total_merged_chunks': total_merged_chunks,
        'total_estimated_cost': round(total_estimated_cost, 4),
        'skipped_notes': skipped_notes,
        'avg_words_per_note': round(total_words / denom, 2) if rows else 0.0,
        'avg_tokens_per_note': round(total_tokens / denom, 2) if rows else 0.0,
        'notes': rows,
    }

    write_json(output_json, summary)
    write_csv(output_csv, rows)
    logger.info(f"Wrote JSON report to {output_json}")
    logger.info(f"Wrote CSV summary to {output_csv}")
    logger.info(f"Notes: {summary['total_notes']}, Merged chunks: {summary['total_merged_chunks']}, Estimated cost: ${summary['total_estimated_cost']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


