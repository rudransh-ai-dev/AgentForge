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
        <Dashboard />
      ) : (
        <LandingPage onEnter={() => setHasEntered(true)} />
      )}
    </ErrorBoundary>
  )
}

export default App
