import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Chip,
} from '@mui/material';
import { useProformaStatus } from '../dashboardHooks';

const STATUS_COLORS: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  DRAFT: 'default',
  SENT: 'info',
  APPROVED: 'success',
  PAYMENT_PENDING: 'warning',
};

export default function ProformaStatusSection() {
  const navigate = useNavigate();
  const { data, isLoading } = useProformaStatus();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const items = data ?? [];

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Proforma Status
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>PI Number</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Customer</TableCell>
              <TableCell sx={{ fontWeight: 600 }} align="right">Amount</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    All proforma invoices are paid.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {items.map((item) => (
              <TableRow
                key={item.id}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => navigate(`/proforma/${item.id}`)}
              >
                <TableCell>{item.pi_number}</TableCell>
                <TableCell>{item.customer_name}</TableCell>
                <TableCell align="right">{Number(item.total_amount).toFixed(2)}</TableCell>
                <TableCell>
                  <Chip
                    label={item.status.replace('_', ' ')}
                    size="small"
                    color={STATUS_COLORS[item.status] ?? 'default'}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
