import React from 'react'
import { createRoot } from 'react-dom/client'
import { ReactFlowProvider } from '@xyflow/react'
import App from './App'

const root = createRoot(document.getElementById('root')!)
root.render(
  <ReactFlowProvider>
    <App />
  </ReactFlowProvider>
)