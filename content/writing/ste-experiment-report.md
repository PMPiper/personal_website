created: 2026-10-12

# Testing a writing-style prompt on a coding agent [DRAFT]

This is the technical companion to [What does "80% of the way to ASD-STE100" actually do?](/writing/ste-jargon-post/). That post is a simple show of what the outputs look like. This one covers how the experiment was set up, what was measured, and what didn't work.

TL;DR: asking Claude Code to write "X% of the way to ASD-STE100" behaves like a switch rather than a dial, does not shorten the output, and does not move the meaning. The agent also never produced the dense prose I set out to remove in the first place.

## 1. Question and design

ASD-STE100 Simplified Technical English (STE) is a controlled language from aerospace maintenance. The tip going around is to ask a model to explain something "80% of the way to ASD-STE100". I wanted to know three things:

1. Does the writing change in proportion to the percentage?
2. Does the meaning survive, or does the agent drop the hard parts to keep sentences short?
3. Does it remove dense, abstract prose in the kinds of document where that prose shows up?

**What a run is.** One *run* is one fresh, headless Claude Code session. It starts in a checkout of Beam with a single prompt, explores the code with read-only tools, and writes one answer. Nothing carries over from one run to the next. I save the answer and the full transcript, and everything below is measured on the answers.

Three choices define a run:

- the **task**: what kind of document the prompt asks for
- the **subsystem**: which part of Beam it is about
- the **STE level**: the style sentence at the end of the prompt

A *cell* is one subsystem at one level, for example "Coders at 80%". That makes 3 subsystems × 5 levels = 15 cells per task. A *repeat* is another run of the same cell with the identical prompt. Repeats show how much two answers differ by chance, which is the noise floor I compare the levels against. The run order was shuffled with a fixed seed, so no level ran all at once.

