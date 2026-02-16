import React, { useState, useEffect } from 'react';
import {
  Box, TextField, Button, Typography, Paper, Grid, Chip,
  CircularProgress, Alert, Card, CardContent, Select,
  MenuItem, FormControl, InputLabel, Slider
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import axios from 'axios';

// Fix Leaflet default marker icons
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const PRESETS = [
  { name: 'New York', lat: 40.7128, lon: -74.006 },
  { name: 'London', lat: 51.5074, lon: -0.1278 },
  { name: 'Tokyo', lat: 35.6762, lon: 139.6503 },
  { name: 'Sydney', lat: -33.8688, lon: 151.2093 },
  { name: 'Paris', lat: 48.8566, lon: 2.3522 },
];

export default function GeospatialSearch({ backendUrl }) {
  const [lat, setLat] = useState(40.7128);
  const [lon, setLon] = useState(-74.006);
  const [distance, setDistance] = useState(50);
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`${backendUrl}/geo/categories`)
      .then(r => setCategories(r.data.data || []))
      .catch(() => {});
  }, [backendUrl]);

  const handlePreset = (preset) => {
    setLat(preset.lat);
    setLon(preset.lon);
  };

  const handleSearch = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(`${backendUrl}/geo/nearby`, {
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        distance: `${distance}km`,
        size: 20,
        category: category || undefined,
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const mapCenter = [lat || 40.7128, lon || -74.006];

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <LocationOnIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#1565c0' }} />
        Geospatial Search
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Geo-distance queries using Elasticsearch geo_point fields. Find stores, restaurants,
        hotels, and parks near a coordinate within a configurable radius.
      </Typography>

      {/* ─── Presets ─────────────────────────────────────────────────── */}
      <Box mb={2} display="flex" gap={1} flexWrap="wrap">
        {PRESETS.map(p => (
          <Chip key={p.name} label={p.name} onClick={() => handlePreset(p)}
            variant="outlined" color="primary" size="small" />
        ))}
      </Box>

      {/* ─── Controls ────────────────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={6} sm={2}>
            <TextField fullWidth size="small" label="Latitude"
              value={lat} onChange={e => setLat(e.target.value)} type="number"
              inputProps={{ step: 0.0001 }}
            />
          </Grid>
          <Grid item xs={6} sm={2}>
            <TextField fullWidth size="small" label="Longitude"
              value={lon} onChange={e => setLon(e.target.value)} type="number"
              inputProps={{ step: 0.0001 }}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <Typography variant="caption" color="text.secondary">
              Radius: <strong>{distance} km</strong>
            </Typography>
            <Slider
              value={distance} min={1} max={500} step={1}
              onChange={(_, v) => setDistance(v)}
              valueLabelDisplay="auto" valueLabelFormat={v => `${v}km`}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Category</InputLabel>
              <Select value={category} label="Category" onChange={e => setCategory(e.target.value)}>
                <MenuItem value="">All</MenuItem>
                {categories.map(c => (
                  <MenuItem key={c.category} value={c.category}>{c.category}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button fullWidth variant="contained" onClick={handleSearch} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : 'Find Nearby'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* ─── Map ─────────────────────────────────────────────────── */}
        <Grid item xs={12} md={7}>
          <Paper variant="outlined" sx={{ height: 400, overflow: 'hidden' }}>
            <MapContainer center={mapCenter} zoom={10} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {/* Search radius circle */}
              <Circle
                center={mapCenter}
                radius={distance * 1000}
                pathOptions={{ color: '#1565c0', fillOpacity: 0.05 }}
              />
              {/* Origin marker */}
              <Marker position={mapCenter}>
                <Popup>Search origin</Popup>
              </Marker>
              {/* Result markers */}
              {results?.data.map((loc, i) => (
                <Marker key={i}
                  position={[loc.location?.lat || loc.lat, loc.location?.lon || loc.lon]}>
                  <Popup>
                    <strong>{loc.name}</strong><br />
                    {loc.category}<br />
                    {loc.address}<br />
                    <em>{loc.distance_km} km away</em>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </Paper>
        </Grid>

        {/* ─── Results List ────────────────────────────────────────── */}
        <Grid item xs={12} md={5}>
          <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto' }}>
            {results ? (
              <>
                <Box p={1.5} bgcolor="#e3f2fd">
                  <Typography variant="subtitle2">
                    {results.total} locations within {distance}km
                  </Typography>
                </Box>
                {results.data.map((loc, i) => (
                  <Card key={i} variant="outlined" sx={{ m: 1 }}>
                    <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                      <Box display="flex" justifyContent="space-between">
                        <Typography variant="subtitle2" fontWeight={600}>{loc.name}</Typography>
                        <Chip label={`${loc.distance_km} km`} size="small" color="primary" />
                      </Box>
                      <Chip label={loc.category} size="small" sx={{ mt: 0.5, mr: 0.5 }} />
                      <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                        {loc.address}, {loc.city}
                      </Typography>
                      {loc.rating && (
                        <Typography variant="caption" color="text.secondary">
                          ⭐ {loc.rating} · {loc.review_count} reviews
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : (
              <Box p={3} textAlign="center">
                <Typography color="text.secondary">
                  Select a location and click "Find Nearby" to search.
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
