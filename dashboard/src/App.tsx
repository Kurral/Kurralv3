import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Traces } from './pages/Traces';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trace" element={<Traces />} />
          <Route path="/mcp-sessions" element={<MCPSessionsPlaceholder />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

// Placeholder for MCP Sessions page (to be built later)
function MCPSessionsPlaceholder() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">MCP Sessions</h1>
        <p className="text-gray-600">This page is under construction.</p>
      </div>
    </div>
  );
}

export default App;
