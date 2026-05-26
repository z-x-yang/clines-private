"""EXP-A4 extension: compute F1-based IAA + per-note CSV + top-3-per-dataset pooled.

Extends post_guideline_simulation.py by:
  - Adding F1 = 2*|A∩B| / (|A|+|B|) (Dice / symmetric mention F1) to per-note + pooled
  - Emitting per_note.csv for downstream selection
  - Computing pooled metrics for top-3-per-dataset (selected by κ_post)
"""
import pandas as pd
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

ROOT = Path("/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data")
EXP_A = ROOT / ".claude/worktrees/agent-a2f527fc03ba78605/runs/EXP-A/_unzipped"
GOLD = ROOT / "outputs/reviewed_updated2"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "runs" / "EXP-A4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = [
    ("4CE","KUMC_7",EXP_A/"for_mo/For_Mo_IAA_cross_annotation/4CE/4CE_KUMC_7_for_review.csv",GOLD/"4CE/KUMC_7_updated.csv",EXP_A/"from_mo/Mo/4CE/KUMC_7_reviewed.csv","Enci","Mo"),
    ("4CE","report03",EXP_A/"for_mo/For_Mo_IAA_cross_annotation/4CE/4CE_report03_default_for_review.csv",GOLD/"4CE/report03_updated.csv",EXP_A/"from_mo/Mo/4CE/report03_reviewed.csv","Enci","Mo"),
    ("4CE","report04",EXP_A/"for_mo/For_Mo_IAA_cross_annotation/4CE/4CE_report04_default_for_review.csv",GOLD/"4CE/report04_updated.csv",EXP_A/"from_mo/Mo/4CE/report04_reviewed.csv","Enci","Mo"),
    ("CORAL","pdac_7",EXP_A/"for_mo/For_Mo_IAA_cross_annotation/Coral/coral_annotated_pdac_7_for_review.csv",GOLD/"coral_annotated_pdac/7_updated.csv",EXP_A/"from_mo/Mo/Coral/7_reviewed.csv","Enci","Mo"),
    ("CORAL","pdac_17",EXP_A/"for_mo/For_Mo_IAA_cross_annotation/Coral/coral_annotated_pdac_17_for_review.csv",GOLD/"coral_annotated_pdac/17_updated.csv",EXP_A/"from_mo/Mo/Coral/17_reviewed.csv","Enci","Mo"),
    ("4CE","BCH_6",EXP_A/"for_enci/For_Enci_IAA_cross_annotation/4CE/4CE_BCH_6_for_review.csv",GOLD/"4CE/BCH_6_updated.csv",EXP_A/"from_enci/To_Zongxin_Enci_add_annotation/4CE/BCH_6_reviewed.csv","Mo","Enci"),
    ("4CE","KUMC_1",EXP_A/"for_enci/For_Enci_IAA_cross_annotation/4CE/4CE_KUMC_1_for_review.csv",GOLD/"4CE/KUMC_1_updated.csv",EXP_A/"from_enci/To_Zongxin_Enci_add_annotation/4CE/KUMC_1_reviewed.csv","Mo","Enci"),
    ("CORAL","pdac_14",EXP_A/"for_enci/For_Enci_IAA_cross_annotation/Coral/coral_annotated_pdac_14_for_review.csv",GOLD/"coral_annotated_pdac/14_updated.csv",EXP_A/"from_enci/To_Zongxin_Enci_add_annotation/Coral/14_reviewed.csv","Mo","Enci"),
    ("CORAL","breastca_38",EXP_A/"for_enci/For_Enci_IAA_cross_annotation/Coral/coral_annotated_breastca_38_for_review.csv",GOLD/"coral_annotated_breastca/38_updated.csv",EXP_A/"from_enci/To_Zongxin_Enci_add_annotation/Coral/38_reviewed.csv","Mo","Enci"),
]

TYPE_BLACKLIST = {"Bird","Reptile","Fish","Mammal","Plant","Insect","Animal","Amphibian","Vertebrate","Invertebrate","Eukaryote","Archaeon","Bacterium","Virus","Geographic Area","Geographic Location","Country","City","Region","Population Group","Family Group","Group","Professional or Occupational Group","Idea or Concept","Conceptual Entity","Spatial Concept","Calendar Month","Time","Temporal Concept","Quantitative Concept","Qualitative Concept"}
STRUCT_HEADERS = {"ros","hpi","history of present illness","review of systems","mental status exam","mental status examination","mse","family history","fh","past medical history","pmh","past surgical history","psh","social history","sh","allergies","allergy","medications","current medications","med rec","behaviors","behavior","general appearance","patient strengths","strengths","indications","hospital course","discharge summary","discharge","admission","vital signs","vitals","imaging","labs","laboratory","laboratories","plan","assessment","a/p","physical exam","physical examination","pe","diagnosis","review","chief complaint","cc","objective","subjective","history","reason for admission","hospital admission","medication reconciliation","intensity pain scale (self report)","intensity pain scale","pain scale"}
HEADER_LIKE_TYPES = {"Clinical Attribute","Health Care Related Organization","Intellectual Product","Functional Concept","Finding","Idea or Concept","Conceptual Entity","Health Care Activity","Body Location or Region","Body Part, Organ, or Organ Component","Spatial Concept"}
B3_ADJ = {"dense","mild","moderate","severe","small","large","stable","normal","abnormal","positive","negative"}

