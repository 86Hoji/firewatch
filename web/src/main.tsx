import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './styles.css';
import { MapStage } from './map/MapStage';
import { Explore } from './pages/Explore';
import { Landing } from './pages/Landing';
import { Validation } from './pages/Validation';

function App() {
  return (
    <BrowserRouter>
      {/* One persistent map behind every page. */}
      <MapStage />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/validation" element={<Validation />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
