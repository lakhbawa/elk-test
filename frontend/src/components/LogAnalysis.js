import React, { useState, useEffect } from 'react';
import {
  Box, TextField, Button, Typography, Paper, Grid, Chip,
  CircularProgress, Alert, Table, TableHead, TableRow, TableCell,
  TableBody, Select, MenuItem, FormControl, InputLabel, Accordion,
  AccordionSummary, AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const LEVEL_COLORS = {
  ERROR: '#f44336', WARN: '#ff9800', WARNING: '#ff9800',
  INFO: '#2196f3', DEBUG: '#9c27b0',
};

const now = new Date();
const minus7d = new Date(now - 7 * 86400000);
const fmt = d => d.toISOString().slice(0, 16);

export default function LogAnalysis({ backendUrl }) {
  const [keyword, setKeyword] = useState('');
  const [level, setLevel] = useState('');
  const [startTime, setStartTime] = useState(fmt(minus7d));
  const [endTime, setEndTime] = useState(fmt(now));
  const [logs, setLogs] = useState(null);
  const [levelData, setLevelData] = useState([]);
  const [topErrors, setTopErrors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAggregations();
  }, []);

  const fetchAggregations = async () => {
    try {
      const [lvl, errs] = await Promise.all([
        axios.get(`${backendUrl}/logs/level-aggregation`),
        axios.get(`${backendUrl}/logs/top-errors`),
      ]);
      setLevelData(lvl.data.data || []);
      setTopErrors(errs.data.data || []);
    } catch {}
  };

  const handleSearch = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/logs/search`, {
        keyword: keyword || undefined,
        level: level || undefined,
        start_time: startTime,
        end_time: endTime,
        size: 50,
      });
      setLogs(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        📊 Log & Event Data Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Search simulated Nginx/application logs ingested via Logstash. Aggregate by
        level, filter by date range, and surface top error hosts.
      </Typography>

      {/* ─── Filters ─────────────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <TextField fullWidth size="small" label="Keyword" value={keyword}
              onChange={e => setKeyword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Level</InputLabel>
              <Select value={level} label="Level" onChange={e => setLevel(e.target.value)}>
                <MenuItem value="">All</MenuItem>
                {['ERROR', 'WARN', 'INFO', 'DEBUG'].map(l => (
                  <MenuItem key={l} value={l}>{l}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} sm={2}>
            <TextField fullWidth size="small" label="From" type="datetime-local"
              value={startTime} onChange={e => setStartTime(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={6} sm={2}>
            <TextField fullWidth size="small" label="To" type="datetime-local"
              value={endTime} onChange={e => setEndTime(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button fullWidth variant="contained" onClick={handleSearch} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : 'Search Logs'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ─── Charts ──────────────────────────────────────────────────── */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={5}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={1}>
              Log Level Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={levelData} dataKey="count" nameKey="level"
                  cx="50%" cy="50%" outerRadius={80} label={e => e.level}>
                  {levelData.map((entry, i) => (
                    <Cell key={i} fill={LEVEL_COLORS[entry.level] || '#607d8b'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={7}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={1}>
              Top Error Hosts
            </Typography>
            {topErrors.length === 0 ? (
              <Typography color="text.secondary">No errors found</Typography>
            ) : (
              topErrors.slice(0, 5).map((h, i) => (
                <Accordion key={i} disableGutters>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" justifyContent="space-between" width="100%" pr={1}>
                      <Typography fontWeight={600}>{h.host}</Typography>
                      <Chip label={`${h.error_count} errors`} size="small" color="error" />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails sx={{ bgcolor: '#fafafa' }}>
                    {h.top_messages.map((m, j) => (
                      <Box key={j} display="flex" justifyContent="space-between" mb={0.5}>
                        <Typography variant="body2" color="text.secondary">{m.message}</Typography>
                        <Chip label={m.count} size="small" />
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              ))
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* ─── Log Table ───────────────────────────────────────────────── */}
      {logs && (
        <Paper variant="outlined">
          <Box p={1.5} display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1" fontWeight={600}>
              Results ({logs.total} total, showing {logs.data.length})
            </Typography>
          </Box>
          <Table size="small">
            <TableHead sx={{ bgcolor: '#e3f2fd' }}>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Level</TableCell>
                <TableCell>Host</TableCell>
                <TableCell>Message</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.data.map((log, i) => (
                <TableRow key={i} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.75rem' }}>
                    {new Date(log['@timestamp']).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={log.level}
                      size="small"
                      sx={{
                        bgcolor: LEVEL_COLORS[log.level] || '#607d8b',
                        color: 'white',
                        fontSize: '0.7rem',
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.8rem' }}>{log.host}</TableCell>
                  <TableCell sx={{ fontSize: '0.8rem' }}>{log.message}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {!logs && !loading && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', bgcolor: '#fafafa' }}>
          <Typography color="text.secondary">
            Click "Search Logs" to query the log index. Try filtering by level "ERROR".
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