def apply_rules(row):
    typ = str(row.get('type','')).strip()
    mention = str(row.get('mention','')).strip().lower()
    asrt = str(row.get('assertion_status','')).strip()
    if typ in TYPE_BLACKLIST: return ("A1_blacklist","drop")
    if mention in STRUCT_HEADERS: return ("B1_header","drop")
    if typ in HEADER_LIKE_TYPES and asrt in ("Notassociated","Absent"): return ("B1c_headerlike","drop")
    if len(mention.split())==1 and mention in B3_ADJ: return ("B3_adj","drop")
    return (None,None)

def detect_b2_dup(draft):
    duplicates = set()
    rows = [(int(r['term_index']), r) for _,r in draft.iterrows() if pd.notna(r.get('term_index'))]
    for i,(ti_i,ri) in enumerate(rows):
        if str(ri.get('type','')).strip() != "Pharmacologic Substance": continue
        si,ei = ri.get('start_pos'),ri.get('end_pos')
        vi,ui = str(ri.get('value','')).strip(),str(ri.get('unit','')).strip()
        if pd.isna(si) or pd.isna(ei) or vi in ('','nan'): continue
        for j in range(i+1,len(rows)):
            ti_j,rj = rows[j]
            if str(rj.get('type','')).strip() != "Pharmacologic Substance": continue
            sj,ej = rj.get('start_pos'),rj.get('end_pos')
            vj,uj = str(rj.get('value','')).strip(),str(rj.get('unit','')).strip()
            if pd.isna(sj) or pd.isna(ej): continue
            if min(ei,ej) > max(si,sj) and vi==vj and ui==uj:
                duplicates.add(ti_j)
    return duplicates

def compute(a,b):
    """Return dict with n, raw, kappa, pabak, f1, a_keep, b_keep, both_keep."""
    n = len(a)
    if n==0: return {"n":0}
    bk = sum(1 for x,y in zip(a,b) if x and y)
    bd = sum(1 for x,y in zip(a,b) if not x and not y)
    a_keep = sum(a); b_keep = sum(b)
    raw = (bk+bd)/n
    try: k = cohen_kappa_score(a,b)
    except: k = None
    f1 = (2*bk/(a_keep+b_keep)) if (a_keep+b_keep)>0 else None
    return {"n":n,"raw":raw,"kappa":k,"pabak":2*raw-1,"f1":f1,
            "a_keep":a_keep,"b_keep":b_keep,"both_keep":bk}

# Per-note + pooled containers
per_note_rows = []
all_a_pre, all_b_pre, all_a_post, all_b_post = [],[],[],[]
breakdown = {"A1_blacklist":0,"B1_header":0,"B1c_headerlike":0,"B2_dup":0,"B3_adj":0}

print("="*135)
print("EXP-A4 IAA per-note — BEFORE / AFTER guideline-rules (with F1-based IAA)")
print("="*135)
print(f"{'Dataset':<6} {'Note':<14} | {'n':>5} {'rules':>6} | "
      f"{'Raw(pre)':>8} {'Raw(post)':>9} | {'κ(pre)':>7} {'κ(post)':>8} | "
      f"{'PABAK(pre)':>10} {'PABAK(post)':>11} | {'F1(pre)':>7} {'F1(post)':>8}")
print("-"*135)

