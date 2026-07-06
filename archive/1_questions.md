# Research Operating System Design Discussion

## Background

I am exploring the design of a Research Operating System inspired by the strengths of BMAD.

The goal is **not** to build another literature survey tool.
Instead, I want to formalize the entire research process into a sequence of reproducible states, where each state produces concrete artifacts and naturally leads to the next stage through human decisions.

The system should automate as much reasoning as possible while keeping researchers in control of important decisions.

---

# Motivation

During my own research, I noticed that research rarely begins with a well-defined problem.

Instead, it often starts from an intuition such as:

> "This technique seems promising."
>
> "Very few researchers appear to be working on this direction."
>
> "This idea may outperform existing methods."

For example, I recently started surveying Signature methods because I had the intuition that Signature representations could become useful building blocks for deep learning models.

That intuition gradually evolved into several concrete research directions through literature review.

I would like this reasoning process itself to become reproducible.

---

# Objective

Rather than generating research proposals directly, I want to design a workflow that transforms vague intuitions into concrete research plans.

For example,

Idea

↓

Research Questions

↓

Research Targets

↓

Literature Survey

↓

Historical Narrative

↓

Current Research Landscape

↓

Research Gaps

↓

Hypotheses

↓

Experiment Design

↓

Implementation Plan

↓

Paper Draft

---

# Questions

## 1. Research Workflow

How do leading research organizations (DeepMind, OpenAI, Microsoft Research, FAIR, Stanford, MIT, etc.) actually manage research projects?

What are the major stages from initial intuition to publication?

What artifacts are typically produced at each stage?

Which decisions require human judgment?

---

## 2. State Machine Design

If research were modeled as a state machine similar to BMAD, what would be the appropriate states?

For each state:

- Inputs
- Outputs
- Produced artifacts
- Human decision points
- Validation criteria

---

## 3. Generalization

Which design principles from BMAD are generally applicable to research?

Which parts of software development workflows should NOT be transferred into research workflows?

---

## 4. Human-in-the-loop

Where should the researcher explicitly make decisions?

Where can AI safely automate reasoning?

How should uncertainty be represented instead of forcing early conclusions?

---

## 5. Deliverables

Please propose a high-level architecture for a Research Operating System.

Do not focus on implementation.

Instead, focus on the reasoning process, state transitions, artifacts, and interaction between AI and researchers.