import React, { useState, useEffect } from 'react';
import {
  AppBar, Toolbar, Typography, Container, Box, Tabs, Tab,
  Chip, Alert, CircularProgress, Button, Tooltip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TimelineIcon from '@mui/icons-material/Timeline';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PsychologyIcon from '@mui/icons-material/Psychology';
import RecommendIcon from '@mui/icons-material/Recommend';
import axios from 'axios';

import FullTextSearch from './components/FullTextSearch';
import LogAnalysis from './components/LogAnalysis';
import RealTimeAnalytics from './components/RealTimeAnalytics';
import GeospatialSearch from './components/GeospatialSearch';
import AnomalyDetection from './components/AnomalyDetection';
import Recommendations from './components/Recommendations';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

const TABS = [
  { label: 'Full-Text Search',  icon: <SearchIcon />,      component: FullTextSearch },
  { label: 'Log Analysis',      icon: <AssessmentIcon />,   component: LogAnalysis },
  { label: 'Real-Time Analytics', icon: <TimelineIcon />,  component: RealTimeAnalytics },
  { label: 'Geospatial',        icon: <LocationOnIcon />,   component: GeospatialSearch },
  { label: 'Anomaly Detection', icon: <PsychologyIcon />,   component: AnomalyDetection },
  { label: 'Recommendations',   icon: <RecommendIcon />,    component: Recommendations },
];

export default function App() {
  const [tab, setTab] = useState(0);
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const { data } = await axios.get(`${BACKEND}/health`);
        setHealth(data);
      } catch {
        setHealth({ status: 'error', elasticsearch: 'unreachable' });
      } finally {
        setHealthLoading(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const ActiveComponent = TABS[tab].component;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: '#f5f7fa' }}>
      {/* ─── AppBar ─────────────────────────────────────────────────────── */}
      <AppBar position="static" sx={{ bgcolor: '#1565c0' }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            🔍 Elasticsearch Demo Hub
          </Typography>

          {healthLoading ? (
            <CircularProgress size={20} sx={{ color: 'white' }} />
          ) : (
            <Tooltip title={`Cluster: ${health?.cluster_name || 'N/A'}`}>
              <Chip
                label={`ES: ${health?.elasticsearch || health?.status}`}
                size="small"
                sx={{
                  bgcolor: health?.status === 'ok' ? '#2e7d32' : '#c62828',
                  color: 'white',
                  fontWeight: 600,
                }}
              />
            </Tooltip>
          )}

          <Button
            size="small"
            sx={{ ml: 2, color: 'white', textTransform: 'none' }}
            href="http://localhost:5601"
            target="_blank"
            rel="noopener noreferrer"
          >
            Kibana ↗
          </Button>
        </Toolbar>

        {/* ─── Tab Bar ──────────────────────────────────────────────────── */}
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            bgcolor: '#0d47a1',
            '& .MuiTab-root': { color: 'rgba(255,255,255,0.7)', minHeight: 48 },
            '& .Mui-selected': { color: 'white !important' },
            '& .MuiTabs-indicator': { bgcolor: '#90caf9' },
          }}
        >
          {TABS.map((t, i) => (
            <Tab key={i} icon={t.icon} label={t.label} iconPosition="start" sx={{ gap: 1 }} />
          ))}
        </Tabs>
      </AppBar>

      {/* ─── Main Content ────────────────────────────────────────────────── */}
      <Container maxWidth="xl" sx={{ flex: 1, py: 3 }}>
        {health?.status === 'error' && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Cannot reach Elasticsearch. Make sure the stack is running (<code>docker-compose up</code>).
          </Alert>
        )}

        <ActiveComponent backendUrl={BACKEND} />
      </Container>

      {/* ─── Footer ─────────────────────────────────────────────────────── */}
      <Box component="footer" sx={{ py: 1.5, textAlign: 'center', bgcolor: '#e3f2fd' }}>
        <Typography variant="caption" color="text.secondary">
          Elasticsearch Demo Hub · Powered by Elasticsearch 8.12 + FastAPI + React
        </Typography>
      </Box>
    </Box>
  );
}
