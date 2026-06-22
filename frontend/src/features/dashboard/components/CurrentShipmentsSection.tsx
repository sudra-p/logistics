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
  Chip,
  CircularProgress,
} from '@mui/material';
import { useCurrentShipments } from '../dashboardHooks';

const STATUS_COLORS: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  PENDING: 'default',
  BOOKED: 'info',
  STUFFING: 'warning',
  SHIPPED: 'success',
};

export default function CurrentShipmentsSection() {
  const navigate = useNavigate();
  const { data, isLoading } = useCurrentShipments();

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
        Current Shipments
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Booking #</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Customer</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Container</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>ETD</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>ETA</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    No active shipments.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {items.map((item) => (
              <TableRow
                key={item.id}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => navigate(`/bookings/${item.id}`)}
              >
                <TableCell>{item.job_number}</TableCell>
                <TableCell>{item.customer_name}</TableCell>
                <TableCell>{item.container_number || '—'}</TableCell>
                <TableCell>
                  <Chip
                    label={item.status}
                    size="small"
                    color={STATUS_COLORS[item.status] ?? 'default'}
                  />
                </TableCell>
                <TableCell>{item.etd || '—'}</TableCell>
                <TableCell>{item.eta || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
