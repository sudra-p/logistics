import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import { usePaymentList } from './hooks';
import type { PaymentMode } from './hooks';

const PAYMENT_MODE_LABELS: Record<PaymentMode, string> = {
  BANK: 'Bank Transfer',
  CASH: 'Cash',
  LC: 'Letter of Credit',
};

function PaymentModeBadge({ mode }: { mode: PaymentMode }) {
  const colorMap: Record<PaymentMode, 'primary' | 'success' | 'warning'> = {
    BANK: 'primary',
    CASH: 'success',
    LC: 'warning',
  };
  return <Chip label={PAYMENT_MODE_LABELS[mode]} size="small" color={colorMap[mode]} variant="outlined" />;
}

export default function PaymentListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  const { data, isLoading, isError, refetch } = usePaymentList({
    page: page + 1,
    pageSize,
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Payments
        </Typography>
        <Button
          variant="contained"
          startIcon={<span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>}
          onClick={() => navigate('/payments/new')}
        >
          New Payment
        </Button>
      </Box>

      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Error state */}
      {isError && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void refetch()}>
              Retry
            </Button>
          }
        >
          Failed to load payments. Please try again.
        </Alert>
      )}

      {/* Table */}
      {data && (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>PI Number</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Customer</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Amount</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Reference</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                        No payments found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.results.map((payment) => (
                  <TableRow key={payment.id} hover>
                    <TableCell>{payment.pi_number}</TableCell>
                    <TableCell>{payment.customer_name}</TableCell>
                    <TableCell align="right">{Number(payment.amount).toFixed(2)}</TableCell>
                    <TableCell>
                      <PaymentModeBadge mode={payment.payment_mode} />
                    </TableCell>
                    <TableCell>{payment.payment_date}</TableCell>
                    <TableCell>{payment.reference_number || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={data.count}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => {
              setPageSize(parseInt(e.target.value, 10));
              setPage(0);
            }}
            rowsPerPageOptions={[10, 25, 50]}
          />
        </>
      )}
    </Box>
  );
}
