#!/usr/bin/env python3
"""Insert the generated fix-table fragment into token-economics-guide.html between markers."""
import re, os
D = os.path.dirname(os.path.abspath(__file__))
g = os.path.join(os.path.dirname(D), "token-economics-guide.html")
import acrfix
def _html_fix(h):
    out=[];incode=0
    for part in re.split(r"(<[^>]+>)",h):
        if part.startswith("<"):
            if re.match(r"<code\b",part): incode+=1
            elif part.startswith("</code"): incode=max(0,incode-1)
            out.append(part)
        elif incode or not part.strip():
            out.append(part)
        else:
            t=acrfix.fix(part)
            out.append(re.sub(r"`([^`]+)`",r"<code>\1</code>",t))
    return "".join(out)
frag = _html_fix(open(os.path.join(D, "fix-table-fragment.html")).read())
html = open(g).read()

intro = '''<section id="fixes">
<h2>The 50 problems and how to fix each one</h2>
<p>Every row below is one of the 50 token-leak rows in hermes-engine. The table gives the fix for API agents, which Token Economics applies at the gateway, and for CLI agents, which Token Economics applies through hooks, settings and flags. Named techniques carry source ids (<code>A:nnn</code> API corpus, <code>C:nnn</code> CLI corpus). A fix with no corpus source says DevX proposal and waits for a P0 spike.</p>
<ul>
<li><strong>Classes.</strong> 1 row is an alert, 3 are zero-risk guards, 33 change behaviour and 13 need a human action.</li>
<li><strong>Evidence.</strong> The API fix rests on a DevX proposal in 21 rows and the CLI fix in 8. Techniques were read by model agents. All 423 sources are covered in <code>12b-source-coverage.md</code>: 86 cited here, 112 papers read in full text, and 225 vendor docs, blogs and pages read at abstract and key-section depth. Each name and number is only as reliable as that read.</li>
<li><strong>Conflict.</strong> C:024 puts conversation history under 1 percent of billed cost. Hermes reports 10.5 percent for row 6. Token Economics measures billed cost and decides.</li>
</ul>
<p>Terms: Model Context Protocol (MCP) is the tool-server standard. Time to live (TTL) is how long a cache entry lasts. Cost per successful task (CPS) is Token Economics's main metric. Language Server Protocol (LSP) gives code navigation. </p>
<p>Retrieval-augmented generation (RAG) feeds retrieved text to a model. Environment variables that start with Claude Code (CLAUDE) belong to Claude Code. RTK is a command-line proxy tool (RTK) named in C:024, and <code>RTK-ML</code> is a variant of it. The source does not expand either name. Software Engineering (SWE) bench tasks, Generative Pre-trained Transformer (GPT) models and the Tool Attention paper's intent-schema overlap (ISO) score appear as the sources name them.</p>
<p>Key-value (KV) is the attention cache a model keeps per token. Small language model (SLM) and language model (LM) name model size. Reinforcement learning (RL), group relative policy optimization (GRPO) and supervised fine-tuning (SFT) are training methods. Total cost of ownership (TCO) is lifetime cost. JSON Lines (JSONL) is a file format with one JSON record per line.</p>
<p>Humanity's Last Exam (HLE) and Massive Multitask Language Understanding (MMLU) appear in source titles. Named-entity recognition (NER) and time to first token (TTFT) appear as the sources use them. United States dollar (USD) is the currency unit.</p>
<div class="wide">
''' + frag + '''
</div>
<p>Mechanism, measured effect, where each technique loses and the test design for every row are in <code>plan/12a-fix-technique-detail.md</code>, and open under each row above.</p>
</section>
'''
block = "<!--fixes:start-->\n" + intro + "<!--fixes:end-->\n"
if "<!--fixes:start-->" in html:
    html = re.sub(r"<!--fixes:start-->.*?<!--fixes:end-->\n", lambda m: block, html, flags=re.S)
else:
    html = html.replace('<section id="phases">', block + '\n<section id="phases">', 1)

css = '''.wide table{min-width:1100px;font-size:13px}
.wide td,.wide th{padding-right:10px}
.rowdetail{border-top:1px solid var(--rule);padding:8px 0;break-inside:auto}
.rowdetail h4{margin:6px 0;font-weight:600;color:var(--ink);break-after:avoid}
.rowdetail table{min-width:900px;font-size:13px}
@media print{.scroll{overflow:visible}.rowdetail table,.wide table{min-width:0;width:100%;table-layout:fixed;font-size:9px}td,th{overflow-wrap:anywhere;word-break:break-word}tr{break-inside:avoid}.rowdetail{break-inside:auto}}
'''
html = html.replace('details{border-top:1px solid var(--rule);padding:8px 0}\nsummary{cursor:pointer;font-weight:500;color:var(--ink)}\ndetails table{min-width:900px;font-size:13px}\n', "")
if ".rowdetail" not in html:
    html = html.replace("@media (max-width:560px)", css + "@media (max-width:560px)", 1)
open(g, "w").write(html)
print("inserted", len(html))
