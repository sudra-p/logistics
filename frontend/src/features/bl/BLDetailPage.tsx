import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import BLStatusBadge from './components/BLStatusBadge';
import { useBLForBooking, useChangeBLStatus } from './hooks';
import type { BLStatus } from './hooks';

export default function BLDetailPage() {
  const { id: bookingIdParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bookingId = bookingIdParam ? parseInt(bookingIdParam, 10) : null;

  const blQuery = useBLForBooking(bookingId);
  const bl = blQuery.data;
  const statusMutation = useChangeBLStatus(bl?.id ?? 0);

  function handleStatusChange(newStatus: BLStatus) {
    statusMutation.mutate(
      { status: newStatus },
      {
        onSuccess: () => {
          void blQuery.refetch();
        },
      }
    );
  }

  if (blQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (blQuery.isError || !bl) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          No Bill of Lading found for this booking.
        </Alert>
        <Button
          variant="contained"
          sx={{ mt: 2 }}
          onClick={() => navigate(`/bookings/${bookingId}/bl/new`)}
        >
          Create Bill of Lading
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" component="h1">
            Bill of Lading
          </Typography>
          <BLStatusBadge status={bl.status} />
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" onClick={() => navigate(`/bookings/${bookingId}`)}>
            Back to Booking
          </Button>
          {bl.status !== 'RELEASED' && (
            <Button
              variant="outlined"
              onClick={() => navigate(`/bookings/${bookingId}/bl/edit`)}
            >
              Edit
            </Button>
          )}
        </Box>
      </Box>

      {statusMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to change status. Please try again.
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">BL Number</Typography>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>{bl.bl_number}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">BL Type</Typography>
            <Typography variant="body1">{bl.bl_type === 'LINE' ? 'Line BL' : 'Direct BL'}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Container Number</Typography>
            <Typography variant="body1">{bl.container_number}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Vessel Name</Typography>
            <Typography variant="body1">{bl.vessel_name}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Voyage Number</Typography>
            <Typography variant="body1">{bl.voyage_number}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Shipper</Typography>
            <Typography variant="body1">{bl.shipper_name || (bl.shipper ? `ID: ${bl.shipper}` : '—')}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" color="text.secondary">Consignee</Typography>
            <Typography variant="body1">{bl.consignee_name || (bl.consignee ? `ID: ${bl.consignee}` : '—')}</Typography>
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Typography variant="body2" color="text.secondary">Notify Party</Typography>
            <Typography variant="body1">{bl.notify_party || '—'}</Typography>
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Typography variant="body2" color="text.secondary">Cargo Description</Typography>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
              {bl.cargo_description || '—'}
            </Typography>
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Status Actions */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Typography variant="subtitle2" color="text.secondary">
            Actions:
          </Typography>
          {bl.status === 'DRAFT' && (
            <Button
              variant="contained"
              color="warning"
              size="small"
              onClick={() => handleStatusChange('SUBMITTED')}
              disabled={statusMutation.isPending}
            >
              Submit BL
            </Button>
          )}
          {bl.status === 'SUBMITTED' && (
            <Button
              variant="contained"
              color="success"
              size="small"
              onClick={() => handleStatusChange('RELEASED')}
              disabled={statusMutation.isPending}
            >
              Release BL
            </Button>
          )}
          {bl.status === 'RELEASED' && (
            <Typography variant="body2" color="success.main">
              BL has been released — no further actions available.
            </Typography>
          )}
        </Box>
      </Paper>
    </Box>
  );
}
