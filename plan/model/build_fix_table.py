#!/usr/bin/env python3
"""Generate the 50-row fix table docs from plan/model/fix-table.json.

Outputs (all generated, never hand-edited):
  plan/12-fix-table-50-rows.md       master table, one row per problem
  plan/12a-fix-technique-detail.md   named techniques, mechanism, effect, loses, test, per row
  plan/model/fix-table-fragment.html guide section body (table + per-row details)

Gate: exactly 50 rows numbered 1..50, every src id resolves to a corpus file.
"""
import json, os, re, sys, html, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acrfix

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAN = os.path.join(ROOT, "plan")
rows = json.load(open(os.path.join(PLAN, "model", "fix-table.json")))

def clean(x):
    if isinstance(x, str):
        x = x.replace("No measured dollar saving for history edits in a coding-agent bill: C:024 puts", "No measured dollar saving for history edits in a coding-agent bill. C:024 puts")
        x = x.replace("which conflicts with", "which conflicts with")
        x = re.sub(r"\bNOT\b", "not", x)
        x = re.sub(r"\beasy\b", "simple", x)
        x = re.sub(r"(?<![`\w])(HEAD|FAIL|ERROR)(?![`\w])", r"`\1`", x)
        x = re.sub(r"(?<![`\w])RTK-ML(?![`\w])", "`RTK-ML`", x)
        x = x.replace("UC Berkeley", "University of California, Berkeley")
        return x
    if isinstance(x, list):
        return [clean(i) for i in x]
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    return x


rows = clean(rows)
_cb = os.path.join(PLAN, "model", "coverage-by-row.json")
extra = json.load(open(_cb)) if os.path.exists(_cb) else {}
extra = clean(extra)
n_extra = sum(len(v) for v in extra.values())

# ---- gate -------------------------------------------------------------
errs = []
if [r["n"] for r in rows] != list(range(1, 51)):
    errs.append("rows are not exactly 1..50")
for r in rows:
    r["class"] = str(r["class"])
    if r["class"] not in "0123":
        errs.append(f"row {r['n']}: bad class {r['class']}")
    if not r["techniques"]:
        errs.append(f"row {r['n']}: no techniques")
    for t in r["techniques"]:
        for s in t.get("src", []):
            m = re.match(r"([AC]):(\d{3})$", s)
            if not m:
                errs.append(f"row {r['n']}: bad src {s}")
                continue
            d = "research/corpus" if m[1] == "A" else "research-cli-agents/corpus"
            if not os.path.exists(os.path.join(ROOT, d, m[2] + ".txt")):
                errs.append(f"row {r['n']}: missing corpus file {s}")
if errs:
    print("\n".join(errs))
    sys.exit(1)

# ---- derived fields ---------------------------------------------------
PHASE = {"0": "P0", "1": "P1", "2": "P2", "3": "P0"}
CLASS_NAME = {"0": "0 Alert", "1": "1 Guard", "2": "2 Behaviour change", "3": "3 Human action"}


def evidence(text):
    t = text.lower()
    return "proposal" if ("devx proposal" in t or "no corpus source" in t) else "corpus"


for r in rows:
    r["phase"] = PHASE[r["class"]]
    r["ev_api"] = evidence(r["fix_api"])
    r["ev_cli"] = evidence(r["fix_cli"])


_seen = set()
_SAFE = {"MCP", "TTL", "CPS", "RAG", "SWE", "GPT", "LSP", "RTK", "RTK-ML"}
_ACR = re.compile(r"(?<![`\w])((?:[A-Z]{2,}[A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*)|(?:[A-Za-z]+-[A-Z]{2,}[A-Za-z0-9]*))(?![`\w])")


def acr(s):
    def f(m):
        w = m.group(1)
        if w in _SAFE or w in _seen:
            return w
        _seen.add(w)
        return f"`{w}`"
    return _ACR.sub(f, s)


def esc(s):
    s = s.replace("|", "\\|").replace("\n", " ")
    return re.sub(r"(?<![`\w])((?:CLAUDE|AGENTS|SPEC)\.md)", r"`\1`", s)


def names(r, with_src=True):
    out = []
    for t in r["techniques"]:
        s = ", ".join(t.get("src", []))
        out.append(f"{t['name']} ({s})" if with_src and s else t["name"])
    return "; ".join(out)


counts = collections.Counter(r["class"] for r in rows)
ntech = sum(len(r["techniques"]) for r in rows)
nsrc = len({s for r in rows for t in r["techniques"] for s in t.get("src", [])})
prop_api = sum(r["ev_api"] == "proposal" for r in rows)
prop_cli = sum(r["ev_cli"] == "proposal" for r in rows)

