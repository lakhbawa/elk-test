import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Grid, Button, CircularProgress,
  Alert, Card, CardContent, Chip, Select, MenuItem,
  FormControl, InputLabel, Divider
} from '@mui/material';
import RecommendIcon from '@mui/icons-material/Recommend';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import axios from 'axios';

export default function Recommendations({ backendUrl }) {
  const [userId, setUserId] = useState('');
  const [users, setUsers] = useState([]);
  const [recs, setRecs] = useState(null);
  const [popular, setPopular] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`${backendUrl}/recs/users`)
      .then(r => setUsers(r.data.data || []))
      .catch(() => {});
    axios.get(`${backendUrl}/recs/popular`)
      .then(r => setPopular(r.data.data || []))
      .catch(() => {});
  }, [backendUrl]);

  const handleGetRecs = async () => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/recs/for-user`, {
        user_id: userId,
        size: 6,
      });
      setRecs(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  const ProductCard = ({ product, badge }) => (
    <Card variant="outlined" sx={{ height: '100%', '&:hover': { boxShadow: 3 } }}>
      <CardContent>
        {badge && (
          <Chip label={badge} size="small" color="primary"
            sx={{ mb: 1, fontSize: '0.7rem' }} />
        )}
        <Typography variant="subtitle2" fontWeight={600}>{product.title}</Typography>
        <Chip label={product.category} size="small" variant="outlined" sx={{ mt: 0.5 }} />
        <Divider sx={{ my: 1 }} />
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
          {product.description?.slice(0, 100)}…
        </Typography>
        <Box mt={1} display="flex" justifyContent="space-between" alignItems="center">
          <Chip label={`$${product.price}`} size="small" color="success" />
          {product.brand && (
            <Typography variant="caption" color="text.disabled">{product.brand}</Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <RecommendIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#1565c0' }} />
        Personalization & Recommendations
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Collaborative filtering using Elasticsearch aggregations: find products liked by
        users similar to the selected user. Falls back to globally popular items.
      </Typography>

      {/* ─── User Selector ───────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={5}>
            <FormControl fullWidth size="small">
              <InputLabel>Select User</InputLabel>
              <Select value={userId} label="Select User"
                onChange={e => setUserId(e.target.value)}>
                {users.slice(0, 30).map(u => (
                  <MenuItem key={u} value={u}>{u}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Button fullWidth variant="contained" onClick={handleGetRecs}
              disabled={loading || !userId} startIcon={<RecommendIcon />}>
              {loading ? <CircularProgress size={20} /> : 'Get Recommendations'}
            </Button>
          </Grid>
          {recs && (
            <Grid item xs={12} sm={4}>
              <Typography variant="body2">
                User has interacted with <strong>{recs.seen_count}</strong> products.
                Showing <strong>{recs.data?.length}</strong> recommendations.
              </Typography>
            </Grid>
          )}
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ─── Personalized Recommendations ────────────────────────────── */}
      {recs && recs.data?.length > 0 && (
        <Box mb={4}>
          <Typography variant="subtitle1" fontWeight={600} mb={1.5}
            sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <RecommendIcon color="primary" />
            Recommended for {recs.user_id}
          </Typography>
          <Grid container spacing={2}>
            {recs.data.map((p, i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <ProductCard product={p} badge={i === 0 ? 'Top Pick' : undefined} />
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {recs?.message && (
        <Alert severity="info" sx={{ mb: 3 }}>{recs.message}</Alert>
      )}

      {/* ─── Popular Products ────────────────────────────────────────── */}
      <Box>
        <Typography variant="subtitle1" fontWeight={600} mb={1.5}
          sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TrendingUpIcon color="warning" />
          Trending Products (Most Interactions)
        </Typography>
        <Grid container spacing={2}>
          {popular.map((p, i) => (
            <Grid item xs={12} sm={6} md={4} key={i}>
              <ProductCard product={p} badge={i < 3 ? `#${i + 1} Popular` : undefined} />
            </Grid>
          ))}
        </Grid>
      </Box>

      {!recs && !loading && popular.length === 0 && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', bgcolor: '#fafafa' }}>
          <Typography color="text.secondary">
            Select a user above to get personalized recommendations.
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
