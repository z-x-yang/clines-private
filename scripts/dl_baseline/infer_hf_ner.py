#!/usr/bin/env python3
"""EXP-H DL baseline inference.

Run a HuggingFace AutoModelForTokenClassification NER model on a directory
of clinical note .txt files and emit predictions in two formats:

1. `<output_dir>/all_entities.csv` — raw per-entity output (one row per
   detected entity, with char_start/char_end matching the absolute offset in
   the source .txt file). Same schema as ClinicalNER/batch_clinical_ner.py
   for cross-comparability.

2. `<output_dir>/with_positions/<dataset>_<note>_default_<marker>_with_positions.csv`
   — same schema as CLINES `outputs/with_positions/*.csv` so it can feed
   directly into `scripts/eval_predictions.py --columns mention`.

Handles long documents via sliding-window inference at the token level
(stride = max_seq_length // 2) so we never truncate a clinical note silently
(fail-fast principle).

Required CLI args:
    --input_dir          dir of .txt files (one per note)
    --output_dir         where to write all_entities.csv + with_positions/
    --model_name         HF model id (e.g. samrawal/bert-base-uncased_clinical-ner)
    --marker             short tag used in the with_positions filename
                         (matches `--model_name` arg of eval_predictions.py)
    --dataset            dataset label that becomes the prefix of the
                         with_positions filename (e.g. 4CE,
                         coral_annotated_breastca, coral_annotated_pdac)
    --max_seq_length     model max seq length (default 512)
    --batch_size         note-level batching is 1; this controls the
                         number of windows fed to the model per forward pass
    --device             auto | cuda | cpu

Fail-fast contract:
  * model load failure -> SystemExit(2)
  * empty input dir   -> SystemExit(3)
  * any .txt file fails to be processed (uncaught exception) -> SystemExit(4),
    we do NOT silently skip; partial outputs would mislead downstream eval.
"""

