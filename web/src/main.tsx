import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './styles.css';
import { MapStage } from './map/MapStage';
import { Explore } from './pages/Explore';

function App() {
  return (
    <BrowserRouter>
      {/* One persistent map behind every page. */}
      <MapStage />
      <Routes>
        <Route path="/explore" element={<Explore />} />
        {/* F1: the map is the whole site for now; the landing replaces this in F3. */}
        <Route path="*" element={<Navigate to={`/explore${location.search}`} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
