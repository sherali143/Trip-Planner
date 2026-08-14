# Documents

| File | What it is |
|---|---|
| `AI_Trip_Planner_Proposal.pdf` | The submitted project proposal (Assessment 1) |
| `CMP7200_Assignment_Brief.pdf` | The module assignment brief and marking criteria |
| `Dissertation_Project_Explanation.docx` | Generated project document — architecture, decisions, measured results |
| `generate_docx.py` | Generates the above |

## Regenerating the project document

```bash
python docs/generate_docx.py
```

It reads `comparison/results/comparison_results.json` and renders the measured
results table from it. **No number in it is typed by hand.**

This matters: the document previously hardcoded its headline figures — "5 LLM
calls", "~230 seconds", "85% faster". Once the LLM calls were actually
instrumented those proved wrong; the naive six-agent arm makes around 19–23
requests, not 5. Numbers typed into a document drift away from the code that
produced them, so now the document refuses to invent them: if the results file
is missing it renders "NOT YET GENERATED" rather than a plausible-looking table.

Re-run it after every evaluation run, alongside `figures/make_charts.py`.

## Where the proposal and the implementation diverge

Worth stating explicitly in the write-up rather than leaving for a reader to
notice:

| Proposal | Implementation | Why |
|---|---|---|
| Kiwi.com for flights | fly-scraper | Kiwi endpoint unreachable |
| GPT-4o / GPT-4o-mini | Gemini 2.5 Flash | Cost |
| 13 MCP tools | 12 | One flight tool consolidated |
| 6 agents | 3 in production, all four variants evaluated | The finding the dissertation reports |

The evaluated "6-agent" arms instantiate **five** agents: the conversational
agent is omitted so every arm receives the identical request string. That is a
deliberate choice for comparability, and it should be described as a five-agent
ablation of the six-agent design rather than as six agents.
