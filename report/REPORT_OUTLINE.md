# Dissertation outline

A planning aid, not content. Every `[WRITE]` marker is yours to fill — the
analysis and argument have to be your own work, and the assignment brief is
explicit that assessed writing must not come from an AI tool.

What this file gives you: the structure, what each section has to contain to
satisfy the published marking criteria, which evidence in this repository
supports it, and a word budget that adds up.

---

## Where the marks are

From the assignment brief, Task 2 (60% of the module):

| Criterion | Weight | What the marker is looking for |
|---|---|---|
| **LO4 — Implementation** | **40%** | An artefact that works and solves a real problem |
| **LO3 — Design of artefact / data-gathering** | **35%** | A defensible evaluation design, with the techniques analysed |
| **LO2 — Theory applied** | **25%** | Literature connected to your design decisions, cited properly |

Two implications worth acting on:

- **75% is the artefact and its evaluation design.** That is built, measured and
  documented. Your job in the writing is to make it legible, not to invent it.
- **LO2 is the one with no code behind it.** It is where a strong project most
  often loses marks, because the literature gets summarised rather than
  *applied*. Every claim you make about your design should trace back to
  something you read.

Grade bands to aim at: 80–89% for LO4 requires "end product is relevant to
solving [a] real life problem"; 90%+ requires the result be "of publishable
standard". Read the exact wording in `../proposal/CMP7200_Assignment_Brief.pdf`
before you finish — it tells you what the marker is ticking.

---

## Structure and word budget

Total 12,000 words (+10% tolerance). Front matter, references and appendices do
not count.

| Ch | Chapter | Words | Serves |
|---|---|---|---|
| — | Title, abstract, contents, acknowledgements | — | not counted |
| 1 | Introduction | 1,200 | LO1 |
| 2 | Literature review | 2,500 | **LO2** |
| 3 | Methodology | 2,000 | **LO3** |
| 4 | Design and implementation | 2,800 | **LO4** |
| 5 | Evaluation and results | 2,200 | LO3 + LO4 |
| 6 | Discussion | 900 | LO2 + LO5 |
| 7 | Conclusion and future work | 400 | LO5 |
| — | References, appendices | — | not counted |

---

## Chapter 1 — Introduction (~1,200)

- 1.1 Background and motivation — `[WRITE]`
- 1.2 Problem statement — `[WRITE]`
- 1.3 Aim and objectives — restate from the proposal, marking any that changed
- 1.4 Scope — `[WRITE]`
- 1.5 Contributions — `[WRITE]`
- 1.6 Dissertation structure — `[WRITE]`

**Evidence available:** `../PROJECT_GUIDE.docx` §1 and §2 cover the problem and
scope in the form the implementation actually took.

**Note:** state your objectives as they ended up, and flag any that changed. A
marker comparing your proposal to your dissertation will notice; explaining a
deviation reads as control, hiding one reads as drift.

---

## Chapter 2 — Literature review (~2,500) — LO2, 25%

- 2.1 Single-LLM tool use and its limits — `[WRITE]`
- 2.2 Multi-agent frameworks — `[WRITE]`
- 2.3 Tool and messaging protocols — `[WRITE]`
- 2.4 AI travel planning systems — `[WRITE]`
- 2.5 Conceptual model and the gap — `[WRITE]`

**Evidence available:** the proposal's review is the starting point; extend it.
Your groundedness result speaks directly to the hallucination literature.

**What separates the bands here:** the criteria distinguish "compares"
literature from "constructs [a] conceptual model derived from these sources".
Aim for the second. For each of the three failure modes you designed against —
context bloat, protocol fragility, semantic drift — name the work that
identifies it and the design decision that answers it. Your measurements let you
close that loop with evidence rather than assertion, which most projects cannot.

---

## Chapter 3 — Methodology (~2,000) — LO3, 35%

- 3.1 Research paradigm (Design Science) — `[WRITE]`
- 3.2 Why four architectures — `[WRITE]`
- 3.3 Scenario design — `[WRITE]`
- 3.4 Metrics and why each was chosen — `[WRITE]`
- 3.5 Controls and fairness — `[WRITE]`
- 3.6 Reproducibility — `[WRITE]`
- 3.7 Ethics and limitations — `[WRITE]`

**Evidence available:**

| Section | Source |
|---|---|
| 3.2 | `../comparison/README.md` — the per-arm justifications |
| 3.3 | `../comparison/scenarios.py` — the docstring explains the axes chosen |
| 3.4 | `../comparison/metrics.py` — including why price matching beats name matching |
| 3.5 | `../comparison/run_comparison.py` — the fairness rules it enforces |
| 3.6 | `../PROJECT_GUIDE.docx` §7 |

