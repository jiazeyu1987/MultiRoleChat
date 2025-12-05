# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **frontend** component of a Multi-Role Dialogue System project designed to create configurable, multi-role conversation environments. The system allows users to orchestrate conversations between multiple virtual roles (teachers, students, experts, officials, etc.) around specific topics using structured dialogue flows with advanced features like loops, conditions, and real-time execution.

## Frontend Architecture (React + TypeScript + Vite)

### Technology Stack
- **Framework**: React 18.2.0 with TypeScript, built with Vite
- **UI Library**: Tailwind CSS 3.3.0 with Lucide React icons
- **Development**: Vite dev server with API proxy to backend on port 5000
- **Build**: TypeScript compilation followed by Vite build

### Key Components
- `MultiRoleDialogSystem.tsx` (63KB) - Main application with full UI
- `LLMTestPage.tsx` (10KB) - LLM testing interface
- `theme.tsx` - Theme system with 5 color schemes
- `App.tsx` - Root component wrapper
- `main.tsx` - React application entry point

### Core Features
- Role management interface
- Flow template editor with JSON configuration
- Real-time conversation execution
- Message history and export functionality
- LLM integration testing
- Theme system with multiple color schemes

### Development Configuration
- `vite.config.ts` - Vite configuration with API proxy to backend:5000
- `tsconfig.json` - TypeScript strict mode configuration
- `tailwind.config.js` - Tailwind CSS configuration
- No ESLint configuration (relies on external linting)

## Development Commands

### Frontend Development
```bash
# Navigate to frontend directory (note: directory name is "fronted", not "frontend")
cd fronted

# Install dependencies
npm install

# Run development server (port 3000, proxies /api to backend:5000)
npm run dev

# Build for production (runs TypeScript compiler first)
npm run build

# Preview production build
npm run preview

# Lint code (if ESLint is configured)
npm run lint
```

### Quick Development Workflow
```bash
# Terminal 1: Start backend (from parent directory)
cd ../backend && python run.py

# Terminal 2: Start frontend (auto-reloads)
cd fronted && npm run dev

# Access application at http://localhost:3000
# API available at http://localhost:3000/api/* (proxied to backend:5000)
# Health check: http://localhost:3000/api/health
```

## Project Structure

### Source Organization
- `src/` - All React components and utilities
- `dist/` - Production build output
- `public/` (via index.html) - Static assets and HTML template

### API Integration
- All API calls go through Vite proxy to backend Flask server
- Base URL for API calls: `/api/*` (proxied to backend:5000)
- Error handling utilities in `src/utils/errorHandler.ts`

### Component Architecture
- Single-page application with React Router
- Centralized state management in main components
- Tailwind CSS for styling with theme system
- Lucide React for consistent iconography

## Backend Integration Notes

This frontend works with a Flask backend that provides:
- RESTful API endpoints for roles, flows, sessions, messages, and LLM operations
- Real-time conversation execution with LLM integration
- Health monitoring and system status endpoints
- Comprehensive error handling and JSON responses

The backend runs on port 5000 and should be started before the frontend for full functionality.

## Environment Setup

The frontend requires minimal configuration:
- Node.js and npm for package management
- Vite handles build tooling and dev server
- Backend API keys configured in backend environment variables
- No frontend-specific environment variables required

## Development Guidelines

1. **Directory Name**: The frontend directory is intentionally named "fronted" (not "frontend") - preserve this naming.

2. **API Proxy**: All `/api/*` requests are automatically proxied to the backend server during development.

3. **TypeScript**: Strict mode is enabled with unused variable checking for code quality.

4. **Styling**: Use Tailwind CSS utility classes with the existing theme system for consistency.

5. **Icons**: Use Lucide React icons for consistent UI elements.

6. **Component Structure**: Follow the existing component patterns and file organization.

7. **Error Handling**: Utilize the error handling utilities for consistent API error management.