import argparse
import csv
import json
import logging
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input_dir", required=True, type=Path)
    p.add_argument("--output_dir", required=True, type=Path)
    p.add_argument("--model_name", required=True, type=str)
    p.add_argument("--marker", required=True, type=str,
                   help="short tag used in with_positions filename, e.g. 'bertbase_clin'")
    p.add_argument("--dataset", required=True, type=str,
                   help="dataset prefix for with_positions filename, "
                        "e.g. '4CE' or 'coral_annotated_breastca'")
    p.add_argument("--gold_dir", type=Path, default=None,
                   help="if set, only run on notes whose <note_id>_updated.csv "
                        "exists under this directory (matches CLINES eval pairing)")
    p.add_argument("--max_seq_length", type=int, default=512)
    p.add_argument("--batch_size", type=int, default=8,
                   help="windows per forward pass; 1 note may produce >1 window")
    p.add_argument("--device", default="auto",
                   choices=["auto", "cuda", "cpu"])
    p.add_argument("--confidence_threshold", type=float, default=0.3,
                   help="argmax-softmax probability floor for a token to count "
                        "as part of an entity. 0.3 keeps recall high; set to 0 "
                        "to accept any non-O label.")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def setup_logger(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger("infer_hf_ner")


def pick_device(arg: str) -> torch.device:
    if arg == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("device=cuda requested but cuda not available")
        return torch.device("cuda")
    if arg == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model(model_name: str, device: torch.device):
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if not tokenizer.is_fast:
        raise SystemExit(
            f"tokenizer for {model_name} is not 'fast'; we rely on offset_mapping. abort.")
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    model.eval()
    model.to(device)
    id2label = model.config.id2label
    return tokenizer, model, id2label


def windows_for_note(text: str, tokenizer, max_seq_length: int):
    """Tokenize text once, return list of (offsets_window, input_ids_window).

    Uses fast-tokenizer's overflow + offset_mapping to keep absolute-char
    positions. Stride = max_seq_length // 4 -> 25% overlap (enough to avoid
    losing entities at window boundaries while keeping redundant compute
    bounded). Special tokens [CLS]/[SEP]/[PAD] are kept in input_ids for the
    model but skipped at decode time by their (0,0) offset signature.
    """
    enc = tokenizer(
        text,
        return_offsets_mapping=True,
        return_overflowing_tokens=True,
        truncation=True,
        max_length=max_seq_length,
        stride=max_seq_length // 4,  # 25% overlap is enough; cuts redundant compute
        padding=False,
    )
    windows = []
    for i in range(len(enc["input_ids"])):
        windows.append({
            "input_ids": enc["input_ids"][i],
            "attention_mask": enc["attention_mask"][i],
            "offsets": enc["offset_mapping"][i],
        })
    return windows


def softmax_predict(model, tokenizer, batch_windows, device, id2label):
    """Run forward on a list of windows (already tokenized), return list of
    (offsets, predicted_labels, predicted_probs) tuples in same order."""
    import torch.nn.functional as F

    pad_id = tokenizer.pad_token_id
    max_len = max(len(w["input_ids"]) for w in batch_windows)
    input_ids = torch.full((len(batch_windows), max_len), pad_id, dtype=torch.long)
    attention_mask = torch.zeros((len(batch_windows), max_len), dtype=torch.long)
    for i, w in enumerate(batch_windows):
        L = len(w["input_ids"])
        input_ids[i, :L] = torch.tensor(w["input_ids"], dtype=torch.long)
        attention_mask[i, :L] = torch.tensor(w["attention_mask"], dtype=torch.long)
    input_ids = input_ids.to(device)
    attention_mask = attention_mask.to(device)
    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
    probs = F.softmax(logits, dim=-1)
    pred_ids = probs.argmax(dim=-1)
    pred_probs = probs.gather(-1, pred_ids.unsqueeze(-1)).squeeze(-1)
    out = []
    for i, w in enumerate(batch_windows):
        L = len(w["input_ids"])
        labels_i = [id2label[int(x)] for x in pred_ids[i, :L].cpu().tolist()]
        probs_i = pred_probs[i, :L].cpu().tolist()
        out.append((w["offsets"], labels_i, probs_i))
    return out


def decode_entities(windows_pred, original_text: str, threshold: float):
    """Decode BIO tags into entities with absolute character offsets in
    the original text. Across overlapping windows, we deduplicate by
    (start_char, end_char, label).

    Returns list of dicts: {text, label, char_start, char_end, confidence}.
    """
    seen = set()
    entities = []

    for offsets, labels, probs in windows_pred:
        # walk through tokens; merge B-X (I-X)* into single entity
        i = 0
        while i < len(labels):
            tok_label = labels[i]
            s, e = offsets[i]
            # special tokens have (0,0) offset
            if s == 0 and e == 0:
                i += 1
                continue
            if tok_label == "O":
                i += 1
                continue
            # accept B-X start; also accept stray I-X start (some models do it)
            if tok_label.startswith(("B-", "I-")):
                ent_class = tok_label.split("-", 1)[1]
                ent_start, ent_end = s, e
                min_prob = probs[i]
                j = i + 1
                # consume continuation I-<same_class> tokens
                while j < len(labels):
                    nxt = labels[j]
                    ns, ne = offsets[j]
                    if ns == 0 and ne == 0:
                        j += 1
                        continue
                    if nxt.startswith("I-") and nxt.split("-", 1)[1] == ent_class:
                        ent_end = ne
                        min_prob = min(min_prob, probs[j])
                        j += 1
                    else:
                        break
                if min_prob >= threshold:
                    surface = original_text[ent_start:ent_end]
                    key = (ent_start, ent_end, ent_class)
                    if key not in seen:
                        seen.add(key)
                        entities.append({
                            "text": surface,
                            "label": ent_class,
                            "char_start": ent_start,
                            "char_end": ent_end,
                            "confidence": float(min_prob),
                        })
                i = j
            else:
                i += 1

    # sort by start_char
    entities.sort(key=lambda x: (x["char_start"], x["char_end"]))
    return entities


def write_all_entities_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["filename", "entity_text", "entity_type",
               "char_start", "char_end", "confidence", "entity_length"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_with_positions_csv(path: Path, dataset: str, note_id: str, marker: str,
                             entities, key_prefix: str):
    """Emit a CLINES-compatible with_positions CSV. Schema matches
    `outputs/with_positions/*.csv` minimally enough for
    `eval_predictions.py --columns mention` to score.

    Columns we populate: term_index, key, mention, type, start_pos, end_pos,
    agent_type. The rest are left blank (eval ignores them for `--columns mention`).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "term_index", "key", "admission_date", "discharge_date", "gender",
        "death_date", "birth_date", "race", "ethnicity", "zip_code",
        "mention", "context", "code", "type", "assertion_status",
        "body_location", "body_location_code", "value", "unit", "infer",
        "freq", "route", "note", "related", "begin_date", "end_date",
        "agent_type", "start_pos", "end_pos",
    ]
    key_val = f"{key_prefix}_{note_id}"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for idx, ent in enumerate(entities, start=1):
            row = {h: "" for h in headers}
            row.update({
                "term_index": idx,
                "key": key_val,
                "mention": ent["text"].strip(),
                "type": ent["label"],
                "agent_type": marker,
                "start_pos": ent["char_start"],
                "end_pos": ent["char_end"],
            })
            w.writerow(row)


def gold_note_ids(gold_dir: Path):
    return {p.name.replace("_updated.csv", "")
            for p in gold_dir.glob("*_updated.csv")}


def dataset_key_prefix(dataset: str) -> str:
    """Map the dataset dir name to the prefix used in the `key` column of
    CLINES with_positions files.

    Observed values:
      - 4CE                       -> '4ce'
      - coral_annotated_breastca  -> 'coral_breastca'
      - coral_annotated_pdac      -> 'coral_pdac'
    The eval doesn't use the key column for matching; we keep the same
    convention for safety/searchability.
    """
    if dataset == "4CE":
        return "4ce"
    if dataset == "coral_annotated_breastca":
        return "coral_breastca"
    if dataset == "coral_annotated_pdac":
        return "coral_pdac"
    return dataset.lower()


def main():
    args = parse_args()
    logger = setup_logger(args.log_level)
    logger.info("args=%s", vars(args))

    if not args.input_dir.is_dir():
        raise SystemExit(f"input_dir not a directory: {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "with_positions").mkdir(exist_ok=True)

    txt_files = sorted(args.input_dir.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"no .txt files under {args.input_dir}")

    if args.gold_dir is not None:
        gold_ids = gold_note_ids(args.gold_dir)
        if not gold_ids:
            raise SystemExit(f"no *_updated.csv files under gold_dir={args.gold_dir}")
        txt_files = [t for t in txt_files if t.stem in gold_ids]
        if not txt_files:
            raise SystemExit(
                f"none of the {args.input_dir} .txt files match gold note IDs "
                f"in {args.gold_dir}")
        logger.info("filtered to %d notes that have matching gold annotations",
                    len(txt_files))

    device = pick_device(args.device)
    logger.info("device=%s", device)
    tokenizer, model, id2label = load_model(args.model_name, device)
    logger.info("loaded model %s; num_labels=%d; sample labels=%s",
                args.model_name, len(id2label), list(id2label.values())[:8])

    key_prefix = dataset_key_prefix(args.dataset)

    all_rows = []
    summary = {
        "total_files": len(txt_files),
        "processed_files": 0,
        "failed_files": 0,
        "total_entities": 0,
        "model_name": args.model_name,
        "marker": args.marker,
        "dataset": args.dataset,
        "max_seq_length": args.max_seq_length,
        "confidence_threshold": args.confidence_threshold,
    }

    for txt in txt_files:
        try:
            text = txt.read_text(encoding="utf-8")
            windows = windows_for_note(text, tokenizer, args.max_seq_length)
            if not windows:
                raise RuntimeError(f"no windows produced for {txt.name}")

            preds = []
            for batch_start in range(0, len(windows), args.batch_size):
                batch = windows[batch_start:batch_start + args.batch_size]
                preds.extend(softmax_predict(model, tokenizer, batch, device, id2label))

            entities = decode_entities(preds, text, args.confidence_threshold)

            for ent in entities:
                all_rows.append({
                    "filename": txt.name,
                    "entity_text": ent["text"].strip(),
                    "entity_type": ent["label"],
                    "char_start": ent["char_start"],
                    "char_end": ent["char_end"],
                    "confidence": ent["confidence"],
                    "entity_length": len(ent["text"].strip()),
                })

            wp_name = f"{args.dataset}_{txt.stem}_default_{args.marker}_with_positions.csv"
            write_with_positions_csv(
                args.output_dir / "with_positions" / wp_name,
                args.dataset, txt.stem, args.marker, entities, key_prefix,
            )

            summary["processed_files"] += 1
            summary["total_entities"] += len(entities)
            logger.info("%s -> %d entities in %d windows", txt.name, len(entities), len(windows))
        except Exception as exc:
            summary["failed_files"] += 1
            logger.exception("FAILED on %s", txt)
            raise SystemExit(f"abort: failed to process {txt}: {exc}") from exc

    write_all_entities_csv(args.output_dir / "all_entities.csv", all_rows)
    with open(args.output_dir / "processing_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("done. summary=%s", summary)


if __name__ == "__main__":
    main()
