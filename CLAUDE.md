# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Multi-Role Dialogue System** project designed to create configurable, multi-role conversation environments. The project is **FULLY IMPLEMENTED** and production-ready.

The system allows users to orchestrate conversations between multiple virtual roles (teachers, students, experts, officials, etc.) around specific topics using structured dialogue flows with advanced features like loops, conditions, and real-time execution.

## Current Architecture

### Frontend (React + TypeScript + Vite)
- **Framework**: React 18.2.0 with TypeScript, built with Vite
- **UI Library**: Tailwind CSS 3.3.0 with Lucide React icons
- **Key Components**:
  - `MultiRoleDialogSystem.tsx` (60KB) - Main application with full UI
  - `LLMTestPage.tsx` (10KB) - LLM testing interface
  - Theme system with 5 color schemes
- **Features**:
  - Role management interface
  - Flow template editor with JSON configuration
  - Real-time conversation execution
  - Message history and export functionality
  - LLM integration testing

### Backend (Flask + SQLAlchemy)
- **Framework**: Flask REST API with application factory pattern
- **Database**: SQLAlchemy ORM with migrations (SQLite default, PostgreSQL/MySQL support)
- **Core Services** (`backend/app/services/`):
  - **`flow_engine_service.py`** (22KB) - Advanced dialogue flow orchestration with loops/conditions
  - **`session_service.py`** (18KB) - Conversation lifecycle management
  - **`message_service.py`** (16KB) - Message handling and management
  - **`flow_service.py`** (14KB) - Flow template management
  - **`role_service.py`** (2KB) - Role configuration management
  - **LLM Services** (`services/llm/`):
    - `simple_llm.py` (15KB) - Simplified Anthropic Claude integration
    - `manager.py` (13KB) - LLM service management
    - `conversation_service.py` (8KB) - Conversation-specific LLM operations
  - **Monitoring Services**:
    - `health_service.py` (18KB) - System health monitoring
    - `monitoring_service.py` (17KB) - Performance metrics

### Data Models (`backend/app/models/`)
- **`role.py`** - Character definitions, personality, speaking style
- **`flow.py`** - FlowTemplate and FlowStep models with JSON configs
- **`session.py`** - Session management with role assignments
- **`message.py`** - Individual messages with context tracking

### API Layer (`backend/app/api/`)
- **RESTful endpoints** with Flask-RESTful:
  - `/api/roles` - Role management (9KB)
  - `/api/flows` - Flow template operations (11KB)
  - `/api/sessions` - Session management (15KB)
  - `/api/messages` - Message operations (14KB)
  - `/api/llm` - LLM conversation endpoints (12KB)
  - `/api/monitoring` - System monitoring (14KB)

## Development Commands

### Backend Setup and Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set up environment (copy from .env.example)
cp ../.env.example .env

# Initialize database
python run.py init-db

# Create system built-in roles and flows
python run.py create-builtin-roles
python run.py create-builtin-flows

# Run development server
python run.py

# Production deployment
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Frontend Setup and Development
```bash
cd fronted  # Note: directory name is "fronted", not "frontend"

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Environment Configuration
Key environment variables (see `.env.example`):
- `ANTHROPIC_API_KEY` - Required for Claude integration
- `DATABASE_URL` - Database connection string
- `FLASK_ENV` - Environment (development/production)
- `LOG_LEVEL` - Logging level
- `API_HOST` / `API_PORT` - Server binding configuration

## Key Technical Features

### 1. Advanced Flow Engine
- JSON-based flow configuration with loops and conditions
- Multi-step conversation orchestration with context management
- Dynamic role assignment and speaker switching
- Flow template copying and versioning

### 2. LLM Integration
- **Simplified Anthropic Claude integration** with automatic API key detection
- Comprehensive request logging and monitoring
- Async processing with timeout and retry handling
- Context-aware conversation management

### 3. Monitoring & Health
- Real-time system health checks (`/api/health`)
- Performance metrics tracking and history
- LLM request monitoring with detailed logging
- Component-level health trend analysis

### 4. Data Management
- SQLAlchemy ORM with proper migrations
- JSON configuration storage for flexible data structures
- Message threading and context tracking
- Session state management with role assignments

## Development Guidelines

When working with this project:

1. **LLM Integration**: The system uses simplified Anthropic Claude integration via `services/llm/simple_llm.py`. It automatically detects API keys from environment or Claude CLI configuration.

2. **Flow Engine**: Advanced dialogue flows are configured using JSON structures stored in the database. The flow engine (`services/flow_engine_service.py`) handles complex logic including loops and conditions.

3. **Database Management**: Use Flask-Migrate for schema changes. Built-in roles and flow templates can be created with the provided CLI commands.

4. **API Architecture**: All endpoints follow RESTful patterns with proper HTTP methods, status codes, and JSON responses with consistent error handling.

5. **Monitoring**: The system includes comprehensive health monitoring and LLM request logging. Check `/api/health` for system status and `logs/` directories for detailed logs.

6. **Frontend Note**: The frontend directory is named `fronted` (not `frontend`) - this is intentional and should be preserved.

## Architecture Patterns

### Service Layer Organization
- **Core Services**: Business logic separated by domain (roles, flows, sessions, messages)
- **LLM Services**: Isolated LLM integration with fallback mechanisms
- **Monitoring Services**: Health checks and performance tracking

### Data Flow
1. Frontend sends REST API requests
2. API layer validates and forwards to services
3. Services orchestrate business logic and LLM calls
4. Data persisted through SQLAlchemy models
5. Real-time status updates via polling

### Key Technical Decisions

- **LLM Provider**: Focused on Anthropic Claude with simplified integration
- **Database**: SQLAlchemy ORM with JSON fields for flexible configuration
- **Frontend**: React + TypeScript with Vite for fast development
- **API Design**: Flask-RESTful with consistent error handling
- **Monitoring**: Built-in health checks and performance metrics

## Original Documentation

The `doc/` directory contains the original specification documents:
- Business requirements, technical architecture, and API specifications
- These documents were used for initial planning but have been superseded by the implemented system
- Refer to these for understanding the original design intent