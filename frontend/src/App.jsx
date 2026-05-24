import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './components/Toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import SourceList from './pages/sources/SourceList';
import SourceDetail from './pages/sources/SourceDetail';
import MemoryList from './pages/memories/MemoryList';
import MemoryDetail from './pages/memories/MemoryDetail';
import MemoryCreate from './pages/memories/MemoryCreate';
import MemoryEdit from './pages/memories/MemoryEdit';
import Recall from './pages/recall/Recall';
import WikiExport from './pages/wiki/WikiExport';
import Timeline from './pages/governance/Timeline';
import Audit from './pages/governance/Audit';
import Policies from './pages/governance/Policies';
import Conflicts from './pages/governance/Conflicts';
import ForgetRequests from './pages/governance/ForgetRequests';

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="sources" element={<SourceList />} />
            <Route path="sources/:docId" element={<SourceDetail />} />
            <Route path="memories" element={<MemoryList />} />
            <Route path="memories/new" element={<MemoryCreate />} />
            <Route path="memories/:memoryId" element={<MemoryDetail />} />
            <Route path="memories/:memoryId/edit" element={<MemoryEdit />} />
            <Route path="recall" element={<Recall />} />
            <Route path="wiki" element={<WikiExport />} />
            <Route path="governance/timeline" element={<Timeline />} />
            <Route path="governance/audit" element={<Audit />} />
            <Route path="governance/policies" element={<Policies />} />
            <Route path="governance/conflicts" element={<Conflicts />} />
            <Route path="governance/forget-requests" element={<ForgetRequests />} />
          </Route>
        </Routes>
      </ToastProvider>
    </BrowserRouter>
  );
}
