import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Autocomplete,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { useCreatePayment, useProformaPayments } from './hooks';
import type { PaymentMode, CreatePaymentPayload } from './hooks';

interface PIOption {
  id: number;
  pi_number: string;
  customer_name: string;
  total_amount: number;
}

const PAYMENT_MODE_OPTIONS: { value: PaymentMode; label: string }[] = [
  { value: 'BANK', label: 'Bank Transfer' },
  { value: 'CASH', label: 'Cash' },
  { value: 'LC', label: 'Letter of Credit' },
];

export default function PaymentFormPage() {
  const navigate = useNavigate();

  // Form state
  const [selectedPI, setSelectedPI] = useState<PIOption | null>(null);
  const [amount, setAmount] = useState('');
  const [paymentMode, setPaymentMode] = useState<PaymentMode>('BANK');
  const [paymentDate, setPaymentDate] = useState('');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState('');

  // Load PI list for searchable dropdown
  const piListQuery = useQuery<PIOption[]>({
    queryKey: ['proforma-invoices', 'for-payment-dropdown'],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.PROFORMA_INVOICES, {
        params: { page_size: 1000 },
      });
      const data = response.data;
      const results = Array.isArray(data) ? data : data.results ?? [];
      return results.map((pi: { id: number; pi_number: string; customer_name: string; total_amount: number }) => ({
        id: pi.id,
        pi_number: pi.pi_number,
        customer_name: pi.customer_name,
        total_amount: Number(pi.total_amount),
      }));
    },
    staleTime: 2 * 60 * 1000,
  });

  // Fetch payment summary for selected PI
  const paymentSummary = useProformaPayments(selectedPI?.id ?? null);

  // Mutation
  const createMutation = useCreatePayment();

  // Set today's date as default
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0] ?? '';
    setPaymentDate(today);
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!selectedPI) {
      setFormError('Please select a Proforma Invoice.');
      return;
    }
    if (!amount || Number(amount) <= 0) {
      setFormError('Payment amount must be a positive number.');
      return;
    }
    if (!paymentDate) {
      setFormError('Payment date is required.');
      return;
    }

    // Validate amount doesn't exceed outstanding balance
    if (paymentSummary.data) {
      const outstandingBalance = paymentSummary.data.outstanding_balance;
      if (Number(amount) > outstandingBalance) {
        setFormError(
          `Payment amount (${Number(amount).toFixed(2)}) exceeds outstanding balance (${outstandingBalance.toFixed(2)}). Please enter a valid amount.`
        );
        return;
      }
    }

    const payload: CreatePaymentPayload = {
      proforma_invoice: selectedPI.id,
      amount: Number(amount),
      payment_mode: paymentMode,
      payment_date: paymentDate,
      reference_number: referenceNumber || undefined,
      notes: notes || undefined,
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        navigate('/payments');
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

  const isPending = createMutation.isPending;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        New Payment
      </Typography>

      {formError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {formError}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSubmit} noValidate>
          <Grid container spacing={2}>
            {/* PI Selector (Searchable Dropdown) */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <Autocomplete
                options={piListQuery.data ?? []}
                getOptionLabel={(option) => `${option.pi_number} — ${option.customer_name}`}
                value={selectedPI}
                onChange={(_, newValue) => setSelectedPI(newValue)}
                loading={piListQuery.isLoading}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Proforma Invoice"
                    required
                    placeholder="Search by PI number or customer..."
                  />
                )}
                isOptionEqualToValue={(option, value) => option.id === value.id}
              />
            </Grid>

            {/* Amount */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Payment Amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                fullWidth
                required
                slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
              />
            </Grid>

            {/* Payment Mode */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth required>
                <InputLabel id="payment-mode-label">Payment Mode</InputLabel>
                <Select
                  labelId="payment-mode-label"
                  label="Payment Mode"
                  value={paymentMode}
                  onChange={(e) => setPaymentMode(e.target.value as PaymentMode)}
                >
                  {PAYMENT_MODE_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Payment Date */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Payment Date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                fullWidth
                required
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>

            {/* Reference Number */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Reference Number"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                fullWidth
                placeholder="e.g., TXN-12345"
              />
            </Grid>

            {/* Notes */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                fullWidth
                multiline
                rows={3}
                placeholder="Optional payment notes..."
              />
            </Grid>
          </Grid>

          {/* Read-only computed fields */}
          {selectedPI && (
            <Paper variant="outlined" sx={{ mt: 3, p: 2, backgroundColor: 'grey.50' }}>
              <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
                Invoice Summary
              </Typography>
              {paymentSummary.isLoading ? (
                <CircularProgress size={20} />
              ) : paymentSummary.data ? (
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      Customer Name
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {paymentSummary.data.customer_name}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      PI Total Amount
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {paymentSummary.data.total_amount.toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      Outstanding Balance
                    </Typography>
                    <Typography
                      variant="body1"
                      sx={{
                        fontWeight: 600,
                        color: paymentSummary.data.outstanding_balance > 0 ? 'warning.main' : 'success.main',
                      }}
                    >
                      {paymentSummary.data.outstanding_balance.toFixed(2)}
                    </Typography>
                  </Grid>
                </Grid>
              ) : null}
            </Paper>
          )}

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
              ) : (
                'Record Payment'
              )}
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/payments')}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
