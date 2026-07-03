Please review the current `docs-discovery/` design without rewriting or replacing it.

Treat the current v2 Discovery OS design as the baseline.

I want an audit, not a redesign.

Please evaluate it from the following perspectives.

## 1. Real-world research practice alignment

Does KagamiOS v2 match how strong computational/ML researchers actually move from vague intuition to a concrete research direction?

Where does it diverge?

Are those divergences acceptable design choices, or serious flaws?

---

## 2. Agent role / personality design

BMAD appears to use stable roles or personas throughout its workflow.

Should KagamiOS also define stable agent personas, or are role-specific behaviors (Interviewer, Scout, Cartographer, Historian, Skeptic, etc.) sufficient?

Is agent personality important for discovery quality, or is it mostly an implementation detail?

---

## 3. Token-cost efficiency

One of BMAD's major strengths is achieving high quality with relatively low token usage.

How can KagamiOS preserve or improve discovery quality while minimizing token consumption?

Please consider ideas such as:

* sharding
* artifact summaries
* cacheable intermediate artifacts
* retrieval boundaries
* citation-backed compressed representations
* avoiding unnecessary LLM calls

---

## 4. Discovery endpoint

The current design ends with a **Direction Decision**.

However, I wonder whether this is the most useful final artifact.

An alternative is that Discovery produces a curated portfolio of competing research opportunities, where the chosen direction is only one outcome.

For example:

* selected direction
* promising alternatives
* rejected directions (with reasons)
* future opportunities

Would this produce a stronger Discovery OS?

Or is the current Direction Decision already the correct abstraction?

Please critique this idea.

---

## 5. Knowledge structure

The current design is artifact-centered.

However, another possibility is that Discovery naturally constructs a hierarchical knowledge structure such as:

Research Area

↓

Community

↓

Research Group

↓

Research Line

↓

Representative Papers

rather than only a collection of artifacts.

Would modeling this hierarchy explicitly improve KagamiOS?

Or is the current artifact graph already the better abstraction?

Please critique this idea.

---

## Important constraint

Do **not** redesign or replace the current Discovery OS.

Treat the existing design as the baseline.

For every recommendation, classify it as one of:

* Must change
* Should consider
* Optional
* Do not change

Also explain which existing document, principle, artifact, state, or interaction mechanism would be affected.

If you believe the current design should remain unchanged on a topic, please say so explicitly.