**The single most important point to land:** arm C exists so the comparison is
not against a straw man. Explain that a marker could otherwise object that the
multi-agent arm lost through misconfiguration, and that arm C removes the
objection. Making that argument yourself is worth more than the result it
protects.

Also state plainly: the six-agent arms instantiate **five** agents (the
conversational agent is omitted so every arm receives an identical request).
Call it a five-agent ablation of the six-agent design.

---

## Chapter 4 — Design and implementation (~2,800) — LO4, 40%

- 4.1 System architecture — insert `../figures/diagrams/architecture.png`
- 4.2 The MCP server — insert `../figures/diagrams/mcp_lifecycle.png`
- 4.3 The A2A protocol — insert `../figures/diagrams/a2a_flow.png`
- 4.4 The four architectures — insert `../figures/diagrams/four_arms.png`
- 4.5 Budget allocation and feasibility — `[WRITE]`
- 4.6 Implementation problems and how they were solved — `[WRITE]`
- 4.7 Testing — `[WRITE]`

**Evidence available:** `../PROJECT_GUIDE.docx` §3, §5 and §8; `../src/README.md`
for the component map and the failure modes worth describing.

**4.6 deserves real space.** The strongest material you have is the *quiet*
failures: dates silently ignored behind an HTTP 200, twelve tools returning
"Connection lost" while the system produced confident itineraries anyway, a cost
figure that was never measured. Each shows diagnosis, not just coding. Guide §8
lists them with resolutions.

**4.5 is your supervisor's requested change.** Cover why one fixed split was
wrong (airfare scales per person and by distance; accommodation scales per night
and is shared), what replaced it, and that the feasibility floor is now
destination-specific.

---

## Chapter 5 — Evaluation and results (~2,200)

- 5.1 Experimental setup — `[WRITE]`
- 5.2 Cost across architectures — insert `../figures/results/efficiency.png`
- 5.3 The effect of tuning — insert `../figures/results/tuning_effect.png`
- 5.4 Groundedness — insert `../figures/results/groundedness.png`
- 5.5 Threats to validity — `[WRITE]`

**Evidence available:** `../comparison/results/comparison_results.json` holds
every number, with provenance (model, API mode, scenario ids, status).

**Check `status` and `scenario_ids` before quoting anything.** If the run is
partial, say so in 5.1 rather than letting a reader assume twenty scenarios.

**5.5 must include, in your own words:**

| Threat | Why it matters |
|---|---|
| Run-to-run variance | Arm B varied 19–23 calls on identical input; figures are single-run |
| Scenario coverage | However many are recorded is your real n |
| Destination price data | A ~60-city table; unknown cities get mid-tier defaults |
| Name-based groundedness | Weak — a model can guess a real airline. Price matching carries the claim |
| No user study | Scripted scenarios limit external validity |

Naming these yourself is worth more than hoping they go unnoticed. A marker who
finds an unmentioned weakness doubts everything else.

---

## Chapter 6 — Discussion (~900)

- 6.1 What the results mean — `[WRITE]`
- 6.2 Against the literature — `[WRITE]`
- 6.3 Where the proposal changed, and why — `[WRITE]`

**Evidence available:** `../proposal/README.md` tabulates every divergence
(Kiwi→fly-scraper, GPT-4o→Gemini, 13→12 tools, 6→3 agents) with reasons.

**The honest finding is the interesting one.** Tuning removed most of the
multi-agent penalty, so the conclusion is narrower than "fewer agents win": the
naive penalty was largely implementation, and what remains after a fair
comparison is a smaller difference in cost but a clear one in call count and
latency. Argue the narrower claim — it is the one your data supports, and it is
harder to attack.

---

## Chapter 7 — Conclusion and future work (~400)

- 7.1 Objectives revisited — `[WRITE]`
- 7.2 Contributions — `[WRITE]`
- 7.3 Future work — `[WRITE]`

Candidates for future work, each grounded in a real limitation: deriving
destination price tiers from live data instead of a fixed table; a hybrid arm
that uses an agent only when a first search fails; a live user study.

---

## Before submitting

- [ ] Student number only — the brief says it is marked anonymously
- [ ] BCU cover sheet attached
- [ ] Font size 11, line spacing 1.5
- [ ] BCU Harvard referencing throughout
- [ ] Word count within 12,000 +10%
- [ ] Every figure captioned and referenced in the text
- [ ] Results regenerated after the final evaluation run:
      `python scripts/make_charts.py && python scripts/generate_guide.py`
- [ ] Numbers in the text match `comparison/results/comparison_results.json`
- [ ] Scenario coverage stated honestly wherever results are quoted
