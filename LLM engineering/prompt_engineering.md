# Prompt Engineering — Concise Guide

---

## 1. Core Components of an Effective Prompt

| Component | Description |
|-----------|-------------|
| **Role** | Who the model should act as |
| **Context** | What the model needs to know |
| **Constraints** | What the model must avoid |
| **Output Format** | How the response should be structured |

---

## 2. Why Output Format Instructions Matter

- LLMs are **non-deterministic** — same prompt can yield different structures across calls.
- Without format guidance, outputs vary (bullet lists, prose, markdown, etc.).
- Explicit format ensures **consistent, machine-parseable** results.

---

## 3. Anatomy of a Prompt

| Message Type | Purpose |
|--------------|---------|
| **System** | Sets identity, rules, and persistent constraints |
| **User** | The specific task or question |
| **Assistant** | The model's response (or a partial example to guide it) |

---

## 4. Why "You are an expert X" Works

- LLMs are trained on massive, diverse text — from **novice** to **expert** level.
- Saying "expert" shifts the model's probability distribution **toward high-quality, authoritative sources** (official docs, Stack Overflow, etc.).
- It's a simple but effective way to **bias the output** toward better reasoning and phrasing.

---

## Summary — Minimal Takeaway

> **Role + Context + Constraints + Format** = reliable prompts.  
> Always specify structure, and use **expert framing** to lift output quality.