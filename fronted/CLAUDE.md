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
- `MultiRoleDialogSystem.tsx` (63KB) - Main application with full UI for role management and flow execution
- `LLMTestPage.tsx` (10KB) - LLM testing interface for API validation
- `theme.tsx` - Theme system with 5 color schemes (blue, purple, emerald, rose, amber)
- `App.tsx` - Root component wrapper with routing
- `main.tsx` - React application entry point

### Advanced Components (Currently Have Build Issues)
- `components/EnhancedSessionTheater.tsx` - Enhanced session interface with debugging
- `components/StepProgressDisplay.tsx` - Real-time progress visualization
- `components/LLMIODisplay.tsx` - LLM input/output debugging display
- `components/StepVisualization.tsx` - Multi-view flow visualization
- `components/DebugPanel.tsx` - Comprehensive debugging and monitoring

### Custom Hooks
- `hooks/useStepProgress.ts` - Step progress state management
- `hooks/useLLMInteractions.ts` - LLM interaction tracking
- `hooks/useWebSocket.ts` - WebSocket connection management
- `hooks/usePermissions.ts` - Permission-based access control
- `hooks/usePerformanceOptimizations.ts` - Performance optimization utilities
- `hooks/useUserPreferences.ts` - User preferences persistence

### Core Features
- Role management interface
- Flow template editor with JSON configuration
- Real-time conversation execution
- Message history and export functionality
- LLM integration testing
- Theme system with multiple color schemes

### Development Configuration
- `vite.config.ts` - Vite configuration with API proxy to backend:5000
- `tsconfig.json` - TypeScript strict mode configuration with unused variable checking
- `tailwind.config.js` - Tailwind CSS configuration for utility-first styling
- ESLint is configured but requires proper initialization (`npm init @eslint/config`)
- API client configuration supports multiple base URLs via environment variables

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
- `src/api/` - Centralized API clients (roleApi.ts, flowApi.ts, sessionApi.ts)
- `src/components/` - Reusable UI components (advanced debugging components)
- `src/hooks/` - Custom React hooks for state management
- `src/utils/` - Utility functions (errorHandler.ts)
- `src/types/` - TypeScript type definitions
- `dist/` - Production build output
- `public/` (via index.html) - Static assets and HTML template

### API Integration
- All API calls go through Vite proxy to backend Flask server
- Base URL for API calls: `/api/*` (proxied to backend:5000)
- Error handling utilities in `src/utils/errorHandler.ts`
- API client supports environment variable configuration (VITE_API_BASE_URL_ALT)
- Centralized HTTP client with error handling and type safety

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

## Development Commands

### Build Status and Issues
```bash
# Note: The project currently has TypeScript compilation errors
npm run build  # Will fail due to syntax errors in components/

# Linting requires ESLint configuration
npm run lint   # Will prompt to run `npm init @eslint/config`

# Development server (runs despite build issues)
npm run dev    # Works fine for development
```

### Testing Commands
```bash
# Run integration tests (if available)
npm test

# Run test coverage (if configured)
npm run test:coverage
```

## Development Guidelines

1. **Directory Name**: The frontend directory is intentionally named "fronted" (not "frontend") - preserve this naming.

2. **API Proxy**: All `/api/*` requests are automatically proxied to the backend server during development via Vite proxy (port 3000 → backend:5000).

3. **TypeScript**: Strict mode is enabled with unused variable checking. Note: There are currently syntax errors in `components/` directory that prevent successful builds.

4. **Styling**: Use Tailwind CSS utility classes with the existing theme system for consistency.

5. **Icons**: Use Lucide React icons for consistent UI elements.

6. **Component Structure**: Follow the existing component patterns and file organization in `src/`.

7. **Error Handling**: Utilize the error handling utilities in `src/utils/errorHandler.ts` for consistent API error management.

8. **API Integration**: Use the centralized API client pattern from `src/api/` with proper TypeScript interfaces.

## Known Issues

- **Build Failures**: TypeScript compilation fails due to syntax errors in components (unterminated regex literals, missing brackets)
- **ESLint Configuration**: Lint command requires ESLint config initialization
- **Development Environment**: Despite build issues, the development server works correctly