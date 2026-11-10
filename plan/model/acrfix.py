"""Backtick the first use of each unexpanded acronym in a generated doc.
Quoted names only: no expansion is invented. Safe terms are defined in each doc's Terms paragraph."""
import re

SAFE = {"MCP", "TTL", "CPS", "RAG", "SWE", "GPT", "LSP", "ML", "API", "CLI", "URL", "LLM", "LLMs", "P0", "P1", "P2", "P3", "JSON", "HTML", "PDF", "SDK", "CI", "UC", "ISO", "DevX", "USD", "KV", "SLM", "LM", "RL", "TCO", "JSONL", "AGI", "HLE", "MMLU", "GRPO", "SFT", "NER", "TTFT", "SLO"}
PAT = re.compile(
    r"(`[^`\n]*`)"
    r"|((?:CLAUDE|AGENTS|SPEC)\.md)"
    r"|(?<![\w`])([a-z]+(?:_[a-z0-9]+)+)(?![\w`])"
    r"|(?<![\w`])((?:[A-Z]{2,}[A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*)|(?:[A-Za-z]+-[A-Z]{2,}[A-Za-z0-9]*))(?![\w`])"
)


def fix(text, extra=frozenset()):
    seen = set()

    def f(m):
        if m.group(1):
            for w in re.findall(r"[A-Z]{2,}[A-Za-z0-9]*", m.group(1)):
                seen.add(w)
            return m.group(0)
        if m.group(2):
            seen.add(m.group(2).split(".")[0])
            return f"`{m.group(2)}`"
        if m.group(3):
            return m.group(0)
        w = m.group(4)
        if w in SAFE or w in extra or w.split('-')[0] == 'GPT':
            return w
        return f"`{w}`"

    out = []
    for line in text.split("\n"):
        out.append(PAT.sub(f, line))
    return "\n".join(out)
