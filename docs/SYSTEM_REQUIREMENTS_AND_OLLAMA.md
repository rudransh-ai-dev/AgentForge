# System Requirements & Setup Guide

This document outlines the hardware and software needed to run the AI Agent IDE. 

## 1. Hardware Requirements
For optimal performance (as demonstrated), the system is designed for high-end workstations.

### 1.1 Minimum Specs (for "Lite" use)
- **CPU**: 6-core modern processor (Intel i5/i7 or AMD Ryzen 5/7).
- **RAM**: 16 GB DDR4/DDR5.
- **GPU**: 8 GB VRAM (Nvidia RTX series recommended).
- **Storage**: 50 GB SSD space (for AI model weights).

### 1.2 Recommended Specs (The "Supercomputer" Experience)
- **GPU**: **Nvidia RTX 5070 Ti (16 GB VRAM)** or higher.
- **RAM**: 32 GB+.
- **Storage**: NVMe M.2 SSD.

---

## 2. Software Prerequisites
The system is built to be platform-independent but works best on Linux (Ubuntu/Debian) or Windows (via WSL2).

1. **Ollama**: The core LLM engine. [Download here](https://ollama.com).
2. **Python 3.10+**: For the backend orchestration.
3. **Node.js 18+**: For the frontend interface.

---

## 3. Ollama Setup & Model Roster
The AI-IDE uses a fleet of specialized models. After installing Ollama, you must pull these models using the terminal:

### 3.1 Core Model List
Run these commands in your terminal:
```bash
# The Router/Manager
ollama pull llama3.1:8b

# The Writing Specialists (Drafting)
ollama pull gpt-oss:20b
ollama pull qwen2.5-coder:14b

# The QA Tester (Deep Reasoning)
ollama pull deepseek-r1:8b

# The Architect (Deep Think Mode)
ollama pull codestral:22b

# The Researcher (Knowledge Agent)
ollama pull qwen2.5:14b
```

### 3.2 Offline Installation (Pendrive)
If you are moving models via pendrive, the model blobs are typically stored in:
- **Linux**: `~/.ollama/models`
- **Windows**: `C:\Users\<User>\.ollama\models`

---

## 4. Project Setup
1. **Extract Code**: Copy the project folder from the pendrive.
2. **Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm install
   ```

## 5. Running the System
The easiest way is to use the provided root script:
```bash
./start.sh
```
This will start both the Python backend (Port 8000) and the React frontend (Port 5173).
