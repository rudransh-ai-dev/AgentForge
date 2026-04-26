import React from 'react'
import { ErrorBoundary } from 'react-error-boundary'
import Dashboard from './pages/Dashboard'
import './index.css'

import LandingPage from './pages/LandingPage'

function App() {
  const [hasEntered, setHasEntered] = React.useState(false);

  return (
    <ErrorBoundary fallbackRender={({ error }) => (
      <div style={{ padding: '20px', color: 'red', backgroundColor: '#fff', fontSize: '20px' }}>
        <h2>React App Crashed:</h2>
        <pre>{error.message}</pre>
      </div>
    )}>
      {hasEntered ? (
        <div className="flex flex-col h-screen">
          <div className="h-8 bg-canvasSubtle border-b border-borderDefault/50 flex items-center justify-between px-3 shrink-0">
            <div className="flex items-center gap-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-medium text-accent">
                Dashboard
              </span>
            </div>
            <span className="text-[9px] text-fgSubtle">v5.0</span>
          </div>
          <div className="flex-1 min-h-0">
            <Dashboard />
          </div>
        </div>
      ) : (
        <LandingPage onEnter={() => setHasEntered(true)} />
      )}
    </ErrorBoundary>
  )
}

export default App
