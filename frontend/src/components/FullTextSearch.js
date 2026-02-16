import React, { useState, useEffect, useRef } from 'react';
import {
  Box, TextField, Button, Typography, Paper, Grid, Chip,
  CircularProgress, Alert, InputAdornment, Card, CardContent,
  Divider, Autocomplete
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';

export default function FullTextSearch({ backendUrl }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const debounceRef = useRef(null);

  // Load categories on mount
  useEffect(() => {
    axios.get(`${backendUrl}/search/categories`)
      .then(r => setCategories(r.data.data || []))
      .catch(() => {});
  }, [backendUrl]);

  // Autocomplete debounce
  const handleQueryChange = (val) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.length < 2) { setSuggestions([]); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const { data } = await axios.post(`${backendUrl}/search/autocomplete`, { prefix: val });
        setSuggestions(data.data || []);
      } catch { setSuggestions([]); }
    }, 300);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/search/fulltext`, {
        query,
        fields: ['title', 'description', 'category'],
        size: 12,
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    await axios.delete(`${backendUrl}/search/clear`).catch(() => {});
    setResults(null);
    setQuery('');
    alert('Index cleared. Re-run seed script to repopulate.');
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom fontWeight={700}>
        <ShoppingCartIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#1565c0' }} />
        Full-Text Search – Product Catalog
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Multi-match query with fuzzy matching, result highlighting, and autocomplete.
        Backed by 150+ seeded e-commerce products across 8 categories.
      </Typography>

      {/* ─── Categories ──────────────────────────────────────────────── */}
      <Box mb={2} display="flex" flexWrap="wrap" gap={1}>
        {categories.map(c => (
          <Chip
            key={c.category}
            label={`${c.category} (${c.count})`}
            size="small"
            variant="outlined"
            color="primary"
            onClick={() => { setQuery(c.category); }}
          />
        ))}
      </Box>

      {/* ─── Search Bar ──────────────────────────────────────────────── */}
      <Box display="flex" gap={1} mb={3}>
        <Autocomplete
          freeSolo
          options={suggestions}
          inputValue={query}
          onInputChange={(_, v) => handleQueryChange(v)}
          onChange={(_, v) => v && setQuery(v)}
          sx={{ flex: 1 }}
          renderInput={(params) => (
            <TextField
              {...params}
              placeholder="Search products… (e.g. 'wireless headphones', 'coffee maker')"
              variant="outlined"
              size="small"
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              InputProps={{
                ...params.InputProps,
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
          )}
        />
        <Button variant="contained" onClick={handleSearch} disabled={loading}>
          {loading ? <CircularProgress size={20} /> : 'Search'}
        </Button>
        <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={handleClear}>
          Clear Index
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ─── Results ─────────────────────────────────────────────────── */}
      {results && (
        <>
          <Typography variant="subtitle2" color="text.secondary" mb={1}>
            {results.total} results found
          </Typography>
          <Grid container spacing={2}>
            {results.data.map((item, i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <Card variant="outlined" sx={{ height: '100%', '&:hover': { boxShadow: 3 } }}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                      <Typography variant="subtitle1" fontWeight={600}
                        dangerouslySetInnerHTML={{
                          __html: item.highlights?.title?.[0] || item.source.title
                        }}
                      />
                      <Chip label={`$${item.source.price}`} size="small" color="success" />
                    </Box>
                    <Chip label={item.source.category} size="small" sx={{ mt: 0.5 }} />
                    <Divider sx={{ my: 1 }} />
                    <Typography variant="body2" color="text.secondary"
                      dangerouslySetInnerHTML={{
                        __html: item.highlights?.description?.[0] || item.source.description?.slice(0, 120) + '…'
                      }}
                    />
                    <Typography variant="caption" color="text.disabled" mt={1} display="block">
                      Score: {item.score?.toFixed(3)} · Brand: {item.source.brand}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {!results && !loading && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', bgcolor: '#fafafa' }}>
          <Typography color="text.secondary">
            Enter a search query above to explore the product catalog.
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Try: "laptop", "organic coffee", "running shoes", "bluetooth speaker"
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