# ---- master table -----------------------------------------------------
m = []
m.append("# The 50 problems and how to fix each one\n")
m.append(
    "Each row is one of the 50 ranked token-leak rows in hermes-engine (`_research/hermes/notes/A-taxonomy.md`). "
    "For each row the table gives the fix for API agents (applied at the gateway) and for CLI agents (applied through "
    "hooks, settings and flags), the named techniques behind it, and the phase it ships in. "
    "Technique names are quoted from the corpus. Ids: `A:nnn` API corpus, `C:nnn` CLI corpus. "
    "Anything with no corpus source is labelled DevX proposal.\n"
)
m.append(
    f"Counts: 50 rows, {ntech} techniques cited from {nsrc} sources, plus {n_extra} more technique entries from the coverage pass over the other sources (`12b-source-coverage.md`). "
    f"Fix classes: {counts['0']} alert, {counts['1']} guard, {counts['2']} behaviour change, {counts['3']} human action. "
    f"Fix evidence: the API fix rests on a DevX proposal in {prop_api} rows and the CLI fix in {prop_cli} rows.\n"
)
m.append(
    "Terms: Model Context Protocol (MCP) is the tool-server standard. Time to live (TTL) is how long a cache entry lasts. "
    "Cost per successful task (CPS) is Token Economics's main metric. Language Server Protocol (LSP) gives code navigation. "
    "RTK is a command-line proxy tool (RTK) named in C:024. "
    "Project instruction files such as `CLAUDE.md`, `AGENTS.md` and `SPEC.md` hold standing rules for a harness.\n"
)
m.append("## How to read the columns\n")
m.append(
    "- **Class** is the highest fix class involved (see `11-detect-measure-apply.md`). Class 2 fixes change what the model sees and wait for a paired cost-per-success win.\n"
    "- **Phase** is where the fix ships. Every detector runs from P0 in alert mode. Class 3 rows ship as recommendations in P0.\n"
    "- **Evidence** is `corpus` when a source in the corpus supports the fix, and `proposal` when it is a DevX proposal that needs a P0 spike.\n"
    "- Mechanism, measured effect, where each technique loses and the test design are in `12a-fix-technique-detail.md`.\n"
)
m.append("## Table\n")
m.append("| # | Problem | Class | Phase | Fix for API agents | Fix for CLI agents | Named techniques | Evidence API / CLI |")
m.append("|---|---|---|---|---|---|---|---|")
for r in rows:
    m.append(
        f"| {r['n']} | {esc(r['name'])} | {CLASS_NAME[r['class']]} | {r['phase']} | {esc(r['fix_api'])} | "
        f"{esc(r['fix_cli'])} | {esc(names(r))} | {r['ev_api']} / {r['ev_cli']} |"
    )
m.append("")
m.append("## Rows by phase\n")
m.append("| Phase | Rows | Count |")
m.append("|---|---|---|")
for ph, label in (("P0", "alert or recommendation"), ("P1", "guard"), ("P2", "behaviour change")):
    ns = [r["n"] for r in rows if r["phase"] == ph]
    m.append(f"| {ph} ({label}) | {', '.join(map(str, ns))} | {len(ns)} |")
m.append("")
m.append(
    "P3 adds no new rows. It puts a canary, a kill-switch and an auto-rollback around every P2 fix that shipped.\n"
)
m.append("## Source notes\n")
m.append(
    "Rows come from hermes-engine, which only observes and prices at list rates. Techniques come from the two corpora "
    "(`research/corpus`, `research-cli-agents/corpus`) and were read by model agents, so each name and number is only as "
    "reliable as that read. All 423 sources have a coverage record in `12b-source-coverage.md`, with how far each was read. Rows 6 and 8 carry a conflict: C:024 puts conversation history under 1 percent of billed "
    "cost, while hermes reports 10.5 percent for row 6. Token Economics measures billed cost and decides.\n"
)
open(os.path.join(PLAN, "12-fix-table-50-rows.md"), "w").write("\n".join(m))

