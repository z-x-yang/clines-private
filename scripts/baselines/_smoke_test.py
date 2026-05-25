#!/usr/bin/env python3
"""Offline smoke test for single_call_baseline.py.

Verifies the non-API parts work end-to-end:
- chunking via semchunk + CLINES-style adjacent merging
- response parsing (strict: single + cot, contract enforcement)
- ParseError raised on contract violations, demjson3 fallback constrained
- span localization with used-span tracking (repeated mentions)
- output schema matches outputs/with_positions/*.csv exactly
- empty predictions DataFrame round-trips through CSV write/read
- process_note fails fast (raises) when a chunk exhausts parse retries

No OPENAIKEY needed; the API client is monkey-patched.

Usage:
    python scripts/baselines/_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

import single_call_baseline as scb


def test_chunking_clines_merging():
    text = "Patient presents with asthma and unspecified colitis. " * 200
    chunks = scb.chunk_note(text, chunk_size_tokens=128)
    raw_count = len(scb.semchunk.chunkerify(
        scb.tiktoken.encoding_for_model("gpt-4"), 128)(text))
    merged_count = len(chunks)
    assert merged_count <= raw_count, (raw_count, merged_count)
    for ct, offset in chunks:
        assert isinstance(ct, str) and ct.strip()
        assert isinstance(offset, int) and offset >= 0
    print(f"  test_chunking_clines_merging: PASS  (raw={raw_count} merged={merged_count})")


def test_strict_parser_single():
    raw = '[{"mention": "asthma", "code": "C0004096||asthma"}]'
    parsed = scb.parse_chunk_response(raw, "single")
    assert len(parsed) == 1 and parsed[0]["mention"] == "asthma"
    raw_fenced = '```json\n[{"a": 1}]\n```'
    try:
        scb.parse_chunk_response(raw_fenced, "single")
        raise AssertionError("expected ParseError on fenced output")
    except scb.ParseError:
        pass
    try:
        scb.parse_chunk_response("Here you go: [{\"a\":1}]", "single")
        raise AssertionError("expected ParseError on prose+json")
    except scb.ParseError:
        pass
    print("  test_strict_parser_single: PASS")


def test_strict_parser_cot():
    raw = '<reasoning>asthma reasoning</reasoning><answer>[{"mention":"asthma"}]</answer>'
    parsed = scb.parse_chunk_response(raw, "cot")
    assert len(parsed) == 1 and parsed[0]["mention"] == "asthma"
    try:
        scb.parse_chunk_response('[{"mention":"asthma"}]', "cot")
        raise AssertionError("expected ParseError on CoT-without-tags")
    except scb.ParseError:
        pass
    try:
        scb.parse_chunk_response("<answer>not a list</answer>", "cot")
        raise AssertionError("expected ParseError on non-array <answer>")
    except scb.ParseError:
        pass
    print("  test_strict_parser_cot: PASS")


def test_parser_demjson3_fallback():
    raw_loose = '[{"mention": "asthma"},]'  # trailing comma
    parsed = scb.parse_chunk_response(raw_loose, "single")
    assert len(parsed) == 1
    try:
        scb.parse_chunk_response('{"mention": "asthma"}', "single")
        raise AssertionError("expected ParseError on non-array")
    except scb.ParseError:
        pass
    print("  test_parser_demjson3_fallback: PASS")


def test_locate_span_repeats():
    note = "Patient has fever. Fever recurred. fever returned."
    used: set = set()
    s1, e1 = scb.locate_span_with_state(note, "fever", 0, len(note), used)
    s2, e2 = scb.locate_span_with_state(note, "Fever", 0, len(note), used)
    s3, e3 = scb.locate_span_with_state(note, "fever", 0, len(note), used)
    spans = sorted([(s1, e1), (s2, e2), (s3, e3)])
    assert len(set(spans)) == 3, spans
    s4, e4 = scb.locate_span_with_state(note, "fever", 0, len(note), used)
    assert (s4, e4) == (-1, -1)
    print(f"  test_locate_span_repeats: PASS  spans={spans}")


def test_locate_span_window_first():
    note = "early fever. " + ("x " * 200) + "late fever."
    used: set = set()
    late_start = note.rfind("late fever") + len("late ")
    s, e = scb.locate_span_with_state(note, "fever", late_start - 5, 20, used)
    assert s >= late_start - 5, (s, e, late_start)
    print(f"  test_locate_span_window_first: PASS  (s={s})")


def test_empty_predictions_df_roundtrip():
    df = scb._empty_predictions_df()
    assert list(df.columns) == scb.OUTPUT_COLUMNS
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    df.to_csv(path, index=True)
    back = pd.read_csv(path)
    expected = ["Unnamed: 0"] + scb.OUTPUT_COLUMNS
    assert list(back.columns) == expected, (back.columns.tolist(), expected)
    assert len(back) == 0
    Path(path).unlink()
    print("  test_empty_predictions_df_roundtrip: PASS")


def test_process_note_raises_on_persistent_parse_error():
    note = "Patient has asthma."
    bad = {"content": "this is not json", "prompt_tokens": 5,
           "completion_tokens": 1, "total_tokens": 6, "retries": 0,
           "wall_seconds": 0.01}
    original = scb.call_model
    scb.call_model = lambda *a, **kw: bad
    raised = False
    try:
        scb.process_note(
            None, "gpt-4o-1120", note, "X", "smoke", "tmp",
            mode="single", chunk_size_tokens=128, chunk_max_retries=1,
        )
    except scb.ParseError:
        raised = True
    finally:
        scb.call_model = original
    assert raised, "expected ParseError on persistent malformed output"
    print("  test_process_note_raises_on_persistent_parse_error: PASS")


def test_end_to_end_mock_full_schema():
    note = "Patient has asthma. Family history of diabetes. No fever today."
    canned = {
        "content": "<answer>" + json.dumps([
            {"mention": "asthma", "code": "C0004096||asthma",
             "assertion_status": "Present", "value": None, "unit": None,
             "begin_date": None, "end_date": None},
            {"mention": "diabetes", "code": "C0011847||diabetes",
             "assertion_status": "Notassociated", "value": None, "unit": None,
             "begin_date": None, "end_date": None},
            {"mention": "fever", "code": "C0015967||fever",
             "assertion_status": "Absent", "value": None, "unit": None,
             "begin_date": None, "end_date": None},
        ]) + "</answer>",
        "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
        "retries": 0, "wall_seconds": 0.05,
    }
    original = scb.call_model
    scb.call_model = lambda *a, **kw: canned
    try:
        df, result = scb.process_note(
            None, "gpt-4o-1120", note, "smoke1", "smoke", "gpt4o_cot",
            mode="cot", chunk_size_tokens=512, chunk_max_retries=1,
        )
    finally:
        scb.call_model = original
    assert result.num_chunks == 1
    assert result.total_api_calls == 1
    assert result.total_tokens == 150
    assert result.total_prompt_tokens == 100
    assert result.total_completion_tokens == 50
    assert result.entities_emitted == 3
    assert list(df.columns) == scb.OUTPUT_COLUMNS
    asthma_row = df[df["mention"] == "asthma"].iloc[0]
    assert asthma_row["start_pos"] == 12
    assert asthma_row["end_pos"] == 18
    assert asthma_row["agent_type"] == "gpt4o_cot"
    fever_row = df[df["mention"] == "fever"].iloc[0]
    assert fever_row["assertion_status"] == "Absent"
    print(f"  test_end_to_end_mock_full_schema: PASS  (df rows={len(df)})")


def test_end_to_end_real_note_chunking():
    note_path = Path(
        "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/"
        "LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt"
    )
    if not note_path.exists():
        print(f"  test_end_to_end_real_note_chunking: SKIP (missing {note_path})")
        return
    note = note_path.read_text(encoding="utf-8", errors="ignore")
    canned = {
        "content": "[]",
        "prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55,
        "retries": 0, "wall_seconds": 0.01,
    }
    original = scb.call_model
    scb.call_model = lambda *a, **kw: canned
    try:
        df, result = scb.process_note(
            None, "o3-mini-0131", note, "BCH_1", "4CE", "o3mini_sp",
            mode="single", chunk_size_tokens=768, chunk_max_retries=1,
        )
    finally:
        scb.call_model = original
    assert result.num_chunks >= 1
    assert result.total_api_calls == result.num_chunks
    assert result.entities_emitted == 0
    assert list(df.columns) == scb.OUTPUT_COLUMNS
    print(f"  test_end_to_end_real_note_chunking: PASS  (chunks={result.num_chunks})")


def test_csv_roundtrip_matches_existing():
    note = "Patient has asthma."
    canned = {
        "content": '[{"mention": "asthma", "code": "C0004096||asthma", '
                   '"assertion_status": "Present", "value": null, "unit": null, '
                   '"begin_date": null, "end_date": null}]',
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
        "retries": 0, "wall_seconds": 0.01,
    }
    original = scb.call_model
    scb.call_model = lambda *a, **kw: canned
    try:
        df, _ = scb.process_note(
            None, "gpt-4o-1120", note, "smoke", "smoke_ds", "tmp_agent",
            mode="single", chunk_size_tokens=128, chunk_max_retries=1,
        )
    finally:
        scb.call_model = original

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    df.to_csv(path, index=True)
    back = pd.read_csv(path)
    expected = ["Unnamed: 0"] + scb.OUTPUT_COLUMNS
    assert list(back.columns) == expected, (back.columns.tolist(), expected)
    existing_path = Path(
        "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/"
        "LLM_Info_Extract/language-into-clinical-data/outputs/with_positions/"
        "4CE_BCH_1_default_gpt4o_with_positions.csv"
    )
    if existing_path.exists():
        existing_cols = list(pd.read_csv(existing_path).columns)
        assert existing_cols == list(back.columns), (existing_cols, list(back.columns))
        print("  test_csv_roundtrip_matches_existing: PASS (matches existing schema)")
    else:
        print("  test_csv_roundtrip_matches_existing: PASS (own schema only)")
    Path(path).unlink()


def main():
    print("EXP-F smoke test (post-codex-review hardening):")
    test_chunking_clines_merging()
    test_strict_parser_single()
    test_strict_parser_cot()
    test_parser_demjson3_fallback()
    test_locate_span_repeats()
    test_locate_span_window_first()
    test_empty_predictions_df_roundtrip()
    test_process_note_raises_on_persistent_parse_error()
    test_end_to_end_mock_full_schema()
    test_end_to_end_real_note_chunking()
    test_csv_roundtrip_matches_existing()
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
