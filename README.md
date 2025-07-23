# BT-RADS Multi-Agent System

A modern, graph-based UI system for BT-RADS (Brain Tumor Reporting and Data System) classification with multi-agent architecture for granular, verifiable clinical decision support.

## Overview

This system breaks down the BT-RADS flowchart into individual agents, each responsible for a specific decision node. The UI presents the algorithm as an interactive graph where clinicians can validate each step, view source evidence, and override decisions when necessary.

## Architecture

- **Frontend**: Next.js 14 + TypeScript + shadcn/ui + React Flow
- **Backend**: FastAPI + LangChain + Ollama
- **Real-time Updates**: WebSockets
- **Database**: PostgreSQL + Redis

## Key Features

- Interactive flowchart visualization
- Step-by-step validation workflow
- Source text highlighting for evidence
- Real-time agent processing status
- Clinical override capabilities
- Comprehensive audit trail

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
btrads-agent-system/
├── backend/
│   ├── agents/           # Individual agent implementations
│   ├── api/              # FastAPI routes
│   ├── models/           # Data models
│   ├── services/         # Business logic
│   └── utils/            # Helper functions
└── frontend/
    ├── app/              # Next.js app directory
    ├── components/       # React components
    ├── lib/              # Utilities
    └── public/           # Static assets
```