# ---- detail doc -------------------------------------------------------
d = ["# Technique detail for the 50 problems\n"]
d.append(
    "One section per row. Each lists detection for API and CLI, the named techniques with how they work, the measured effect, "
    "where they lose, the test design, and what the corpus does not cover. Master table: `12-fix-table-50-rows.md`.\n"
)
d.append(
    "Terms: Model Context Protocol (MCP) is the tool-server standard. Time to live (TTL) is how long a cache entry lasts. "
    "Cost per successful task (CPS) is Token Economics's main metric. Language Server Protocol (LSP) gives code navigation. "
    "\n\n"
    "\n\nRetrieval-augmented generation (RAG) feeds retrieved text to a model. RTK-ML is a variant of the command-line proxy tool (RTK) that C:024 names without expanding either term. "
    "Environment variables that start with Claude Code (CLAUDE) belong to Claude Code. "
    "Software Engineering (SWE) bench tasks and Generative Pre-trained Transformer (GPT) models appear as the sources name them. "
    "Project instruction files such as `CLAUDE.md`, `AGENTS.md` and `SPEC.md` hold standing rules for a harness. "
    "Key-value (KV) is the attention cache a model keeps per token. Small language model (SLM) and language model (LM) name model size.\n\nReinforcement learning (RL), group relative policy optimization (GRPO) and supervised fine-tuning (SFT) are training methods. Total cost of ownership (TCO) is lifetime cost. JSON Lines (JSONL) is a file format with one JSON record per line.\n\nArtificial general intelligence (AGI), Humanity's Last Exam (HLE) and Massive Multitask Language Understanding (MMLU) appear in source titles.\n\nNamed-entity recognition (NER), time to first token (TTFT) and service-level objective (SLO) appear as the sources use them. \n"
)
for r in rows:
    d.append(f"## {r['n']}. {r['name']}\n")
    d.append(f"{r['why']}\n")
    d.append(f"- **Detect, API:** {r['detect_api']}")
    d.append(f"- **Detect, CLI:** {r['detect_cli']}")
    d.append(f"- **Fix, API:** {r['fix_api']}")
    d.append(f"- **Fix, CLI:** {r['fix_cli']}")
    d.append(f"- **Class and phase:** {CLASS_NAME[r['class']]}, {r['phase']}\n")
    d.append("| Technique | Kind | How it works | Effect | Loses when | Source |")
    d.append("|---|---|---|---|---|---|")
    for t in r["techniques"]:
        d.append(
            f"| {esc(t['name'])} | {t['kind']} | {esc(t['how'])} | {esc(t['effect'])} | {esc(t['loses'])} | "
            f"{esc(', '.join(t.get('src', [])))}: {esc(t['paper'])} |"
        )
    d.append("")
    ex = extra.get(str(r["n"]), [])
    if ex:
        d.append("More techniques from the source coverage pass (`12b-source-coverage.md`). Each is one source's claim and is untested here.\n")
        d.append("| Technique | How it works | Effect | Loses when | Source |")
        d.append("|---|---|---|---|---|")
        for x in ex:
            d.append(f"| {acr(esc(x['technique']))} | {acr(esc(x['how']))} | {acr(esc(x['effect']))} | {acr(esc(x['loses'] or 'not stated'))} | {x['id']} |")
        d.append("")
    d.append(f"**Test before enabling:** {r['methodology']}\n")
    d.append(f"**Not covered by the corpus:** {r['gaps']}\n")
open(os.path.join(PLAN, "12a-fix-technique-detail.md"), "w").write(acrfix.fix("\n".join(d)))

# ---- html fragment ----------------------------------------------------
def h(x):
    x = html.escape(x)
    x = re.sub(r"`([^`]+)`", r"<code>\1</code>", x)
    return re.sub(r"(?<![>\w`])((?:CLAUDE|AGENTS|SPEC)\.md)", r"<code>\1</code>", x)


f = []
f.append('<div class="scroll"><table>')
f.append(
    "<tr><th>#</th><th>Problem</th><th>Class</th><th>Phase</th><th>Fix for API agents</th>"
    "<th>Fix for CLI agents</th><th>Named techniques</th></tr>"
)
for r in rows:
    f.append(
        f'<tr id="row{r["n"]}"><td>{r["n"]}</td><td>{h(r["name"])}</td><td>{h(CLASS_NAME[r["class"]])}</td>'
        f'<td>{r["phase"]}</td><td>{h(r["fix_api"])}</td><td>{h(r["fix_cli"])}</td><td>{h(names(r))}</td></tr>'
    )
f.append("</table></div>")
f.append("<h3>Technique detail by row</h3>")
for r in rows:
    f.append(f"<div class=\"rowdetail\"><h4>{r['n']}. {h(r['name'])}</h4>")
    f.append(f"<p>{h(r['why'])}</p>")
    f.append(
        f"<p>API detection: {h(r['detect_api'])} CLI detection: {h(r['detect_cli'])}</p>"
    )
    f.append('<div class="scroll"><table><tr><th>Technique</th><th>How it works</th><th>Effect</th><th>Loses when</th><th>Source</th></tr>')
    for t in r["techniques"]:
        f.append(
            f"<tr><td>{h(t['name'])}</td><td>{h(t['how'])}</td><td>{h(t['effect'])}</td><td>{h(t['loses'])}</td>"
            f"<td>{h(', '.join(t.get('src', [])))}: {h(t['paper'])}</td></tr>"
        )
    f.append("</table></div>")
    ex = extra.get(str(r["n"]), [])
    if ex:
        f.append("<p>More techniques from the source coverage pass. Each is one source's claim and is untested here.</p>")
        f.append('<div class="scroll"><table><tr><th>Technique</th><th>How it works</th><th>Effect</th><th>Loses when</th><th>Source</th></tr>')
        for x in ex:
            f.append(f"<tr><td>{h(x['technique'])}</td><td>{h(x['how'])}</td><td>{h(x['effect'])}</td><td>{h(x['loses'] or 'not stated')}</td><td>{x['id']}</td></tr>")
        f.append("</table></div>")
    f.append(f"<p>Test before enabling: {h(r['methodology'])} Not covered: {h(r['gaps'])}</p></div>")
open(os.path.join(PLAN, "model", "fix-table-fragment.html"), "w").write("\n".join(f))

print(
    f"ok: 50 rows, {ntech} techniques, {nsrc} sources, classes {dict(counts)}, "
    f"proposal fixes api={prop_api} cli={prop_cli}"
)
