created: 2026-10-11

# What does "80% of the way to ASD-STE100" actually do?

> The canonical ingress path is a close-bounded, single-writer admission seam: the UI emits a work-request envelope into the durable intent ledger, which serves as the authoritative source of truth for desired-state materialization. A leader-fenced reconciler then performs level-triggered convergence over the bounded work set, hydrating each intent into a hermetic, owner-scoped execution unit.

All that says is "the UI saves the request to a database, and a controller picks it up and runs it as a pod."

If you use coding agents every day you have probably read a sentence like that, said "wait, what?" and started a `/btw` or `/side` to figure out what it actually meant. The agent may be technically correct, but it is talking the way an engineer might write an ambitious design doc for other engineers already familiar with what needs to be built. But even still, "don't use a five-dollar word when a fifty-cent word will do."

While I synthesized that particular example, I have seen AI outputs not too far off from it. What makes it distracting rather than helpful:

- **Invented compound terms.** "Durable intent ledger" and "admission seam" sound like established concepts but aren't, so you waste time wondering whether you're missing something.
- **Stacked qualifiers.** "Close-bounded, single-writer" and "hermetic, owner-scoped" pile adjectives on a noun without saying what any of them rules out.
- **Abstract verbs for simple actions.** "Hydrating" and "materialization" stand in for "creates" and "writes".
- **No concrete nouns.** It never names a database, a pod, or an HTTP call, so you can't check it against real code.

To be clear, I'm not complaining about engineering idioms like "hot path" or "wire up". I find that language to actually be very approachable.

## The tip

