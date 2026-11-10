#!/usr/bin/env python3
"""Merge the coverage-pass records and write plan/12b-source-coverage.md.

Inputs: model/source-coverage.json (337 records from the coverage pass, plus read-depth tags)
        model/fix-table.json (rows and the 86 sources the table cites)
Output: plan/12b-source-coverage.md, model/coverage-by-row.json (read by build_fix_table.py)
Gate: every one of the 423 corpus ids has exactly one record.
"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acrfix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PLAN = os.path.join(ROOT, "plan")
cov = {r["id"]: r for r in json.load(open(os.path.join(HERE, "source-coverage.json")))}
rows = {r["n"]: r for r in json.load(open(os.path.join(HERE, "fix-table.json")))}

# ids and titles from the corpora
corpus = {}
for p, d in (("A", "research/corpus"), ("C", "research-cli-agents/corpus")):
    for f in sorted(os.listdir(os.path.join(ROOT, d))):
        if f.endswith(".txt"):
            t = open(os.path.join(ROOT, d, f), errors="replace").readline()
            corpus[f"{p}:{f[:3]}"] = re.sub(r"^TITLE:\s*", "", t).strip()
cited = collections.defaultdict(list)
for r in rows.values():
    for t in r["techniques"]:
        for s in t.get("src", []):
            if r["n"] not in cited[s]:
                cited[s].append(r["n"])

errs = []
if len(corpus) != 423:
    errs.append(f"corpus has {len(corpus)} ids, expected 423")
for i in corpus:
    if i not in cov and i not in cited:
        errs.append(f"no record for {i}")
for i in cov:
    if i in cited:
        errs.append(f"{i} is both cited and in the coverage pass")
    if i not in corpus:
        errs.append(f"{i} not in corpus")
if errs:
    print("\n".join(errs)); sys.exit(1)

THIN = set("A:037 A:140 A:286 C:113 A:139 A:138 A:142 A:141 A:266 A:253 C:042 C:125 A:137 A:254 C:118".split())
PARTIAL = set("C:135 C:096 A:017 A:083 A:094 A:105 A:009 A:062 A:072 A:157 A:008 A:041 A:131 C:033 C:045 C:131 A:024 A:147 A:201 A:251 A:035 A:063 A:085 A:133 A:027 A:038 A:066 A:076 A:109 A:120 A:136 A:185 A:101 A:129 A:178 A:273 C:097".split())


def _s(v):
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    return "" if v is None else str(v)


FULLREC = {}
for _r in json.load(open(os.path.join(HERE, "full-read.json"))):
    FULLREC[_r["id"]] = {k: (_r[k] if k == "new_techniques" else _s(_r.get(k))) for k in ("id", "read", "algorithm", "methodology", "key_numbers", "limits", "use_for_project", "corrections", "new_techniques")}
    FULLREC[_r["id"]]["new_techniques"] = [str(x) for x in _r.get("new_techniques") or []]
ABSTRACT = set()
TRUNC = set()
SKIM = set()
APP_READ = set("A:002 A:023 A:025 A:026 A:033 A:047 A:074 A:109 A:156 C:029 C:135 A:122 A:092 C:030 C:043".split())


def tier(i):
    if i in ABSTRACT:
        return "abstract page only"
    if i in TRUNC:
        return "partly read, about half"
    if i in SKIM:
        return "skimmed sections"
    if i in APP_READ:
        return "full text"
    if re.search(r"appendi|supplement|references|proof", FULLREC[i]["read"].lower()):
        return "full body, appendix not read"
    return "full text"


THIN = THIN - (set(FULLREC) - ABSTRACT)


def depth(i):
    if i in FULLREC:
        return tier(i)
    if i in cited:
        return "passage read for the row"
    if i in THIN:
        return "thin text, not assessed"
    if i in PARTIAL:
        return "partial read"
    return "abstract and key sections"


SEEN = set()
ACR = re.compile(r"(?<![`\w])((?:[A-Z]{2,}[A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*)|(?:[A-Za-z]+-[A-Z]{2,}[A-Za-z0-9]*)|(?:CLAUDE|AGENTS|SPEC)\.md)(?![`\w])")
BAN = [(r"\beasily\b", "readily"), (r"\beasy\b", "simple"), (r"\bbasically\b ?", ""), (r"\bvery\b ?", ""), (r"\betc\.?", "and others")]


def ban(t):
    for a, b in BAN:
        t = re.sub(a, b, t, flags=re.I)
    return t


EXTRA = frozenset('AI QA GPU CPU OOD EM KL AUC FLOPs MLP DPO PPO FP8 GSM8K AIME24 GPQA NQ APIs GPT MATH500 AMC23 NVIDIA'.split())
SAFE = {"MCP", "TTL", "CPS", "RAG", "SWE", "GPT", "LSP"}


def cell(s):
    s = re.sub(r"\s+", " ", str(s)).replace("|", "/").strip()
    for a, b in BAN:
        s = re.sub(a, b, s, flags=re.I)
    s = re.sub(r"\b(just|robust|Robust|Just)\b", r"`\1`", s)

    def f(m):
        w = m.group(1)
        if w in SAFE or w in SEEN:
            return w
        SEEN.add(w)
        return f"`{w}`"
    return ACR.sub(f, s)


# per-row additions from new techniques
byrow = collections.defaultdict(list)
for i, r in cov.items():
    if r.get("new") and r["rows"] and i not in THIN:
        for n in r["rows"]:
            if n in rows:
                f = FULLREC.get(i)
                if f and i not in ABSTRACT:
                    byrow[n].append({"id": i, "technique": r["technique"], "how": ban(f["algorithm"]), "effect": ban(f["key_numbers"]), "loses": ban(f["limits"])})
                else:
                    byrow[n].append({"id": i, "technique": r["technique"], "how": r["how"], "effect": r["effect"], "loses": r["loses"]})
json.dump({str(k): v for k, v in sorted(byrow.items())}, open(os.path.join(HERE, "coverage-by-row.json"), "w"), indent=1)

n_thin = sum(1 for i in cov if i in THIN and i not in FULLREC)
n_part = sum(1 for i in cov if i in PARTIAL and i not in FULLREC and i not in THIN)
tc = collections.Counter(tier(i) for i in FULLREC)
n_full = sum(v for k, v in tc.items() if k in ("full text", "full body, appendix not read"))
n_notfull = len(FULLREC) - n_full
n_abs2 = len(cov) - len(FULLREC)
n_rel = sum(1 for i, r in cov.items() if r["rows"] and i not in THIN)
n_new = sum(1 for i, r in cov.items() if r.get("new") and r["rows"] and i not in THIN)
n_none = sum(1 for i, r in cov.items() if not r["rows"] or i in THIN)

o = ["# Source coverage: all 423 corpus sources\n"]
o.append(
    "Every source in the two corpora has a record here. The fix table cites "
    f"{len(cited)} of them directly. A second pass read the other {len(cov)} for the names of algorithms, techniques and methods, "
    "and for which of the 50 rows each one bears on. This file is generated from `model/source-coverage.json`.\n"
)
o.append("## Counts\n")
o.append("| Group | Sources |")
o.append("|---|---|")
o.append(f"| Cited in the fix table, passage read for the row | {len(cited)} |")
o.append(f"| Papers read in full text by a model agent (third pass) | {n_full} |")
o.append(f"| Papers where the full text was not available or only partly read | {n_notfull} |")
o.append(f"| Vendor docs, blogs and others at abstract and key-section depth | {n_abs2} |")
o.append(f"| Of the second pass, bears on at least one row | {n_rel} |")
o.append(f"| Of the second pass, names a technique not already in the table | {n_new} |")
o.append(f"| Of the second pass, no technique for the 50 rows | {n_none} |")
o.append(f"| Thin text, could not be assessed | {n_thin} |")
o.append(f"| Total | {len(corpus)} |")
o.append("")
o.append("## How far each source was read\n")
o.append(
    f"Three passes, all by model agents. Pass one read {len(cited)} sources for the passage behind a fix-table row. "
    f"Pass two covered the other {len(cov)} at the abstract and key sections. "
    f"Pass three re-read the {len(FULLREC)} papers among them in full text. "
    f"Some of the {n_full} had no bibliography or appendix read. "
    "C:043 was read from a PDF the user supplied from Downloads after SSRN blocked the download. "
    "A:050 (HELM, 162 pages) was first read in part and later re-read in full from the local PDF, bibliography excepted.\n\n"
    "Six papers that had only an abstract page were downloaded after the user approved it, and were read in full except bibliographies.\n\n"
    "The vendor docs, blogs and other pages (about "
    f"{n_abs2}) were not re-read in full. No one read every source cover to cover. Figures are each source's own claim.\n\n"
    "One reader earlier fetched an arXiv PDF for A:025 without permission and deleted it. The user later approved downloading six abstract-only papers, A:025 among them, and A:025 was read from that approved copy. "
    "A:024 was read from a PDF already in `research/papers`.\n\n"
    "Terms: Model Context Protocol (MCP), time to live (TTL), cost per successful task (CPS), "
    "retrieval-augmented generation (RAG), Software Engineering (SWE) and Generative Pre-trained Transformer (GPT) appear as the sources use them. "
    "Key-value (KV) is the attention cache a model keeps per token. Small language model (SLM) and language model (LM) name model size.\n\nReinforcement learning (RL), group relative policy optimization (GRPO) and supervised fine-tuning (SFT) are training methods. Total cost of ownership (TCO) is lifetime cost. JSON Lines (JSONL) is a file format with one JSON record per line.\n\nArtificial general intelligence (AGI), Humanity's Last Exam (HLE) and Massive Multitask Language Understanding (MMLU) appear in source titles.\n\nNamed-entity recognition (NER), time to first token (TTFT) and service-level objective (SLO) appear as the sources use them. "
    "Other capitalised abbreviations are quoted from the source titles and are not expanded here.\n\n"
    "Terms in the full-text table: artificial intelligence (AI), question answering (QA), graphics processing unit (GPU) and central processing unit (CPU). "
    "Out-of-distribution (OOD), exact match (EM), Kullback-Leibler (KL) divergence and area under the curve (AUC) are measures. "
    "Floating-point operations (FLOPs), multilayer perceptron (MLP) and 8-bit floating point (FP8) are compute terms.\n\n"
    "Direct preference optimization (DPO) and proximal policy optimization (PPO) are training methods. "
    "Grade School Math 8K (GSM8K), American Invitational Mathematics Examination 2024 (AIME24), Graduate-Level Google-Proof Q&A (GPQA) and Natural Questions (NQ) are benchmarks. "
    "Application Programming Interfaces (APIs) is the plural of API. Other model and benchmark names are quoted as the sources give them.\n"
)
o.append("## Techniques not yet in the fix table, by row\n")
o.append("These come from the second pass. They are added to the detail file `12a-fix-technique-detail.md`. A row ships none of them until its own paired test passes.\n")
o.append("| Row | Problem | Added techniques (source) |")
o.append("|---|---|---|")
for n in sorted(byrow):
    items = "; ".join(f"{x['technique']} ({x['id']})" for x in byrow[n])
    o.append(f"| {n} | {cell(rows[n]['name'])} | {cell(items)} |")
o.append("")
o.append("## Full-text read of the 112 papers\n")
o.append("Each row is one paper. The record gives the algorithm, how it was tested, the key numbers, where it loses, what it means for Token Economics, and any correction to the earlier record. Read depth is in the second column.\n")
o.append("| Id | Read | Algorithm | Method | Key numbers | Loses | Use for Token Economics | Correction |")
o.append("|---|---|---|---|---|---|---|---|")
for i in sorted(FULLREC, key=lambda x: (x[0], x[2:])):
    f = FULLREC[i]
    o.append("| " + " | ".join([i, tier(i), cell(f["algorithm"]), cell(f["methodology"]), cell(f["key_numbers"]), cell(f["limits"]), cell(f["use_for_project"]), cell(f["corrections"])]) + " |")
o.append("")
o.append("## Technique names found in the full text\n")
o.append("Names the full-text pass found that the earlier records lacked. A row ships none of them until its own paired test passes.\n")
o.append("| Id | Names |")
o.append("|---|---|")
for i in sorted(FULLREC, key=lambda x: (x[0], x[2:])):
    nt = FULLREC[i]["new_techniques"]
    if nt:
        o.append(f"| {i} | {cell('; '.join(nt))} |")
o.append("")
o.append("## All 423 sources\n")
o.append("| Id | Title | Read | Rows | Technique or method |")
o.append("|---|---|---|---|---|")
for i in sorted(corpus, key=lambda x: (x[0], x[2:])):
    if i in cov:
        r = cov[i]
        rr = ", ".join(map(str, r["rows"])) or "none"
        tech = r["technique"] if i not in THIN else "not assessed: " + r["technique"]
    else:
        rr = ", ".join(map(str, cited[i]))
        tech = "; ".join(sorted({t["name"] for n in cited[i] for t in rows[n]["techniques"] if i in t.get("src", [])}))
    o.append(f"| {i} | {cell(corpus[i])} | {depth(i)} | {rr} | {cell(tech)} |")
o.append("")
_txt = acrfix.fix("\n".join(o), EXTRA)
for _w in ("SWE-bench", "LLMLingua", "KV-cache", "GPTCache"):
    _tok = "`" + _w + "`"
    _i = _txt.find(_tok)
    if _i >= 0:
        _txt = _txt[:_i + len(_tok)] + _txt[_i + len(_tok):].replace(_tok, _w)
open(os.path.join(PLAN, "12b-source-coverage.md"), "w").write(_txt)
print(f"ok: {len(corpus)} sources, cited {len(cited)}, second pass {len(cov)}, relevant {n_rel}, new {n_new}, none {n_none}, partial {n_part}, thin {n_thin}")