| Params | Values |
|---|---|
| Agent | Claude Code 2.1.296, headless (`claude -p`) |
| Codebase | [Apache Beam](https://github.com/apache/beam) Python SDK, pinned at commit `fadfc78` |
| Subsystem | RunInference, Coders, FnApiRunner |
| STE level | 0, 25, 50, 80, 100 |
| Task | explanation, design document, handoff document |

This is the prompt for the explanation task. `{name}` and `{path}` come from the subsystem:

```text
You are in a checkout of Apache Beam. Explain how the {name} subsystem in
sdks/python/apache_beam/{path} works to an experienced software engineer who
has never used Beam. Cover what problem it solves, the main classes and how
data flows through them, and anything surprising. Only read code under
sdks/python. Do not modify any files.
```

The only thing that changes between levels is one sentence at the end:

- Level 0: no sentence.
- Levels 25, 50, and 80: "Write your explanation about X% of the way to ASD-STE100 Simplified Technical English."
- Level 100: "Write your explanation in ASD-STE100 Simplified Technical English."

The two document tasks use the same structure with a different request:

| Task | Model and effort | Runs | The prompt asks for |
|---|---|---|---|
| Explanation | Sonnet 5.5, medium | 45 (3 per cell) | an explanation for an experienced engineer who has never used Beam |
| Design document | Sonnet 5.5, high | 15 (1 per cell) | the current architecture, for a design review |
| Handoff document | Sonnet 5.5, high | 15 (1 per cell) | a handoff for the engineer who takes over tomorrow |

I started with the explanation task only. The two document tasks were added after the first results, for a reason covered in section 6.

I picked Beam because I needed a codebase I didn't know, big enough that the agent has to go explore. The three subsystems differ in size:

| Subsystem | Path | Non-test Python files |
|---|---|---|
| RunInference (model inference inside a pipeline) | `apache_beam/ml/inference` | 18 |
| Coders (serialization) | `apache_beam/coders` | 10 |
| FnApiRunner (local portable runner) | `apache_beam/runners/portability/fn_api_runner` | 8 |

## 2. Isolating the agent

We needed to totally isolate the agent and prompt from style preferences. The target repository and my own Claude Code setup were two places there could be leakage.

**The repository.** Beam ships an `.agent/skills/` folder with 13 skills, including a `beam-concepts` cheat sheet. Claude Code doesn't auto-load that folder, but the agent could find it while exploring, and a pre-written concept guide would shape exactly the wording I'm trying to measure. So the harness deletes it with one local commit, then scans every tracked file for other agent instructions (`CLAUDE.md`, `AGENTS.md`, `.cursor/`, `SKILL.md`, and so on) and refuses to run if it finds one. Before every run the checkout is reset, and after every run `git status` must be empty or the run is thrown out.

**My setup.** I have a CLAUDE.md, memory, and skills. Every run used:

```bash
claude --safe-mode -p "<prompt>" \
  --model claude-sonnet-5-5 --effort medium \
  --tools "Read,Grep,Glob,Bash" \
  --allowedTools "Bash(ls *)" "Bash(find *)" "Bash(rg *)" "Bash(grep *)" \
                 "Bash(cat *)" "Bash(head *)" "Bash(wc *)" \
  --disallowedTools "Edit" "Write" "mcp__*" \
  --permission-prompts none \
  --strict-mcp-config \
  --setting-sources "" \
  --no-session-persistence \
  --output-format stream-json --verbose \
  --max-turns 60 --max-budget-usd 5
```

The harness also reads the `init` event of every session and fails the run unless it reports no MCP servers, the configured model, and exactly the built-in tools, skills, plugins, and agents that I pinned in the config.

Three things here were not what I assumed, and I only know because I tested them:

- **`--safe-mode` still applied my personal permission rules.** My `settings.json` allows things like `python3` and `mkdir`. `--setting-sources ""` stops that. With it, a test run that tried both was denied.
- **The allowlist is not the real boundary.** Claude Code also runs commands it considers read-only (`sed -n`, `tail`, `echo`) without asking, so the agent was not limited to the seven commands I listed. It was still read-only -- the `git status` check enforces that, not the list.
- **`--safe-mode` keeps what ships with Claude Code.** Three built-in plugins and 17 built-in skills still show up in the session. That's fine, but "no plugins" is the wrong assertion. "Exactly these plugins" is the right one.

I also left `git` off the allowlist on purpose. Deleting `.agent/` with a commit leaves it one `git show` away in the parent commit.

All 75 runs passed these checks on the first attempt.

## 3. Running it on a $20 plan

I ran all of this on a $20-a-month Pro plan, not an API key. On a subscription the limit often isn't dollars, it is a five-hour usage window, plus a weekly one, and every headless run draws on the same windows as my normal use.

| Task and model | Cost per run at API prices | Share of the five-hour window per run |
|---|---|---|
| Explanation, Sonnet 5.5 at medium effort | about $0.16 | about 1.6% |
| Design document, Sonnet 5.5 at high effort | about $0.71 | about 5% |
| Handoff document, Sonnet 5.5 at high effort | about $0.72 | about 6-7% |
| Design document, Opus 5.5 at high effort (3 test runs) | about $1.00 | about 4.5% |

The dollar column is what Claude Code reports each run would have cost on the API. The window column is rougher since it is read from the usage figure each run reports, and the session I used to build and babysit the harness was drawing on the same window. The total is ~$32 at API prices.

The windows are why the experiment is the size it is:

- I planned five repeats per cell for the explanation task and ran three, because three fit in one window and still gave a noise floor.
- I wanted Opus for the document tasks and used Sonnet. A 45-run Opus batch would have needed about two windows.
- The document tasks have one run per cell for the same reason. Those 30 runs took parts of three windows over two days.

Two harness features exist only because of this. `--stop-at-usage` ends a batch at a set share of the window, so there is room left to analyze what ran. `--by-repeat` finishes one repeat of every cell before starting the next, so a batch that stops early is still a balanced design. A stopped batch resumes with the same command and skips the cells that already finished.

## 4. Measures

**Text preparation.** Fenced code blocks, headings, and table rows are not prose and are dropped. Each remaining line is split into sentences with spaCy. An inline code span counts as one word for sentence length and is left out of everything else.

**STE surface measures.** Word count, words per sentence, share of sentences over 20 and over 25 words (the two STE limits), passive-voice rate, and Flesch-Kincaid grade.

**Dense-prose measures.** These exist because my first attempt at "jargon" measured the wrong thing (section 7). They count the features of one dense paragraph that I use as a yardstick:

- stacked noun phrases: the share of noun phrases with three or more nouns and adjectives ("durable intent ledger")
- hyphenated compounds per 1,000 words ("leader-fenced", "owner-scoped")
- nominalizations per 1,000 words: long nouns ending in -tion, -ment, -ity and the like
- nouns and adjectives per verb

**Content.** Identifier retention: of the code identifiers that the 0% runs of a subsystem agree on, how many does a given run mention? A 0% run is scored against the other 0% runs, never itself.

**Embeddings.** I used [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) through `sentence-transformers` on an RTX 5070. Code blocks were stripped first so pasted code didn't dominate the vectors. From the document embeddings: silhouette scores by subsystem and by level, cosine similarity to the 0% centroid, and the similarity between repeats.

**Statistics.** Per cell and per level: median, quartiles, mean, and a bootstrap 95% interval of the mean (10,000 resamples, seeded). Spearman correlation between level and each measure, with a bootstrap interval. I report the numbers and don't star anything as significant.

## 5. Results: the explanation task

45 runs, 9 per level (3 subsystems × 3 repeats).

| Measure | 0% | 25% | 50% | 80% | 100% |
|---|---|---|---|---|---|
| Words (median) | 1117 | 1156 | 1146 | 1110 | 1157 |
| Words per sentence (mean) | 9.3 | 8.6 | 8.8 | 8.5 | 8.3 |
| Sentences over 25 words | 0.5% | 0.2% | 0.1% | 0.0% | 0.1% |
| Passive voice | 9.3% | 7.9% | 7.6% | 5.4% | 5.2% |
| Flesch-Kincaid grade | 6.1 | 5.0 | 4.7 | 4.8 | 4.5 |
| Stacked noun phrases | 7.0% | 5.0% | 4.8% | 5.2% | 4.9% |
| Hyphenated compounds per 1k words | 23.1 | 13.8 | 12.4 | 12.1 | 10.5 |
| Nominalizations per 1k words | 23.5 | 22.6 | 21.3 | 23.0 | 20.9 |
| Files read by the agent (median) | 5 | 5 | 4 | 4 | 4 |

![Sentence length by STE level](/images/ste-jargon-post/explanation-sentence_length_by_level.png)

**The dial is closer to a switch.** Mean sentence length goes from 9.3 words at 0% (95% CI 8.9 to 9.8) to 8.6 at 25% and ends at 8.3 at 100% (8.0 to 8.6). The intervals for 25% through 100% all overlap each other. The Flesch-Kincaid grade does the same thing: 6.1, then 5.0, then somewhere between 4.5 and 4.8. Hyphenated compounds roughly halve by 25% (Spearman rho of -0.65 with level, 95% CI -0.82 to -0.41). Passive voice is the one row that looks like a dial, though with nine runs per level I can't tell neighboring steps apart.

**Length and exploration did not move.** The median explanation is about 1,100 words at every level (rho of -0.02). The agent read about 4 files per run at every level (rho of -0.08), and turns and cost didn't move either. Asking for a writing style did not change how the agent explored.

**The baseline was already inside the limits.** Only 0.5% of the 0% sentences were over 25 words and 3.3% were over 20. There was not much for STE to remove.

### Did the meaning survive?

![UMAP of explanations, colored by STE level, shaped by subsystem](/images/ste-jargon-post/explanation-doc_umap.png)

If STE only changes the style, the explanations should still group by subsystem, with the levels mixed inside each group. If the style takes over, they'll group by level.

| Grouping | Silhouette score |
|---|---|
| By subsystem, all runs | 0.90 |
| By STE level, all runs | -0.11 |
| By STE level, within RunInference | 0.00 |
| By STE level, within Coders | -0.07 |
| By STE level, within FnApiRunner | -0.10 |

By subsystem the score is 0.90, about as clean as clusters get. By level it is negative overall and roughly zero inside each subsystem. The embedding model can't tell a 0% explanation of Coders from a 100% one.

![Cosine similarity to the 0% baseline by STE level](/images/ste-jargon-post/explanation-drift_vs_level.png)

Drift from the baseline is flat. For every subsystem and level the mean similarity to the 0% centroid is between 0.962 and 0.976. The 0% runs themselves -- each compared with the other two -- score 0.962 to 0.971. No level drifted, including 100%. What we feared, that the hard parts get dropped to keep the sentences short, doesn't show up here.

The grey band is the noise floor: two 0% runs of the same subsystem have a median cosine similarity of 0.959 (IQR 0.954 to 0.960, 9 pairs). Similarity to a centroid runs a little higher than similarity between two single runs, so the fair comparison is the 0% points, and the STE levels sit right on top of them. Higher levels didn't make the repeats more alike either: mean pairwise similarity within a cell was 0.957 at 0% and 0.963 at 100%.

![Share of baseline identifiers mentioned, by STE level](/images/ste-jargon-post/explanation-identifier_retention.png)

Identifiers are the one place where something was lost. A 0% run mentions 65% of the identifiers that the other 0% runs agree on (95% CI 62% to 68%). At 25% through 80% that falls to 58-59%, and at 100% to 56% (53% to 59%). Roughly one in ten of the shared class and function names goes missing, and like everything else, most of that happens at the first step.

## 6. Results: the document tasks

The explanation results left a hole. The prose I wanted to get rid of looks like this:

> The canonical ingress path is a close-bounded, single-writer admission seam: the UI emits a work-request envelope into the durable intent ledger, which serves as the authoritative source of truth for desired-state materialization.

The full paragraph is four sentences of this. Scored with the dense-prose measures, it has 33% stacked noun phrases and 96 hyphenated compounds per 1,000 words. The 0% explanations had 7.0% and 23. The agent never wrote anything like it, so there was nothing for STE to fix.

I see that style most in AI-written design docs and handoff docs, so I added those two tasks. This is one run per cell, so each column below is 3 runs, one per subsystem.

Design document:

| Measure | Dense paragraph | 0% | 25% | 50% | 80% | 100% |
|---|---|---|---|---|---|---|
| Stacked noun phrases | 33% | 10.4% | 8.3% | 7.6% | 6.6% | 6.7% |
| Hyphenated compounds per 1k words | 96 | 33.1 | 17.3 | 15.0 | 16.5 | 11.6 |
| Nominalizations per 1k words | 58 | 31.2 | 23.4 | 21.6 | 20.6 | 23.6 |
| Words per sentence (mean) | | 9.9 | 8.1 | 8.5 | 8.3 | 7.9 |
| Flesch-Kincaid grade | | 7.6 | 5.6 | 5.3 | 5.3 | 4.9 |

![Hyphenated compounds per 1,000 words by STE level, design document](/images/ste-jargon-post/design-doc-compounds_by_level.png)

Handoff document:

| Measure | Dense paragraph | 0% | 25% | 50% | 80% | 100% |
|---|---|---|---|---|---|---|
| Stacked noun phrases | 33% | 9.0% | 7.2% | 7.4% | 5.6% | 6.1% |
| Hyphenated compounds per 1k words | 96 | 25.1 | 19.4 | 12.6 | 11.0 | 8.9 |
| Nominalizations per 1k words | 58 | 21.6 | 21.1 | 17.3 | 21.1 | 20.0 |
| Words per sentence (mean) | | 8.8 | 8.4 | 8.0 | 8.3 | 7.8 |
| Flesch-Kincaid grade | | 6.3 | 4.9 | 4.4 | 4.6 | 4.1 |

![Hyphenated compounds per 1,000 words by STE level, handoff document](/images/ste-jargon-post/handoff-compounds_by_level.png)

**The baseline is still not dense.** Asking for a design document did make the 0% output denser than the explanations: 10.4% stacked noun phrases against 7.0%, and 33 compounds per 1,000 words against 23. That is still about a third of the dense paragraph. The handoff baseline was no denser than the explanations at all. Three test runs with Opus at high effort were no denser either (7.7% and 27.5). This agent does not write that paragraph on its own.

**On what density there was, STE worked.** For the design documents it was a switch again: compounds halve at 25% (33 to 17), and the grade drops two levels at the first step, 7.6 to 5.6. Across the 15 runs the correlation with level is -0.74 for compounds (95% CI -0.94 to -0.28). The handoff documents are the one case that looks like a dial: compounds go 25, 19, 13, 11, 9 (rho of -0.85, 95% CI -0.95 to -0.57).

**One thing went the other way.** The three 100% design documents averaged about 2,700 words against about 2,100 at 0%, and one ran past 9,000 tokens. Short sentences are not the same as a short document. The handoff documents did not show this.

**The meaning checks agree with the explanation task as far as they go.** Silhouette is 0.92 by subsystem and -0.33 by level for the design documents, and 0.88 and -0.33 for the handoff documents. Similarity to the 0% document of the same subsystem averages 0.954 to 0.972 across levels and tasks. With a single 0% run per subsystem there is no noise floor to compare that with and no baseline for identifier retention, so I can't say whether anything was lost.

With one run per cell this is a first look, not a result. I can't separate a level's effect from one run's luck.

## 7. What didn't work

**The idiom list.** My first measure of jargon was a list of 43 engineering idioms ("wire up", "hot path", "under the hood"). Obviously this is not useful: it matched 22 sentences out of 5,998. It was also the wrong target, since a lot of those terms help a human reader. The dense-prose measures replaced it.

**The density axis.** The dense paragraph and its one-sentence plain version say the same thing, so the difference between their embeddings should point from "plain" to "dense". I scored each run by its similarity to the dense version minus its similarity to the plain one. It was flat for the explanations (about +0.02 at every level), flat for the handoff documents (about -0.01), and moved slightly for the design documents (+0.03 at 0%, about zero after). The two anchor texts are about a Kubernetes-style controller and the runs are about Beam, so topic swamps style. I'd call this measure a miss.

**The sentence-level map.** A UMAP of all 5,998 sentences, colored by level, with the idiom sentences marked. Nothing really interesting came out of it. Sentences from every level are mixed through the whole map.

**t-SNE.** With clusters this tight, t-SNE draws each subsystem as a single dot. UMAP makes the same point readably, so that's the one shown above.

**My first identifier score.** It compared 0% runs against a bigger baseline set than everything else, which made 0% look worst. Scoring every run against leave-one-out baseline sets fixed it.

## 8. Caveats

This is by no means exhaustive.

- The agent never produced the target style at baseline. The experiment shows what STE does to mostly plain prose, not to prose like the dense paragraph.
- Three runs per cell for the explanation task and one for the document tasks. Neighboring levels cannot be told apart.
- One agent, one repository, one model per task. The explanation and document tasks used different effort levels, so comparing them is not a controlled comparison of task.
- The dense-prose measures are counts of surface patterns picked to match one example paragraph, so they are only as good as that example.
- My sentence splitter counts list items and run-in labels like "Speed." as sentences, which pulls the average length down at every level.
- "Files read" is parsed from shell commands, because the agent mostly reads through `sed -n`, `cat`, and `grep` rather than the Read tool. It is an approximation.
- Claude has almost certainly seen Beam's source during training. That affects every level equally, but this is a test of explaining code it may partly know.
- Embedding similarity is a proxy for meaning, not a guarantee. I have not read the explanations against the code for errors.

## 9. What I'd do next

- **Give the agent dense text to rewrite.** Hand it the dense paragraph, or a real design doc, and measure how each level rewrites it. This tests the actual target, and it's the one I'm most curious about.
- **Test the compounding claim.** Chain agents: one plans, one implements, one reviews, one writes the PR description. Run it with and without STE and measure the dense-prose counts at each handoff.
- **Use the skills instead of a prompt sentence.** Run the same grid with an STE skill installed and compare against the 80% prompt.
- **Measure comprehension instead of style.** Give each explanation to a fresh agent with no repo access, ask questions with known answers from the code, and score it.
- **Mid-session descriptions.** The dense style also shows up when an agent describes a system partway through a long session. That needs a harness that runs a long task first.
- **More repeats, models, and agents.** Starting with repeats 2 and 3 of the document tasks.

---

*Reproducing this: the harness, prompts, metrics, and figures are at [github.com/PMPiper/asd-ste100-agent-exploration](https://github.com/PMPiper/asd-ste100-agent-exploration). Claude Code 2.1.296. Model `claude-sonnet-5-5`, at medium effort for the explanation task and high effort for the document tasks. Beam commit `fadfc789376137afabab0469bf1e43a0f10a6ad0`. Runs on 2026-10-11 and 2026-10-12 (UTC).*