A few weeks ago Andrej Karpathy posted [some tips](https://x.com/karpathy/status/2105819303471976479) on understanding the outputs of language models. The first one was about understanding through text:

> "Ask your LLM to explain something in ASD-STE100, it's a controlled language specification originally developed for aerospace maintenance documentation. [...] Sometimes I've tried to soften it a bit e.g. ask for '80% of the way to ASD-STE100' because the spec is quite stringent."

He continues to suggest "even better" approaches that build on the previous. Text, then diagrams, then interactive web pages, then fully custom explainer videos. His summary is that as agents do more of the legwork, more of our work moves up into oversight and understanding. We're all TLM's now.

[ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/) (STE) is a controlled language from the aerospace industry. It came out of the 1980s so that maintenance technicians, many of them non-native English speakers, could not misread a manual. It has two parts: 53 writing rules and a dictionary of about 900 approved words where each word has one meaning and one part of speech. A few of the rules people tend to remember:

- Keep procedural sentences to 20 words or fewer and descriptive sentences to 25 or fewer.
- Use the active voice.
- Write one instruction per sentence.
- Use one word for one thing, and no synonyms.

This idea has existed prior to Andrej's post. [SimpleEnglish](https://github.com/AminBlg/SimpleEnglish) and [asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) both package STE as an agent skill. I've been trying the simple prompt approach like Andrej.

This approach is interesting because of the "80%". A percentage of a writing standard is not something you can quantify easily. Does the agent treat it as a dial, where 50% is halfway between normal and strict, or is it more like an on/off switch?

## What I tried

I only looked at text in and text out. No skills, no hooks, no output styles. I asked Claude Code to explain part of a codebase I wasn't familiar with, using a templated prompt, and changed one sentence at the end of the prompt:

```text
You are in a checkout of Apache Beam. Explain how the {name} subsystem in
sdks/python/apache_beam/{path} works to an experienced software engineer who
has never used Beam. Cover what problem it solves, the main classes and how
data flows through them, and anything surprising. Only read code under
sdks/python. Do not modify any files.
---
0%:   (nothing added)
25%:  Write your explanation about 25% of the way to ASD-STE100 Simplified Technical English.
50%:  ... about 50% of the way ...
80%:  ... about 80% of the way ...  (Karpathy's setting)
100%: Write your explanation in ASD-STE100 Simplified Technical English.
```

That's 5 levels × 3 subsystems of [Apache Beam](https://github.com/apache/beam)'s Python SDK × 3 repeats = 45 runs, with Sonnet 5.5 at medium effort. Each run was a fresh headless session with my personal CLAUDE.md, skills, and memory switched off, so my setup couldn't leak a style preference into the results. The [companion post](/writing/ste-experiment-report/) has the harness, the isolation checks, and the statistics.

## What it looks like

Here is the same part of one explanation at each level: the opening of the "what problem does it solve" section for Beam's Coders subsystem. Each excerpt is from the run closest to the middle of its group, not the best-looking one.

**0%**

> Beam pipelines are distributed. A `PCollection` is a logical collection of elements, but those elements get physically moved around: shuffled for a `GroupByKey`, written to a spill file, or sent over gRPC between the SDK worker and the runner. The runner is often not Python. It might be Java, Go, or Dataflow's service.

**25%**

> Beam is a framework for data pipelines. A pipeline is a graph of steps. Each step reads a PCollection, which is a distributed collection of elements, and writes another one. At some points the elements must become bytes:

**50%**

> Beam is a framework for distributed data pipelines. A pipeline is a graph of steps. Each step reads a collection of elements (a `PCollection`) and writes another one. The elements must leave the Python process in many cases:

**80%**

> Beam runs your pipeline on many machines. Data moves between steps as `PCollection`s. A runner must sometimes send elements over a network, write them to disk, or group them by key. For this, it needs a way to turn each Python object into bytes and back.

**100%**

> Beam runs a data pipeline on many machines. Elements of a collection (a `PCollection`) must cross process borders. They are written to disk, sent over the network, and grouped by key. Python objects cannot do this on their own, so each element must become bytes and later become an object again.

The 0% version assumes you know exactly what a shuffle and a spill file are. Every other version builds up. I can distinguish 0% from non-0%, but I can't really distinguish one non-0% from another.

## What changed, in numbers (n=9)

| | 0% | 25% | 50% | 80% | 100% |
|---|---|---|---|---|---|
| Words (median) | 1117 | 1156 | 1146 | 1110 | 1157 |
| Words per sentence | 9.3 | 8.6 | 8.8 | 8.5 | 8.3 |
| Passive sentences | 9.3% | 7.9% | 7.6% | 5.4% | 5.2% |
| Reading grade ([Flesch-Kincaid](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests)) | 6.1 | 5.0 | 4.7 | 4.8 | 4.5 |
| Hyphenated compounds per 1,000 words | 23.1 | 13.8 | 12.4 | 12.1 | 10.5 |

![Sentence length by STE level](/images/ste-jargon-post/explanation-sentence_length_by_level.png)

**It is more like a switch than a dial.** Almost everything that moves, moves between 0% and 25%, and then mostly stays put. The reading grade drops a full level at the first step and about half a level over the next four. Compounds like "leader-fenced" roughly halve at 25%. Passive voice is the one row that keeps falling, though with nine runs per level I can't tell neighboring steps apart.

**It does not make the answer shorter.** The median explanation is about 1,100 words at every level. The agent wrote the same amount in slightly shorter sentences.

**The baseline already writes plainly.** Only 0.5% of the 0% sentences were over STE's 25-word limit. This test shows what STE does to mostly plain writing. It can't show what STE does to an answer like my initial example because this agent never wrote anything like it with my simple harness.

## Takeaways

- **Don't agonize over the number.** 80% isn't special. In this test 25% got most of the effect, and I could not tell the levels above it apart.
- **Don't expect shorter answers.** If you want it shorter, ask for that separately.
- **Try it where the writing is actually dense.** My worst examples come from longer agent sessions on a different setup than the one I tested, and that is where I'd expect the bigger payoff. I haven't measured it (yet!).

---

*The harness, the isolation checks, the statistics, and the things that didn't work are in the [companion post](/writing/ste-experiment-report/). The code is at [github.com/PMPiper/asd-ste100-agent-exploration](https://github.com/PMPiper/asd-ste100-agent-exploration).*

*[[TODO: optional one-line note on how you used Claude while writing this post.]]*
