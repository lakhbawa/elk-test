import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Grid, Select, MenuItem, FormControl,
  InputLabel, Button, CircularProgress, Alert, Card, CardContent,
  ToggleButton, ToggleButtonGroup
} from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import axios from 'axios';

const METRICS = ['cpu', 'memory', 'disk', 'network'];
const METRIC_COLORS = { cpu: '#f44336', memory: '#2196f3', disk: '#4caf50', network: '#ff9800' };
const INTERVALS = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
];

const RANGES = [
  { label: '1h', gte: 'now-1h' },
  { label: '6h', gte: 'now-6h' },
  { label: '24h', gte: 'now-24h' },
  { label: '7d', gte: 'now-7d' },
];

export default function RealTimeAnalytics({ backendUrl }) {
  const [metric, setMetric] = useState('cpu');
  const [host, setHost] = useState('');
  const [hosts, setHosts] = useState([]);
  const [interval, setIntervalVal] = useState('5m');
  const [range, setRange] = useState('now-6h');
  const [chartData, setChartData] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`${backendUrl}/analytics/hosts`)
      .then(r => setHosts(r.data.data || []))
      .catch(() => {});
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      const { data } = await axios.get(`${backendUrl}/analytics/summary`);
      setSummary(data.data || []);
    } catch {}
  };

  const fetchTimeseries = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/analytics/timeseries`, {
        metric,
        host: host || undefined,
        start_time: range,
        end_time: 'now',
        interval,
      });
      const formatted = (data.data || []).map(d => ({
        ...d,
        time: new Date(d.timestamp).toLocaleTimeString(),
      }));
      setChartData(formatted);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load timeseries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTimeseries(); }, [metric, host, interval, range]);

  const avgValue = chartData.length
    ? (chartData.reduce((s, d) => s + d.avg, 0) / chartData.length).toFixed(1)
    : '–';
  const maxValue = chartData.length
    ? Math.max(...chartData.map(d => d.max)).toFixed(1)
    : '–';

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        📈 Real-Time Analytics & Observability
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Date histogram aggregations over simulated system metrics (CPU, memory, disk, network)
        from multiple hosts. Rolling averages computed server-side in Elasticsearch.
      </Typography>

      {/* ─── Summary Cards ───────────────────────────────────────────── */}
      <Grid container spacing={2} mb={3}>
        {summary.map(s => (
          <Grid item xs={6} sm={3} key={s.metric}>
            <Card variant="outlined" sx={{ textAlign: 'center', bgcolor: '#f9fbe7' }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="caption" color="text.secondary" textTransform="uppercase">
                  {s.metric} (24h avg)
                </Typography>
                <Typography variant="h6" fontWeight={700}
                  color={METRIC_COLORS[s.metric] || 'text.primary'}>
                  {s.avg_24h}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  peak {s.max_24h}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* ─── Controls ────────────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Metric</InputLabel>
              <Select value={metric} label="Metric" onChange={e => setMetric(e.target.value)}>
                {METRICS.map(m => <MenuItem key={m} value={m}>{m.toUpperCase()}</MenuItem>)}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Host</InputLabel>
              <Select value={host} label="Host" onChange={e => setHost(e.target.value)}>
                <MenuItem value="">All hosts</MenuItem>
                {hosts.map(h => <MenuItem key={h} value={h}>{h}</MenuItem>)}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Typography variant="caption" color="text.secondary">Time Range</Typography>
            <ToggleButtonGroup
              value={range} exclusive size="small" fullWidth
              onChange={(_, v) => v && setRange(v)}
            >
              {RANGES.map(r => (
                <ToggleButton key={r.gte} value={r.gte}>{r.label}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Typography variant="caption" color="text.secondary">Interval</Typography>
            <ToggleButtonGroup
              value={interval} exclusive size="small" fullWidth
              onChange={(_, v) => v && setIntervalVal(v)}
            >
              {INTERVALS.map(i => (
                <ToggleButton key={i.value} value={i.value}>{i.label}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ─── Chart ───────────────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="subtitle1" fontWeight={600}>
            {metric.toUpperCase()} over time
          </Typography>
          <Box display="flex" gap={2}>
            <Typography variant="body2">
              Avg: <strong>{avgValue}%</strong>
            </Typography>
            <Typography variant="body2">
              Peak: <strong style={{ color: '#f44336' }}>{maxValue}%</strong>
            </Typography>
          </Box>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" py={5}>
            <CircularProgress />
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v) => `${v}%`}
                labelStyle={{ fontWeight: 600 }}
              />
              <Legend />
              <ReferenceLine y={80} stroke="#f44336" strokeDasharray="4 4" label="80%" />
              <Line
                type="monotone" dataKey="avg" name="Average"
                stroke={METRIC_COLORS[metric]} strokeWidth={2} dot={false}
              />
              <Line
                type="monotone" dataKey="max" name="Max"
                stroke="#ff7043" strokeWidth={1} strokeDasharray="5 5" dot={false}
              />
              <Line
                type="monotone" dataKey="min" name="Min"
                stroke="#66bb6a" strokeWidth={1} strokeDasharray="5 5" dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Paper>
    </Box>
  );
}