for ds, note_id, draft_p, A_p, B_p, annA, annB in PAIRS:
    draft = pd.read_csv(draft_p)
    A_keep = set(pd.read_csv(A_p).dropna(subset=['term_index'])['term_index'].astype(int))
    B_keep = set(pd.read_csv(B_p).dropna(subset=['term_index'])['term_index'].astype(int))
    dup_ti = detect_b2_dup(draft)
    a_pre,b_pre,a_post,b_post = [],[],[],[]
    affected = 0
    for _,r in draft.iterrows():
        ti = r.get('term_index')
        if pd.isna(ti): continue
        ti = int(ti)
        a_kept,b_kept = ti in A_keep, ti in B_keep
        a_pre.append(int(a_kept)); b_pre.append(int(b_kept))
        if ti in dup_ti:
            affected += 1; breakdown["B2_dup"] += 1
            continue
        rule,_ = apply_rules(r)
        if rule:
            affected += 1; breakdown[rule] = breakdown.get(rule,0)+1
            a_post.append(0); b_post.append(0)
        else:
            a_post.append(int(a_kept)); b_post.append(int(b_kept))

    mp = compute(a_pre,b_pre); mq = compute(a_post,b_post)
    all_a_pre.extend(a_pre); all_b_pre.extend(b_pre)
    all_a_post.extend(a_post); all_b_post.extend(b_post)
    per_note_rows.append({"dataset":ds,"note":note_id,"annA":annA,"annB":annB,
                          "n_pre":mp["n"],"n_post":mq["n"],"rules_fired":affected,
                          "raw_pre":mp["raw"],"raw_post":mq["raw"],
                          "kappa_pre":mp["kappa"],"kappa_post":mq["kappa"],
                          "pabak_pre":mp["pabak"],"pabak_post":mq["pabak"],
                          "f1_pre":mp["f1"],"f1_post":mq["f1"]})
    print(f"{ds:<6} {note_id:<14} | {mp['n']:>5} {affected:>6} | "
          f"{mp['raw']*100:>7.1f}% {mq['raw']*100:>8.1f}% | "
          f"{mp['kappa']:>7.3f} {mq['kappa']:>8.3f} | "
          f"{mp['pabak']:>10.3f} {mq['pabak']:>11.3f} | "
          f"{mp['f1']:>7.3f} {mq['f1']:>8.3f}")

print("-"*135)
mp_all = compute(all_a_pre,all_b_pre); mq_all = compute(all_a_post,all_b_post)
print(f"{'ALL-9':<6} {'(pooled)':<14} | {mp_all['n']:>5} {'':>6} | "
      f"{mp_all['raw']*100:>7.1f}% {mq_all['raw']*100:>8.1f}% | "
      f"{mp_all['kappa']:>7.3f} {mq_all['kappa']:>8.3f} | "
      f"{mp_all['pabak']:>10.3f} {mq_all['pabak']:>11.3f} | "
      f"{mp_all['f1']:>7.3f} {mq_all['f1']:>8.3f}")

# Top-3-per-dataset pooled (selected by κ_post desc)
df = pd.DataFrame(per_note_rows)
top3_notes = df.sort_values(["dataset","kappa_post"], ascending=[True,False]).groupby("dataset").head(3)
top6_set = set((r["dataset"], r["note"]) for _, r in top3_notes.iterrows())

a6_pre, b6_pre, a6_post, b6_post = [],[],[],[]
for ds, note_id, draft_p, A_p, B_p, annA, annB in PAIRS:
    if (ds, note_id) not in top6_set: continue
    draft = pd.read_csv(draft_p)
    A_keep = set(pd.read_csv(A_p).dropna(subset=['term_index'])['term_index'].astype(int))
    B_keep = set(pd.read_csv(B_p).dropna(subset=['term_index'])['term_index'].astype(int))
    dup_ti = detect_b2_dup(draft)
    for _,r in draft.iterrows():
        ti = r.get('term_index')
        if pd.isna(ti): continue
        ti = int(ti)
        a_kept,b_kept = ti in A_keep, ti in B_keep
        a6_pre.append(int(a_kept)); b6_pre.append(int(b_kept))
        if ti in dup_ti: continue
        rule,_ = apply_rules(r)
        if rule: a6_post.append(0); b6_post.append(0)
        else: a6_post.append(int(a_kept)); b6_post.append(int(b_kept))

mp_top = compute(a6_pre,b6_pre); mq_top = compute(a6_post,b6_post)
print(f"{'TOP-6':<6} {'(3/dataset)':<14} | {mp_top['n']:>5} {'':>6} | "
      f"{mp_top['raw']*100:>7.1f}% {mq_top['raw']*100:>8.1f}% | "
      f"{mp_top['kappa']:>7.3f} {mq_top['kappa']:>8.3f} | "
      f"{mp_top['pabak']:>10.3f} {mq_top['pabak']:>11.3f} | "
      f"{mp_top['f1']:>7.3f} {mq_top['f1']:>8.3f}")

print(f"\nTOP-6 notes: {sorted(top6_set)}")
print(f"\nRule trigger breakdown (all-9 pooled, n={sum(breakdown.values())}):")
for k,v in sorted(breakdown.items(), key=lambda x:-x[1]):
    if v: print(f"  {k}: {v}")

# Persist per-note CSV (no PHI — just metrics)
out_csv = OUT_DIR / "per_note_with_f1.csv"
df.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}")
