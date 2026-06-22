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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material';
import PIStatusBadge from './components/PIStatusBadge';
import { useProformaList } from './hooks';
import { useAuth } from '@/auth/useAuth';
import type { PIStatus } from './hooks';

const STATUS_OPTIONS: { value: PIStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'SENT', label: 'Sent' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'PAYMENT_PENDING', label: 'Payment Pending' },
  { value: 'PAID', label: 'Paid' },
];

export default function ProformaListPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [statusFilter, setStatusFilter] = useState<PIStatus | ''>('');

  const { data, isLoading, isError, refetch } = useProformaList({
    page: page + 1, // API is 1-indexed
    pageSize,
    status: statusFilter,
  });

  const pageTitle = role === 'Sales' ? 'My Proformas' : 'Proforma Invoices';

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {pageTitle}
        </Typography>
        <Button
          variant="contained"
          startIcon={<span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>}
          onClick={() => navigate('/proforma/new')}
        >
          New PI
        </Button>
      </Box>

      {/* Status Filter */}
      <Box sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="status-filter-label">Status</InputLabel>
          <Select
            labelId="status-filter-label"
            label="Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as PIStatus | '');
              setPage(0);
            }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
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
          Failed to load proforma invoices. Please try again.
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
                  <TableCell sx={{ fontWeight: 600 }}>Currency</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                        No proforma invoices found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.results.map((pi) => (
                  <TableRow
                    key={pi.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/proforma/${pi.id}`)}
                  >
                    <TableCell>{pi.pi_number}</TableCell>
                    <TableCell>{pi.customer_name}</TableCell>
                    <TableCell align="right">{Number(pi.total_amount).toFixed(2)}</TableCell>
                    <TableCell>{pi.currency}</TableCell>
                    <TableCell>
                      <PIStatusBadge status={pi.status} />
                    </TableCell>
                    <TableCell>{pi.date}</TableCell>
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
