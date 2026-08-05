# Prompt Techniques — Concise Guide

---

## 1. Zero-Shot vs. Few-Shot

| Technique | Description |
|-----------|-------------|
| **Zero-Shot** | Asking a question without providing any examples |
| **Few-Shot** | Providing a few relevant examples in the prompt to guide the model |

---

## 2. Reasoning Techniques — CoT, ToT, GoT

Instead of producing an immediate response, these techniques guide the model to **reason step by step** for better outputs.

| Technique | Description |
|-----------|-------------|
| **CoT (Chain of Thought)** | Prompts the model to show **step-by-step reasoning** toward the answer. *("Let's think step by step.")* |
| **ToT (Tree of Thought)** | Explores **multiple reasoning branches** in a tree structure. Each path is **evaluated** and **pruned** or **expanded** using search algorithms (BFS/DFS). |
| **GoT (Graph of Thought)** | Models reasoning as a **graph (DAG)** where thoughts can **merge** (combine) and **branch** (split). Unlike trees, thoughts can **share information** across different branches. |

---

## 3. Self-Consistency

- Generate **multiple reasoning paths** using **Chain of Thought** (with temperature > 0).
- Each path produces a **final answer**.
- Use a **voting mechanism** to select the most **consistent** answer across all runs.
- Best for tasks with a **single correct answer** (math, logic, etc.).

---

## 4. Decomposition Prompting (Divide-and-Conquer)

Breaking down a complex task into smaller, manageable sub-tasks.

| Strategy | Description |
|----------|-------------|
| **Sequential** | Sub-tasks executed **one after another**, each depending on the previous |
| **Parallel** | Sub-tasks executed **independently** at the same time |
| **Hierarchical** | Sub-tasks organized in a **tree-like structure** (high-level → sub-levels) |

---

## Summary — Quick Reference

| Technique | Core Idea |
|-----------|-----------|
| **Zero/Few-Shot** | Examples or no examples |
| **CoT** | Step-by-step reasoning |
| **ToT** | Tree search with pruning |
| **GoT** | Graph with merging and branching |
| **Self-Consistency** | Vote on multiple CoT paths |
| **Decomposition** | Break down into sub-tasks |