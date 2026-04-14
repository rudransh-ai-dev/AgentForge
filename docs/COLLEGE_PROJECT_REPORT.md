# Project Report: Agent-Oriented Intelligent Development Environment (AI-IDE)

**Course**: BCA / B.Tech / Computer Science Final Year Project
**Developed by**: Rudransh
**Academic Year**: 2025-2026

---

## 1. Abstract
The AI-IDE is a production-grade, local-first multi-agent orchestration system designed to automate software development lifecycles. Unlike traditional cloud-based AI tools, this system operates entirely on local infrastructure using the **Ollama** inference engine. It employs a specialized fleet of 10+ autonomous agents—including a Manager, Writer, Editor, and Tester—to transform natural language prompts into fully functional, multi-file software projects. The system features a custom VRAM-aware scheduler to manage large language model (LLM) transitions on high-end hardware, ensuring deterministic and resource-optimized execution.

## 2. Introduction
In the era of Generative AI, software development is shifting from manual coding to "Agentic Orchestration." However, reliance on proprietary cloud APIs (like OpenAI or Anthropic) introduces latency, cost, and privacy risks. The AI-IDE addresses these challenges by bringing the power of an "AI Coder Fleet" to a local workstation. This project demonstrates how multiple specialized models can collaborate through a structured pipeline to solve complex architectural problems without any internet dependency.

## 3. Objectives
- **Local-First Inference**: Implement a system that requires zero API keys and zero internet access.
- **Multi-Agent Collaboration**: Design a 3-stage pipeline (Drafting → Refinement → Validation) where different models check each other's work.
- **Resource Management**: Develop a VRAM Scheduler to handle massive models (up to 27B parameters) on a single workstation without crashing the system.
- **Actionable Output**: Produce real, runnable code in a persistent workspace rather than just text responses.

## 4. System Architecture
The system is built on a **Modular Micro-Agent Architecture**:

### 4.1 The Manager (The Brain)
- **Model**: `llama3.1:8b`
- **Function**: Classifies user intent, breaks down complex tasks into steps, and routes work to the appropriate specialist.

### 4.2 The Production Pipeline
1. **Writer (Stage 1)**: Uses `gpt-oss:20b` or `codestral:22b` to draft the initial code and folder structure.
2. **Editor (Stage 2)**: Uses `qwen2.5-coder:14b` to refine the draft, fix syntax errors, and apply best practices.
3. **Tester (Stage 3)**: Uses `deepseek-r1:8b` to perform a "QA Review" and provide feedback for another round of editing if bugs are found.

### 4.3 VRAM-Aware Scheduling
A critical component of the system is the **FIFO VRAM Scheduler**. Since LLMs are memory-intensive, the scheduler ensures that:
- Small models (<9GB) can co-reside in memory for speed.
- Large models (>10GB) get "Exclusive Access," meaning the scheduler automatically unloads other models to prevent GPU memory overflow.

## 5. Technical Stack
- **Backend**: Python 3.10+, FastAPI, Asyncio.
- **Frontend**: React.js, Vite, ReactFlow (for canvas visualization), Zustand (state management).
- **Inference**: Ollama (Local LLM server).
- **Database**: SQLite (for run tracking and metrics).

## 6. Implementation Highlights
- **Real-Time Canvas**: A visual ReactFlow interface where users can watch the agents "light up" while they work.
- **Deep Think Mode**: A high-performance toggle that triggers the `codestral:22b` 17.5B parameter model for architecture-level reasoning.
- **Researcher Agent**: A specialized agent for non-coding tasks (explanations, comparisons, documentation).

## 7. Results and Performance
On a high-end workstation (RTX 5070 Ti), the system achieves:
- **Direct Mode Latency**: < 3 seconds.
- **Full Pipeline Latency**: 12–25 seconds depending on code complexity.
- **Success Rate**: High accuracy in generating Python/JavaScript boilerplate and standalone utilities.

## 8. Conclusion
The AI-IDE demonstrates that a high-performance development environment can be built entirely on local hardware. By coordinating multiple specialized agents, we achieve a level of code quality that surpasses single-model interactions. This project serves as a blueprint for the future of private, secure, and autonomous software engineering.

---
**Verified for Submission**
**Date**: April 14, 2026
