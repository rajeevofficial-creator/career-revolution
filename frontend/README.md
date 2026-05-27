# Career Revolution - Frontend

React-based frontend for the Career Revolution platform.

## Features
- User authentication (login/register)
- Document upload and management
- Profile editing and completion
- Dashboard with statistics
- Responsive design with Material-UI

## Setup

### 1. Install dependencies
```bash
npm install
```

### 2. Configure API URL
Edit `.env` file:
```
REACT_APP_API_URL=http://localhost:8000
```

### 3. Start development server
```bash
npm start
```

## Project Structure
```
frontend/
├── public/              # Static files
├── src/
│   ├── components/     # Reusable components
│   ├── pages/         # Page components
│   ├── services/      # API services
│   ├── utils/         # Utilities
│   ├── App.js         # Main app component
│   └── index.js       # Entry point
└── package.json       # Dependencies
```

## Available Scripts
- `npm start` - Run development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from CRA

## API Integration
The frontend connects to the FastAPI backend at `http://localhost:8000`. Make sure the backend is running before starting the frontend.