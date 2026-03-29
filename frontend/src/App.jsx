import React from 'react'
import { ErrorBoundary } from 'react-error-boundary'
import Dashboard from './Dashboard'
import './index.css'

function App() {
  return (
    <ErrorBoundary fallbackRender={({ error }) => (
      <div style={{ padding: '20px', color: 'red', backgroundColor: '#fff', fontSize: '20px' }}>
        <h2>React App Crashed:</h2>
        <pre>{error.message}</pre>
      </div>
    )}>
      <Dashboard />
    </ErrorBoundary>
  )
}

export default App
