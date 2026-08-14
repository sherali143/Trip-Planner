# Proposal and assignment brief

| File | What it is |
|---|---|
| `AI_Trip_Planner_Proposal.pdf` | The submitted project proposal (Assessment 1) |
| `CMP7200_Assignment_Brief.pdf` | Module assignment brief and marking criteria |

## Where the implementation diverges from the proposal

Worth stating in the write-up rather than leaving a reader to notice.

| Proposal | Implementation | Reason |
|---|---|---|
| Kiwi.com for flights | fly-scraper | The Kiwi endpoint was unreachable |
| GPT-4o / GPT-4o-mini | Gemini 2.5 Flash | Cost |
| 13 MCP tools | 12 | One flight tool consolidated |
| 6 agents | 3 in production; all four variants evaluated | This is the finding the dissertation reports |

**One point of precision.** The evaluated six-agent arms instantiate **five**
agents: the conversational agent is omitted so every architecture receives the
identical request string. That is deliberate, for comparability — but it should
be described as a five-agent ablation of the six-agent design rather than as six
agents, because a reader who counts will otherwise think it is an error.
