"""EXP-A IAA v3 — CONSENSUS rewrite instead of EXCLUDE.

If rule applies, simulate "if guideline existed both annotators would make same call":
  A1/B1/B1c/B3 → rule says SHOULD DROP → rewrite to both_drop=(0,0)
  B2 (drug dup) → exclude (dup is structural artifact of AI, not annotation issue)
"""
import pandas as pd
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

ROOT = Path("/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data")
EXP_A = ROOT / ".claude/worktrees/agent-a2f527fc03ba78605/runs/EXP-A/_unzipped"
GOLD = ROOT / "outputs/reviewed_updated2"

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
    if typ in TYPE_BLACKLIST:
        return ("A1_blacklist", "drop")
    if mention in STRUCT_HEADERS:
        return ("B1_header", "drop")
    if typ in HEADER_LIKE_TYPES and asrt in ("Notassociated","Absent"):
        return ("B1c_headerlike", "drop")
    if len(mention.split())==1 and mention in B3_ADJ:
        return ("B3_adj", "drop")
    return (None, None)

def detect_b2_dup(draft):
    """Drug brand/generic dup: 2 Pharm Subs rows with same value+unit + overlapping span."""
    duplicates = set()
    rows = [(int(r['term_index']), r) for _,r in draft.iterrows() if pd.notna(r.get('term_index'))]
    for i, (ti_i, ri) in enumerate(rows):
        if str(ri.get('type','')).strip() != "Pharmacologic Substance": continue
        si, ei = ri.get('start_pos'), ri.get('end_pos')
        vi, ui = str(ri.get('value','')).strip(), str(ri.get('unit','')).strip()
        if pd.isna(si) or pd.isna(ei) or vi in ('','nan'): continue
        for j in range(i+1, len(rows)):
            ti_j, rj = rows[j]
            if str(rj.get('type','')).strip() != "Pharmacologic Substance": continue
            sj, ej = rj.get('start_pos'), rj.get('end_pos')
            vj, uj = str(rj.get('value','')).strip(), str(rj.get('unit','')).strip()
            if pd.isna(sj) or pd.isna(ej): continue
            if min(ei,ej) > max(si,sj) and vi==vj and ui==uj:
                duplicates.add(ti_j)
    return duplicates

def compute(a,b):
    n = len(a)
    if n==0: return {"n":0,"raw":None,"kappa":None,"pabak":None}
    bk = sum(1 for x,y in zip(a,b) if x and y)
    bd = sum(1 for x,y in zip(a,b) if not x and not y)
    raw = (bk+bd)/n
    try: k = cohen_kappa_score(a,b)
    except: k = None
    return {"n":n,"raw":raw,"kappa":k,"pabak":2*raw-1}

print("="*120)
print("EXP-A IAA per-note — BEFORE / AFTER guideline-rules (CONSENSUS rewrite)")
print("="*120)
print(f"{'Dataset':<6} {'Note':<14} {'AnnA':<5} {'AnnB':<5} | {'n':>5} {'rules':>6} | "
      f"{'Raw%(pre)':>9} {'Raw%(post)':>10} | {'κ(pre)':>7} {'κ(post)':>8} | {'PABAK(pre)':>10} {'PABAK(post)':>11}")
print("-"*120)

all_a_pre, all_b_pre, all_a_post, all_b_post = [],[],[],[]
total_n=0; total_affected=0
breakdown = {"A1_blacklist":0,"B1_header":0,"B1c_headerlike":0,"B2_dup":0,"B3_adj":0}

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
        a_kept = ti in A_keep
        b_kept = ti in B_keep
        a_pre.append(int(a_kept)); b_pre.append(int(b_kept))
        
        # B2: drug dup → exclude from post (structural artifact)
        if ti in dup_ti:
            affected += 1; breakdown["B2_dup"] += 1
            continue
        # A1/B1/B1c/B3: consensus = drop (rewrite both to 0)
        rule, action = apply_rules(r)
        if rule:
            affected += 1; breakdown[rule] = breakdown.get(rule,0)+1
            a_post.append(0); b_post.append(0)
        else:
            a_post.append(int(a_kept)); b_post.append(int(b_kept))
    
    n = len(a_pre); total_n += n; total_affected += affected
    m_pre = compute(a_pre,b_pre); m_post = compute(a_post,b_post)
    all_a_pre.extend(a_pre); all_b_pre.extend(b_pre)
    all_a_post.extend(a_post); all_b_post.extend(b_post)
    print(f"{ds:<6} {note_id:<14} {annA:<5} {annB:<5} | {n:>5} {affected:>6} | "
          f"{m_pre['raw']*100:>8.1f}% {m_post['raw']*100:>9.1f}% | "
          f"{m_pre['kappa']:>7.3f} {m_post['kappa']:>8.3f} | "
          f"{m_pre['pabak']:>10.3f} {m_post['pabak']:>11.3f}")

print("-"*120)
mp = compute(all_a_pre,all_b_pre); mq = compute(all_a_post,all_b_post)
print(f"{'OVERALL':<6} {'(pooled)':<14} {'':<5} {'':<5} | {total_n:>5} {total_affected:>6} | "
      f"{mp['raw']*100:>8.1f}% {mq['raw']*100:>9.1f}% | "
      f"{mp['kappa']:>7.3f} {mq['kappa']:>8.3f} | "
      f"{mp['pabak']:>10.3f} {mq['pabak']:>11.3f}")
print(f"\nRule trigger breakdown (pooled n={total_affected}, {100*total_affected/total_n:.1f}% of all rows):")
for k,v in sorted(breakdown.items(), key=lambda x:-x[1]):
    print(f"  {k}: {v} ({100*v/max(1,total_affected):.1f}%)")
print(f"\nΔ overall: Raw% +{(mq['raw']-mp['raw'])*100:.1f}pp, κ {mq['kappa']-mp['kappa']:+.3f}, PABAK {mq['pabak']-mp['pabak']:+.3f}")
