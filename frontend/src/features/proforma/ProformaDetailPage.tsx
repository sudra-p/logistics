import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import PIStatusBadge from './components/PIStatusBadge';
import LineItemTable from './components/LineItemTable';
import {
  useProformaDetail,
  useProformaPayments,
  useProformaBookings,
  useChangeProformaStatus,
} from './hooks';
import type { PIStatus } from './hooks';

/** Determines the next allowed status transitions. */
const NEXT_ACTIONS: Record<PIStatus, { label: string; nextStatus: PIStatus }[]> = {
  DRAFT: [{ label: 'Send to Customer', nextStatus: 'SENT' }],
  SENT: [{ label: 'Mark Approved', nextStatus: 'APPROVED' }],
  APPROVED: [{ label: 'Mark Payment Pending', nextStatus: 'PAYMENT_PENDING' }],
  PAYMENT_PENDING: [{ label: 'Mark Paid', nextStatus: 'PAID' }],
  PAID: [],
};

export default function ProformaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const piId = id ? Number(id) : null;

  const piQuery = useProformaDetail(piId);
  const paymentsQuery = useProformaPayments(piId);
  const bookingsQuery = useProformaBookings(piId);
  const statusMutation = useChangeProformaStatus(piId ?? 0);

  if (piQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (piQuery.isError || !piQuery.data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void piQuery.refetch()}>
              Retry
            </Button>
          }
        >
          Failed to load proforma invoice.
        </Alert>
      </Box>
    );
  }

  const pi = piQuery.data;
  const actions = NEXT_ACTIONS[pi.status] ?? [];
  const payments = paymentsQuery.data ?? [];
  const bookings = bookingsQuery.data ?? [];
  const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount), 0);
  const outstanding = Number(pi.total_amount) - totalPaid;

  function handleStatusChange(nextStatus: PIStatus) {
    statusMutation.mutate(
      { status: nextStatus },
      { onSuccess: () => void piQuery.refetch() },
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1">
            {pi.pi_number}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
            <PIStatusBadge status={pi.status} />
            {pi.customer_name && (
              <Typography variant="body2" color="text.secondary">
                — {pi.customer_name}
              </Typography>
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {pi.status === 'DRAFT' && (
            <Button
              variant="outlined"
              onClick={() => navigate(`/proforma/${pi.id}/edit`)}
            >
              Edit
            </Button>
          )}
          {actions.map((action) => (
            <Button
              key={action.nextStatus}
              variant="contained"
              onClick={() => handleStatusChange(action.nextStatus)}
              disabled={statusMutation.isPending}
            >
              {action.label}
            </Button>
          ))}
        </Box>
      </Box>

      {statusMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to update status. Please try again.
        </Alert>
      )}

      {/* Details */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Invoice Details
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Date</Typography>
            <Typography variant="body1">{pi.date}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Currency</Typography>
            <Typography variant="body1">{pi.currency}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Exchange Rate</Typography>
            <Typography variant="body1">{pi.exchange_rate}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Expected Shipment</Typography>
            <Typography variant="body1">{pi.expected_shipment_date}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Payment Terms</Typography>
            <Typography variant="body1">{pi.payment_terms || '—'}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Total Amount</Typography>
            <Typography variant="h6">
              {Number(pi.total_amount).toFixed(2)} {pi.currency}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Line Items */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Line Items
        </Typography>
        <LineItemTable
          items={pi.line_items}
          onChange={() => {}}
          readOnly
          currency={pi.currency}
        />
      </Paper>

      {/* Payment History */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Payment History
        </Typography>
        <Box sx={{ mb: 2, display: 'flex', gap: 3 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">Total Paid</Typography>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {totalPaid.toFixed(2)} {pi.currency}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">Outstanding</Typography>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }} color={outstanding > 0 ? 'warning.main' : 'success.main'}>
              {outstanding.toFixed(2)} {pi.currency}
            </Typography>
          </Box>
        </Box>
        {paymentsQuery.isLoading ? (
          <CircularProgress size={20} />
        ) : payments.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No payments recorded yet.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Amount</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Reference</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>{payment.payment_date}</TableCell>
                    <TableCell align="right">{Number(payment.amount).toFixed(2)}</TableCell>
                    <TableCell>{payment.payment_mode}</TableCell>
                    <TableCell>{payment.reference_number || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Linked Bookings */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Linked Bookings
        </Typography>
        {bookingsQuery.isLoading ? (
          <CircularProgress size={20} />
        ) : bookings.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No bookings linked to this proforma invoice.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Job Number</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Booking Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bookings.map((booking) => (
                  <TableRow
                    key={booking.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/bookings/${booking.id}`)}
                  >
                    <TableCell>{booking.job_number}</TableCell>
                    <TableCell>
                      <Chip label={booking.status} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{booking.booking_date}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}
