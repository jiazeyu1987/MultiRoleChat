# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Multi-Role Dialogue System** project designed to create configurable, multi-role conversation environments. The system allows users to orchestrate conversations between multiple virtual roles (teachers, students, experts, officials, etc.) around specific topics using structured dialogue flows with advanced features like loops, conditions, and real-time execution.

## Current Architecture

### Frontend (React + TypeScript + Vite)
- **Framework**: React 18.2.0 with TypeScript, built with Vite
- **UI Library**: Tailwind CSS 3.3.0 with Lucide React icons
- **Key Components**:
  - `MultiRoleDialogSystem.tsx` (63KB) - Main application with full UI
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
  - **`flow_engine_service.py`** (24KB) - Advanced dialogue flow orchestration with loops/conditions
  - **`flow_service.py`** (16KB) - Flow template management
  - **`session_service.py`** (18KB) - Conversation lifecycle management
  - **`message_service.py`** (16KB) - Message handling and management
  - **`role_service.py`** (2KB) - Role configuration management
  - **LLM Services** (`services/llm/`):
    - `simple_llm.py` (15KB) - Simplified Anthropic Claude integration
    - `manager.py` (13KB) - LLM service management
    - `conversation_service.py` (8KB) - Conversation-specific LLM operations
  - **Monitoring Services**:
    - `health_service.py` (18KB) - System health monitoring
    - `monitoring_service.py` (17KB) - Performance metrics

### Data Models (`backend/app/models/`)
- **`role.py`** - Character definitions with unified prompt field
- **`flow.py`** - FlowTemplate and FlowStep models with JSON configs
- **`session.py`** - Session management with role assignments
- **`message.py`** - Individual messages with context tracking

### API Layer (`backend/app/api/`)
- **RESTful endpoints** with Flask-RESTful:
  - `/api/roles` - Role management
  - `/api/flows` - Flow template operations
  - `/api/sessions` - Session management
  - `/api/messages` - Message operations
  - `/api/llm` - LLM conversation endpoints
  - `/api/monitoring` - System monitoring

## Development Commands

### Backend Setup and Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set up environment (copy from .env.example)
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python run.py init-db

# Create system built-in roles and flows
python run.py create-builtin-roles
python run.py create-builtin-flows

# Run development server (default port 5000)
python run.py

# Production deployment
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Frontend Setup and Development
```bash
cd fronted  # Note: directory name is "fronted", not "frontend"

# Install dependencies
npm install

# Run development server (port 3000, proxies /api to backend:5000)
npm run dev

# Build for production (runs TypeScript compiler first)
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

**Frontend-specific files:**
- `vite.config.ts` - Vite configuration with API proxy to backend:5000
- `tsconfig.json` - TypeScript strict mode configuration
- `src/utils/errorHandler.ts` - Centralized API error handling utilities

### Quick Development Workflow
```bash
# Terminal 1: Start backend
cd backend && python run.py

# Terminal 2: Start frontend (auto-reloads)
cd fronted && npm run dev

# Access application at http://localhost:3000
# API available at http://localhost:3000/api/* (proxied)
# Health check: http://localhost:3000/api/health
```

### Database Management Commands
```bash
cd backend

# Check database status
python check_db.py

# Clean database (use with caution)
python clean_db.py

# Apply migrations
python apply_migration.py

# Clear all flow templates and steps
python clear_templates.py

# Reset templates to built-in only
python reset_templates.py
```

### Environment Configuration
Key environment variables (copy from `backend/.env.example`):
- `FLASK_ENV` - Environment (development/production)
- `SECRET_KEY` - Flask secret key for sessions
- `DATABASE_URL` - Database connection string (default: sqlite:///app.db)
- `OPENAI_API_KEY` - OpenAI API key for LLM integration
- `OPENAI_BASE_URL` - OpenAI API base URL (optional)
- `OPENAI_MODEL` - OpenAI model to use (default: gpt-3.5-turbo)
- `OPENAI_MAX_TOKENS` - Max tokens for OpenAI responses (default: 1000)
- `OPENAI_TEMPERATURE` - OpenAI temperature setting (default: 0.7)
- `OPENAI_TIMEOUT` - OpenAI request timeout in seconds (default: 30)
- `OPENAI_MAX_RETRIES` - OpenAI request retry attempts (default: 3)
- `LLM_DEFAULT_PROVIDER` - Default LLM provider (openai)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_FILE` - Log file path (default: logs/app.log)
- `DEFAULT_PAGE_SIZE` - Pagination settings (default: 20)
- `MAX_PAGE_SIZE` - Maximum allowed page size (default: 100)

