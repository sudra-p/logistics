import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Grid,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
} from '@mui/material';
import { useStockItem, useCreateStockItem, useUpdateStockItem } from './hooks';
import { UNIT_OPTIONS } from './unitOptions';

export default function StockFormPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const stockItemId = id ? parseInt(id, 10) : null;

  // Form state
  const [productName, setProductName] = useState('');
  const [availableStock, setAvailableStock] = useState('0');
  const [reservedStock, setReservedStock] = useState('0');
  const [shippedStock, setShippedStock] = useState('0');
  const [unit, setUnit] = useState('units');
  const [formError, setFormError] = useState('');

  // Fetch existing stock item for edit mode
  const stockItemQuery = useStockItem(stockItemId);

  // Mutations
  const createMutation = useCreateStockItem();
  const updateMutation = useUpdateStockItem(stockItemId ?? 0);

  // Populate form when editing
  useEffect(() => {
    if (stockItemQuery.data) {
      setProductName(stockItemQuery.data.product_name);
      setAvailableStock(String(stockItemQuery.data.available_stock));
      setReservedStock(String(stockItemQuery.data.reserved_stock));
      setShippedStock(String(stockItemQuery.data.shipped_stock));
      setUnit(stockItemQuery.data.unit);
    }
  }, [stockItemQuery.data]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!productName.trim()) {
      setFormError('Product name is required.');
      return;
    }
    if (Number(availableStock) < 0 || Number(reservedStock) < 0 || Number(shippedStock) < 0) {
      setFormError('Stock values must be non-negative.');
      return;
    }

    const payload = {
      product_name: productName.trim(),
      available_stock: parseInt(availableStock, 10),
      reserved_stock: parseInt(reservedStock, 10),
      shipped_stock: parseInt(shippedStock, 10),
      unit: unit.trim() || 'units',
    };

    const mutation = isEdit ? updateMutation : createMutation;

    mutation.mutate(payload, {
      onSuccess: () => {
        navigate('/inventory');
      },
      onError: (error: unknown) => {
        const axiosErr = error as { response?: { data?: Record<string, string[]> } };
        if (axiosErr.response?.data) {
          const messages = Object.entries(axiosErr.response.data)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('; ');
          setFormError(messages || 'An error occurred.');
        } else {
          setFormError('An unexpected error occurred. Please try again.');
        }
      },
    });
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  // Detect legacy unit values not in the standard options list
  const isLegacyUnit = unit && !UNIT_OPTIONS.some((opt) => opt.value === unit);

  // Loading state for edit mode
  if (isEdit && stockItemQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isEdit && stockItemQuery.isError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load stock item. Please go back and try again.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {isEdit ? 'Edit Stock Item' : 'New Stock Item'}
      </Typography>

      {formError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {formError}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSubmit} noValidate>
          <Grid container spacing={2}>
            {/* Product Name */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Product Name"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                fullWidth
                required
                placeholder="e.g., Rice Bags 50kg"
              />
            </Grid>

            {/* Unit */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="unit-select-label">Unit</InputLabel>
                <Select
                  labelId="unit-select-label"
                  id="unit-select"
                  value={unit}
                  label="Unit"
                  onChange={(e) => setUnit(e.target.value)}
                >
                  {UNIT_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                  {isLegacyUnit && (
                    <MenuItem key={unit} value={unit}>
                      {unit} (legacy)
                    </MenuItem>
                  )}
                </Select>
              </FormControl>
            </Grid>

            {/* Available Stock */}
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Available Stock"
                type="number"
                value={availableStock}
                onChange={(e) => setAvailableStock(e.target.value)}
                fullWidth
                required
                slotProps={{ htmlInput: { min: 0, step: 1 } }}
              />
            </Grid>

            {/* Reserved Stock */}
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Reserved Stock"
                type="number"
                value={reservedStock}
                onChange={(e) => setReservedStock(e.target.value)}
                fullWidth
                slotProps={{ htmlInput: { min: 0, step: 1 } }}
              />
            </Grid>

            {/* Shipped Stock */}
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Shipped Stock"
                type="number"
                value={shippedStock}
                onChange={(e) => setShippedStock(e.target.value)}
                fullWidth
                slotProps={{ htmlInput: { min: 0, step: 1 } }}
              />
            </Grid>
          </Grid>

          {/* Submit */}
          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isPending}
            >
              {isPending ? (
                <CircularProgress size={24} color="inherit" />
              ) : isEdit ? (
                'Update Stock Item'
              ) : (
                'Create Stock Item'
              )}
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/inventory')}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
