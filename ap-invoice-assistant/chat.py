
import os
import re


def _find_requested_lines(query: str, comparison: dict):
    """Very small intent parser: look for a line number, else return all flagged lines."""
    m = re.search(r"line\s*#?\s*(\d+)", query, re.I)
    if m:
        line_no = int(m.group(1))
        return [lr for lr in comparison["line_results"] if lr["line_no"] == line_no]

    m = re.search(r"\b(NB|PN|MN|CH|DK)[- ]?\d+\b", query, re.I)
    if m:
        sku = m.group(0).upper().replace(" ", "-")
        return [lr for lr in comparison["line_results"] if lr["sku"].upper() == sku]

    # default: all lines that actually have exceptions
    return [lr for lr in comparison["line_results"] if lr["exceptions"]]


def _template_answer(line_results: list, comparison: dict) -> str:
    if not line_results:
        return "I couldn't find a line matching that reference. Try asking about a specific line number, e.g. 'why was line 2 flagged?'"

    parts = []
    any_flagged = False
    for lr in line_results:
        if not lr["exceptions"]:
            continue
        any_flagged = True
        parts.append(f"**Line {lr['line_no']} — {lr['sku']} ({lr['description']}):**")
        for exc in lr["exceptions"]:
            parts.append(f"  • [{exc['type']}] {exc['detail']}")

    if not any_flagged:
        return "That line matched the PO within tolerance on price, quantity, and tax — no exception was raised."

    if comparison["missing_po_lines"]:
        skus = ", ".join(l["sku"] for l in comparison["missing_po_lines"])
        parts.append(f"\nNote: PO line(s) for {skus} were authorized but never appear on this invoice at all.")

    return "\n".join(parts)


def answer_query(query: str, comparison: dict) -> str:
    line_results = _find_requested_lines(query, comparison)
    grounded_answer = _template_answer(line_results, comparison)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return grounded_answer

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": (
                    "Rephrase the following exception explanation in clear, professional plain English "
                    "for an AP reviewer. Do NOT add any fact, number, or claim that is not already present "
                    "in the text below. Do not speculate about cause. Keep every number exactly as given.\n\n"
                    f"Reviewer question: {query}\n\nGrounded facts:\n{grounded_answer}"
                ),
            }],
        )
        return resp.content[0].text.strip()
    except Exception:
        # If the LLM call fails for any reason, fall back to the deterministic answer.
        return grounded_answer