### Testing and Validation
No automated test suite is currently configured. Manual testing can be done via:
- **Frontend**: LLMTestPage component at `/llm-test` route for API testing
- **Backend**: Health check endpoint at `/api/health` for system status
- **Integration**: Use built-in flow templates and roles for end-to-end testing
- **Database**: Use `python check_db.py` to verify database integrity
- **LLM Integration**: Test files like `test_llm_integration.py` for OpenAI connectivity

## Key Technical Features

### 1. Advanced Flow Engine
- JSON-based flow configuration with loops and conditions
- Multi-step conversation orchestration with context management
- Dynamic role assignment and speaker switching
- Flow template copying and versioning
- Termination condition configuration

### 2. LLM Integration
- **OpenAI API integration** as primary provider (configured via environment variables)
- Support for multiple LLM providers via service abstraction layer
- Comprehensive request logging and monitoring through `services/llm/`
- Async processing with timeout and retry handling
- Context-aware conversation management with message threading

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

1. **LLM Integration**: The system supports both Anthropic Claude and OpenAI integration via `services/llm/`. Configure API keys in environment variables.

2. **Flow Engine**: Advanced dialogue flows are configured using JSON structures stored in the database. The flow engine (`services/flow_engine_service.py`) handles complex logic including loops, conditions, and termination criteria.

3. **Database Management**: Use Flask-Migrate for schema changes. Built-in roles and flow templates can be created with the provided CLI commands.

4. **API Architecture**: All endpoints follow RESTful patterns with proper HTTP methods, status codes, and JSON responses with consistent error handling.

5. **Monitoring**: The system includes comprehensive health monitoring and LLM request logging. Check `/api/health` for system status and `logs/` directories for detailed logs.

6. **Frontend Note**: The frontend directory is named `fronted` (not `frontend`) - this is intentional and should be preserved.

7. **Role Model**: The Role model uses a unified `prompt` field that contains all role information (description, style, constraints, focus points).

## Architecture Patterns

### Service Layer Organization
- **Core Services**: Business logic separated by domain (roles, flows, sessions, messages)
- **LLM Services**: Isolated LLM integration with provider abstraction
- **Monitoring Services**: Health checks and performance tracking

### Data Flow
1. Frontend sends REST API requests (React components at `fronted/src/MultiRoleDialogSystem.tsx`)
2. Vite dev server proxies `/api/*` requests to Flask backend on port 5000
3. API layer validates and forwards to services (`backend/app/api/`)
4. Services orchestrate business logic and LLM calls (`backend/app/services/`)
5. Data persisted through SQLAlchemy models (`backend/app/models/`)
6. Real-time status updates via polling (health checks at `/api/health`)

### Key Technical Decisions

- **LLM Provider**: OpenAI API integration with provider abstraction for extensibility
- **Database**: SQLAlchemy ORM with JSON fields for flexible flow configurations
- **Frontend**: React + TypeScript with Vite for fast development and hot reloading
- **API Design**: Flask-RESTful with consistent error handling and CORS support
- **Development**: Proxy configuration routes frontend API calls to backend during development
- **Monitoring**: Built-in health checks and performance metrics with detailed logging

## Additional Documentation

- **`doc/`** and **`doc_glm/`** directories contain specification and implementation documents
- **`会话剧场.md`** - Latest conversation theater functionality documentation
- **`LLM调用方式对比分析.md`** - LLM integration comparison analysis
- **`会话执行下一步功能实现总结.md`** - Next-step execution implementation summary
- Various test HTML files (`debug_*.html`, `test_*.html`) for manual testing and debugging

Note: These documents were used for planning and are superseded by the implemented system, but may be useful for understanding design intent and recent improvements.