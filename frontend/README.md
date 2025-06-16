# Code Analysis Tool Frontend

This is the frontend application for the Code Analysis Tool, built with Vue 3 and Element Plus.

## Project Structure

```
frontend/
├── public/                  # Static assets
├── src/
│   ├── api/                 # API services
│   │   ├── http.js          # Base HTTP client with interceptors
│   │   ├── projects.js      # Project-related API calls
│   │   └── analysis.js      # Analysis-related API calls
│   ├── assets/              # Assets (images, global CSS)
│   │   └── css/
│   │       └── main.css     # Global CSS variables and utility classes
│   ├── components/          # Reusable UI components
│   │   ├── ProjectCard.vue  # Project card component
│   │   ├── CodeEditor.vue   # Monaco editor wrapper
│   │   ├── DiffViewer.vue   # Code diff viewer
│   │   ├── TestCaseViewer.vue # Test case viewer component
│   │   ├── TestCaseItem.vue # Individual test case component
│   │   └── TestCaseFilters.vue # Test case filters component
│   ├── layouts/             # Layout components
│   │   └── MainLayout.vue   # Main application layout
│   ├── mixins/              # Vue mixins (if needed)
│   ├── router/              # Vue Router configuration
│   │   └── index.js         # Routes definition
│   ├── store/               # Vuex store
│   │   ├── index.js         # Store configuration and global state
│   │   └── modules/         # Vuex modules
│   │       ├── projects.js  # Projects module
│   │       └── analysis.js  # Analysis module
│   ├── utils/               # Utility functions
│   │   ├── formatters.js    # Data formatting utilities
│   │   └── websocket.js     # WebSocket service
│   ├── views/               # Application views/pages
│   │   ├── ProjectList.vue  # List of projects
│   │   ├── NewProject.vue   # Create new project form
│   │   ├── ProjectDetail.vue # Project details page
│   │   └── ProjectAnalysis.vue # Project analysis page
│   ├── App.vue              # Root component
│   └── main.js              # Entry point
├── .env                     # Environment variables
├── .env.development         # Development environment variables
├── .env.production          # Production environment variables
├── package.json             # Dependencies and scripts
└── vite.config.js           # Vite configuration
```

## Key Features

1. **Modular Store Structure**: Organized Vuex store with modules for better state management.
2. **API Service Layer**: Centralized API calls with proper error handling.
3. **Component Reusability**: Well-designed reusable components.
4. **Responsive Design**: Mobile-friendly layouts using Element Plus.
5. **Dark Mode Support**: Toggle between light and dark themes.
6. **Real-time Updates**: WebSocket integration for live notifications.
7. **Code Visualization**: Advanced code diff viewing and editing.
8. **Test Case Management**: Comprehensive test case viewing and filtering.

## Component Highlights

### MainLayout.vue
The main application layout includes a header, sidebar navigation, and a notification system.

### ProjectCard.vue
Reusable card component for displaying project information, with consistent styling.

### DiffViewer.vue
Component for displaying code differences with Monaco Editor integration.

### TestCaseViewer.vue
Component for displaying and managing test cases with filtering and sorting capabilities.

### CodeEditor.vue
Monaco Editor wrapper with additional features like fullscreen mode, theme switching, and language selection.

## Setup and Development

### Prerequisites
- Node.js 14.x or later
- npm 7.x or later

### Installation
```bash
# Install dependencies
npm install
```

### Development
```bash
# Start development server
npm run dev
```

### Building for Production
```bash
# Build for production
npm run build
```

## Environment Configuration

Create an `.env.local` file with the following variables:

```
VITE_APP_API_BASE_URL=http://localhost:8000/api
VITE_APP_WS_URL=ws://localhost:8000
```

## Customization

### Theme Customization
The application uses CSS variables for theming, which can be modified in `src/assets/css/main.css`.

