# Review 2 — Agent Roles vs. Stable Personas

**Question:** BMAD uses stable roles/personas throughout its workflow. Should KagamiOS define stable agent personas, or are role-specific behaviors (Interviewer, Scout, Cartographer, Historian, Skeptic) sufficient? Is agent personality important for discovery quality, or mostly an implementation detail?

**Verdict in one paragraph.** Separate the two things BMAD's personas bundle. The *behavioral contract* (a stable, named role with fixed responsibilities, fixed inputs, and a fixed epistemic stance) is genuinely quality-bearing, and the baseline under-specifies it — one paragraph in `bmad_transfer.md` §3.5 is all there is. The *personality* (a named character with a voice and a persona) is an implementation detail in BMAD and would be mildly **harmful** in KagamiOS, because likability produces deference and deference is precisely the failure E6 exists to prevent. Keep the baseline's stance ("modes of critique, not simulated colleagues" — **Do not change**), and strengthen it with explicit role charters (**Should consider, S4**).

---

## 1. What BMAD's personas actually do — three functions, unbundled

| Function | What it buys BMAD | Does KagamiOS need it? |
|---|---|---|
| **Behavioral spec.** A stable persona is a compressed, reusable behavioral contract: the Analyst always interrogates, never architects; the PM writes what/why, never how. | Consistency across sessions; predictable outputs; less prompt drift | **Yes** — and the baseline has the role list but not the contracts |
| **Context discipline.** Each agent starts fresh, reads only its charter + designated inputs. This — not the personality — is where BMAD's token frugality and role fidelity actually come from | Small contexts, no cross-stage bleed | **Yes** — this belongs to the context-loading contract (M1, review 3) |
| **Character.** Names, personality, a simulated colleague to talk to | User engagement; makes a form feel like a conversation | **No** — see §3 |

The user's question treats these as one decision; they are three. KagamiOS should adopt the first two and decline the third.

## 2. What the baseline has, and where it is thin

`bmad_transfer.md` §3.5 names five roles — Interviewer (the kernel, promoted to central), Scout, Cartographer, Historian, Skeptic — and inherits v1's caution that they are modes of critique. That is the right cast and the right caution. What is missing is the binding between roles and the design's own enforcement machinery:

- **Generation windows (E6) are role-shaped but not role-assigned.** "The AI may not draft direction-shaped content before Gaps are accepted" — which role does that constrain, and which role enforces the quarantine into `premature_ideas`? If every role is the same underlying model with the same context, the window is a convention, not a mechanism.
- **The Skeptic's independence is asserted, not arranged.** A Skeptic that shares full context with the drafting role tends to critique within the draft's own frame. Its charter should *forbid* it from reading the drafting rationale — attack the artifact, not the argument for it.
- **Evidence obligations differ by role but are unstated.** The Scout reports what exists and must never interpret; the Cartographer proposes partitions and must always offer the alternative cut (this is also DQ3's mitigation); the Historian must cite primary sources for every "abandoned because" claim.

**Recommendation S4 (Should consider).** Add a role-charter section (in `bmad_transfer.md` or a small `roles.md`): per role — mission, permitted outputs, **forbidden outputs**, evidence obligations, which generation windows bind it, and what context it is given (tying into M1). This is a specification of what the baseline already believes, not a design change. Affected: `bmad_transfer.md` §3.5; touches E6 enforcement and DQ3.

## 3. Why character-personas would hurt this design specifically

BMAD can afford charming personas because its user's job is to **correct agents on facts** ("no, the login flow works like this"). KagamiOS's user must **resist agents on taste** — decline the AI's clustering, override its gap verdicts, diverge from its candidate ranking. The design's own threat model (E6: homogenization; DQ3: the menu is also an anchor) says the danger is the researcher deferring to fluent AI output. Persona design increases deference by construction: that is what it is *for*. A warm, named Interviewer makes "skip — use your default" feel like letting a colleague down; an authoritative Historian makes its evolution narrative harder to doubt. Every unit of parasocial trust the persona earns is subtracted from the researcher's independence, which E7 says is the actual product.

There is also a cheaper reading of the same evidence: BMAD's quality does not come from Mary-the-Analyst having a personality; it comes from the Analyst having a *job description and a bounded context*. The personality is packaging. Import the job description; leave the packaging.

**Do not change (D3):** the baseline's refusal of simulated colleagues. If anything, the charters of S4 should state the anti-persona rule explicitly, so an implementer does not "helpfully" add character later.

## 4. The one thing personality-adjacent design does buy: legibility

A genuine cost of the no-persona stance: to the researcher, all system output arrives in one undifferentiated voice, so adversarial content (Skeptic) blends into descriptive content (Historian) and the researcher loses the social license to disagree that a visibly adversarial interlocutor grants. Real seminar culture solves this with roles, not personalities — "let me play devil's advocate" changes the footing of the conversation without anyone pretending to be someone.

**Recommendation O1 (Optional).** Label output by role, and let the Skeptic's register be visibly adversarial (objections, not observations). This is presentation, not persona: no names, no character, no continuity of "self." It restores the legibility benefit at zero anchoring cost.

## 5. Answer to the question as asked

- Stable personas in the BMAD sense: **no** — and this is a considered rejection, not an omission.
- Role-specific behaviors: **sufficient in kind, under-specified in degree** — promote the five roles from a list to charters (S4).
- Is personality important for discovery quality? **The contract half is; the character half is an implementation detail with negative expected value here.** The quality-bearing properties — consistency, bounded context, epistemic stance, adversarial license — are all obtainable without personas, and the baseline's architecture already points that way.
