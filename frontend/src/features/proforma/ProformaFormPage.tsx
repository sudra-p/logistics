import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Button,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import LineItemTable from './components/LineItemTable';
import {
  useProformaDetail,
  useCreateProforma,
  useUpdateProforma,
} from './hooks';
import type { ProformaLineItem, PICurrency, CreateProformaPayload } from './hooks';

interface MasterDataOption {
  id: number;
  name: string;
}

export default function ProformaFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditMode = !!id;
  const piId = id ? Number(id) : null;

  // Form state
  const [date, setDate] = useState('');
  const [customer, setCustomer] = useState<number | ''>('');
  const [currency, setCurrency] = useState<PICurrency>('USD');
  const [exchangeRate, setExchangeRate] = useState('1.0000');
  const [paymentTerms, setPaymentTerms] = useState('');
  const [expectedShipmentDate, setExpectedShipmentDate] = useState('');
  const [lineItems, setLineItems] = useState<ProformaLineItem[]>([
    { product_name: '', quantity: 0, rate: 0, amount: 0 },
  ]);
  const [formError, setFormError] = useState('');

  // Load existing PI for edit mode
  const piQuery = useProformaDetail(piId);

  // Load customers dropdown
  const clientsQuery = useQuery<MasterDataOption[]>({
    queryKey: ['master-data', 'clients', 'active'],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.MASTER_DATA('clients'), {
        params: { is_active: true, page_size: 1000 },
      });
      const data = response.data;
      const results = Array.isArray(data) ? data : data.results ?? [];
      return results.map((item: { id: number; name: string }) => ({
        id: item.id,
        name: item.name,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });

  // Mutations
  const createMutation = useCreateProforma();
  const updateMutation = useUpdateProforma(piId ?? 0);

  // Populate form on edit
  useEffect(() => {
    if (piQuery.data) {
      const pi = piQuery.data;
      setDate(pi.date);
      setCustomer(pi.customer);
      setCurrency(pi.currency);
      setExchangeRate(String(pi.exchange_rate));
      setPaymentTerms(pi.payment_terms);
      setExpectedShipmentDate(pi.expected_shipment_date);
      setLineItems(
        pi.line_items.length > 0
          ? pi.line_items
          : [{ product_name: '', quantity: 0, rate: 0, amount: 0 }],
      );
    }
  }, [piQuery.data]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    // Basic validation
    const validItems = lineItems.filter((item) => item.product_name.trim() !== '');
    if (validItems.length === 0) {
      setFormError('At least one line item with a product name is required.');
      return;
    }
    if (!customer) {
      setFormError('Customer is required.');
      return;
    }
    if (!date) {
      setFormError('PI Date is required.');
      return;
    }
    if (!expectedShipmentDate) {
      setFormError('Expected Shipment Date is required.');
      return;
    }

    const payload: CreateProformaPayload = {
      date,
      customer: customer as number,
      currency,
      exchange_rate: parseFloat(exchangeRate) || 1,
      payment_terms: paymentTerms,
      expected_shipment_date: expectedShipmentDate,
      line_items: validItems.map((item) => ({
        product_name: item.product_name,
        quantity: item.quantity,
        rate: item.rate,
        amount: item.quantity * item.rate,
      })),
    };

    const mutation = isEditMode ? updateMutation : createMutation;
    mutation.mutate(payload, {
      onSuccess: (data) => {
        navigate(`/proforma/${data.id}`);
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

  // Loading state for edit mode
  if (isEditMode && piQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isEditMode && piQuery.isError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load proforma invoice data.</Alert>
      </Box>
    );
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {isEditMode ? 'Edit Proforma Invoice' : 'New Proforma Invoice'}
      </Typography>

      {formError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {formError}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSubmit} noValidate>
          <Grid container spacing={2}>
            {/* Customer Dropdown */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth required>
                <InputLabel id="customer-label">Customer</InputLabel>
                <Select
                  labelId="customer-label"
                  label="Customer"
                  value={customer}
                  onChange={(e) => setCustomer(e.target.value as number)}
                >
                  {clientsQuery.isLoading && (
                    <MenuItem disabled value="">Loading...</MenuItem>
                  )}
                  {(clientsQuery.data ?? []).map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* PI Date */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="PI Date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                fullWidth
                required
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>

            {/* Currency */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth required>
                <InputLabel id="currency-label">Currency</InputLabel>
                <Select
                  labelId="currency-label"
                  label="Currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value as PICurrency)}
                >
                  <MenuItem value="USD">USD</MenuItem>
                  <MenuItem value="INR">INR</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Exchange Rate */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Exchange Rate (USD to INR)"
                type="number"
                value={exchangeRate}
                onChange={(e) => setExchangeRate(e.target.value)}
                fullWidth
                slotProps={{ htmlInput: { min: 0, step: '0.0001' } }}
              />
            </Grid>

            {/* Expected Shipment Date */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Expected Shipment Date"
                type="date"
                value={expectedShipmentDate}
                onChange={(e) => setExpectedShipmentDate(e.target.value)}
                fullWidth
                required
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>

            {/* Payment Terms */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Payment Terms"
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                fullWidth
                multiline
                rows={3}
                placeholder="e.g., 50% advance, 50% before shipment"
              />
            </Grid>
          </Grid>

          {/* Line Items */}
          <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
            Line Items
          </Typography>
          <LineItemTable
            items={lineItems}
            onChange={setLineItems}
            currency={currency}
          />

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
              ) : isEditMode ? (
                'Update PI'
              ) : (
                'Create PI'
              )}
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/proforma')}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
