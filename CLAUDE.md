# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Multi-Role Dialogue System** project designed to create configurable, multi-role conversation environments. The project is currently in the **planning/documentation phase** - no implementation code exists yet.

The system aims to allow users to orchestrate conversations between multiple virtual roles (teachers, students, experts, officials, etc.) around specific topics using structured dialogue flows.

## Architecture Plan

### Frontend (React)
- **Framework**: React SPA with React Router
- **UI Library**: Ant Design or Material UI
- **Data Fetching**: React Query (or SWR)
- **Key Features**:
  - Role management interface
  - Flow template editor
  - Conversation execution interface
  - History browsing and export

### Backend (Flask)
- **Framework**: Flask REST API
- **Database**: SQLAlchemy ORM (SQLite for dev, MySQL/PostgreSQL for production)
- **Core Services**:
  - FlowEngineService: Dialogue flow orchestration
  - SessionService: Conversation lifecycle management
  - RoleService: Role configuration management
  - LLMService: External model integration
  - HistoryService: Conversation history and export

### Data Models
- **Role**: Character definitions, personality, speaking style
- **FlowTemplate**: Conversation flow templates
- **FlowStep**: Individual conversation steps
- **Session**: Conversation instances
- **Message**: Individual conversation messages

## Current Project Status

**This is a documentation-only project.** The `doc/` directory contains comprehensive specifications including:

- `multi_role_dialog_system_requirements_zh.txt` - Business requirements
- `multi_role_dialog_tech_architecture_react_flask_zh.txt` - Technical architecture
- `multi_role_dialog_backend_requirements_zh.txt` - Backend specifications
- `multi_role_dialog_frontend_requirements_zh.txt` - Frontend specifications
- `multi_role_dialog_communication_spec_zh.txt` - API specifications

## Implementation Roadmap (From Documentation)

### Phase 1: Backend Foundation
1. Set up Flask project structure
2. Define ORM models (Role, FlowTemplate, FlowStep, Session, Message)
3. Implement basic REST API endpoints
4. Create role management functionality
5. Build basic flow template management

### Phase 2: Frontend Foundation
1. Set up React application with routing
2. Implement role management interface
3. Create flow template management pages
4. Build basic API integration

### Phase 3: Core Dialogue Engine
1. Implement FlowEngineService for conversation orchestration
2. Build LLM integration layer
3. Create conversation execution interface
4. Implement session management

### Phase 4: Advanced Features
1. Add loop and conditional logic to flow engine
2. Implement conversation history and export
3. Build advanced UI features
4. Add real-time updates (WebSocket/SSE)

## Development Guidelines

When implementing this project:

1. **Follow the detailed architecture** in `doc/multi_role_dialog_tech_architecture_react_flask_zh.txt`
2. **Use the API specifications** in `doc/multi_role_dialog_communication_spec_zh.txt`
3. **Implement the exact data models** described in the architecture document
4. **Start with the MVP version** - linear conversation flows without complex loops/conditions
5. **Maintain separation of concerns** between the flow engine, LLM service, and UI layers

## Key Technical Decisions (From Architecture)

- **Database**: Use SQLAlchemy ORM for database abstraction
- **LLM Integration**: Abstract LLM calls behind LLMService for flexibility
- **State Management**: Server-side session management with React state for UI
- **API Design**: RESTful endpoints with clear separation by domain
- **Authentication**: Token-based authentication (expandable to JWT)

## File Structure to Implement

Based on the architecture documents, the eventual project structure should be:

```
MultiRoleChat/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── api/
│   │   ├── services/
│   │   └── schemas/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   └── App.js
│   ├── package.json
│   └── public/
└── doc/ (existing)
```

## Notes for Future Claude Instances

- **This project needs to be built from scratch** using the comprehensive documentation in `doc/`
- **Start by reading the architecture document** to understand the complete system design
- **Implement the exact API structure** specified in the communication specifications
- **Follow the data models** outlined in the technical architecture
- **The system is designed for Chinese users** - all requirements documents are in Chinese