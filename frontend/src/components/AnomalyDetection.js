import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Grid, Button, CircularProgress, Alert,
  Table, TableHead, TableRow, TableCell, TableBody, Chip, Slider,
  Select, MenuItem, FormControl, InputLabel, Card, CardContent
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import axios from 'axios';

const RANGES = [
  { label: '24h', gte: 'now-24h' },
  { label: '7d', gte: 'now-7d' },
  { label: '30d', gte: 'now-30d' },
];

export default function AnomalyDetection({ backendUrl }) {
  const [startTime, setStartTime] = useState('now-7d');
  const [userId, setUserId] = useState('');
  const [users, setUsers] = useState([]);
  const [threshold, setThreshold] = useState(2.5);
  const [result, setResult] = useState(null);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`${backendUrl}/ml/users`)
      .then(r => setUsers(r.data.data || []))
      .catch(() => {});
    axios.get(`${backendUrl}/ml/transaction-summary`)
      .then(r => setSummary(r.data.data || []))
      .catch(() => {});
  }, [backendUrl]);

  const handleDetect = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/ml/detect`, {
        start_time: startTime,
        end_time: 'now',
        z_score_threshold: threshold,
        user_id: userId || undefined,
      });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed');
    } finally {
      setLoading(false);
    }
  };

  const chartData = summary.map(d => ({
    date: d.date.slice(0, 10),
    total: d.total,
    avg: d.avg,
    count: d.count,
  }));

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <WarningIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#f44336' }} />
        Anomaly Detection – Transaction Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Statistical outlier detection using Z-scores computed over Elasticsearch
        <code> extended_stats </code> aggregations. Transactions with |z| &gt; threshold
        are flagged as anomalous.
      </Typography>

      {/* ─── Daily Summary Chart ─────────────────────────────────────── */}
      {summary.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={1}>
            Daily Transaction Volume (Last 30 days)
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="total" name="Total ($)" fill="#90caf9" />
              <Line yAxisId="right" type="monotone" dataKey="avg"
                name="Avg Tx ($)" stroke="#f44336" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </Paper>
      )}

      {/* ─── Controls ────────────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Time Range</InputLabel>
              <Select value={startTime} label="Time Range"
                onChange={e => setStartTime(e.target.value)}>
                {RANGES.map(r => (
                  <MenuItem key={r.gte} value={r.gte}>{r.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>User ID</InputLabel>
              <Select value={userId} label="User ID"
                onChange={e => setUserId(e.target.value)}>
                <MenuItem value="">All users</MenuItem>
                {users.slice(0, 20).map(u => (
                  <MenuItem key={u} value={u}>{u}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Typography variant="caption" color="text.secondary">
              Z-Score Threshold: <strong>{threshold}</strong>
              <em style={{ color: '#666', marginLeft: 8 }}>
                (lower = more sensitive)
              </em>
            </Typography>
            <Slider
              value={threshold} min={1} max={4} step={0.1}
              onChange={(_, v) => setThreshold(v)}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button fullWidth variant="contained" color="error"
              onClick={handleDetect} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : 'Detect Anomalies'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ─── Results ─────────────────────────────────────────────────── */}
      {result && (
        <>
          {/* Stats Cards */}
          <Grid container spacing={2} mb={3}>
            {[
              { label: 'Total Transactions', value: result.global_stats.count, color: '#1565c0' },
              { label: 'Mean Amount', value: `$${result.global_stats.mean}`, color: '#2e7d32' },
              { label: 'Std Deviation', value: `$${result.global_stats.std_dev}`, color: '#e65100' },
              { label: 'Anomalies Found', value: result.anomaly_count, color: '#c62828' },
            ].map(c => (
              <Grid item xs={6} sm={3} key={c.label}>
                <Card variant="outlined" sx={{ textAlign: 'center' }}>
                  <CardContent sx={{ py: 1.5 }}>
                    <Typography variant="caption" color="text.secondary">{c.label}</Typography>
                    <Typography variant="h6" fontWeight={700} color={c.color}>{c.value}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Anomalous Transactions */}
          <Paper variant="outlined">
            <Box p={1.5} bgcolor="#ffebee" display="flex" alignItems="center" gap={1}>
              <WarningIcon color="error" fontSize="small" />
              <Typography variant="subtitle1" fontWeight={600} color="error">
                Anomalous Transactions ({result.anomaly_count})
              </Typography>
              <Typography variant="caption" color="text.secondary">
                |z| &gt; {result.threshold}
              </Typography>
            </Box>
            {result.anomalies.length === 0 ? (
              <Box p={3} textAlign="center">
                <Typography color="text.secondary">No anomalies found. Try lowering the threshold.</Typography>
              </Box>
            ) : (
              <Table size="small">
                <TableHead sx={{ bgcolor: '#ffcdd2' }}>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>User ID</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Z-Score</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.anomalies.slice(0, 20).map((tx, i) => (
                    <TableRow key={i} hover sx={{ bgcolor: '#fff8f8' }}>
                      <TableCell sx={{ fontSize: '0.75rem' }}>
                        {new Date(tx.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{tx.user_id}</TableCell>
                      <TableCell>
                        <strong style={{ color: '#c62828' }}>${tx.amount?.toFixed(2)}</strong>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={tx.z_score}
                          size="small"
                          color={Math.abs(tx.z_score) > 3 ? 'error' : 'warning'}
                        />
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{tx.category}</TableCell>
                      <TableCell>
                        <Chip label="ANOMALY" size="small" color="error" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </>
      )}

      {!result && !loading && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', bgcolor: '#fafafa' }}>
          <Typography color="text.secondary">
            Configure parameters and click "Detect Anomalies" to run analysis.
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Detection uses Z-scores from ES extended_stats aggregation.
            Z &gt; threshold = anomaly.
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
