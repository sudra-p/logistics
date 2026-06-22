import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Grid,
  Button,
  CircularProgress,
  Alert,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import apiClient from '@/api/client';
import BLAutoFillPreview from './components/BLAutoFillPreview';
import { useBLForBooking, useCreateBL, useUpdateBL } from './hooks';
import type { BLType } from './hooks';

interface ShipperOption {
  id: number;
  name: string;
}

interface ConsigneeOption {
  id: number;
  name: string;
}

export default function BLFormPage() {
  const { id: bookingIdParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bookingId = bookingIdParam ? parseInt(bookingIdParam, 10) : null;

  const [blNumber, setBLNumber] = useState('');
  const [blType, setBLType] = useState<BLType>('LINE');
  const [containerNumber, setContainerNumber] = useState('');
  const [vesselName, setVesselName] = useState('');
  const [voyageNumber, setVoyageNumber] = useState('');
  const [shipper, setShipper] = useState<number | ''>('');
  const [consignee, setConsignee] = useState<number | ''>('');
  const [notifyParty, setNotifyParty] = useState('');
  const [cargoDescription, setCargoDescription] = useState('');
  const [formError, setFormError] = useState('');
  const [shippers, setShippers] = useState<ShipperOption[]>([]);
  const [consignees, setConsignees] = useState<ConsigneeOption[]>([]);
  const [vessels, setVessels] = useState<{ id: number; name: string }[]>([]);

  // Fetch existing BL
  const blQuery = useBLForBooking(bookingId);
  const existingBL = blQuery.data;
  const isExisting = Boolean(existingBL);

  // Mutations
  const createMutation = useCreateBL(bookingId ?? 0);
  const updateMutation = useUpdateBL(existingBL?.id ?? 0);

  // Load master data (shippers, consignees, vessels)
  useEffect(() => {
    apiClient.get('master-data/shippers/').then((res) => {
      const data = res.data?.results ?? res.data ?? [];
      setShippers(data);
    }).catch(() => {});
    apiClient.get('master-data/consignees/').then((res) => {
      const data = res.data?.results ?? res.data ?? [];
      setConsignees(data);
    }).catch(() => {});
    apiClient.get('master-data/vessels/').then((res) => {
      const data = res.data?.results ?? res.data ?? [];
      setVessels(data);
    }).catch(() => {});
  }, []);

  // Populate form from existing BL or auto-fill
  useEffect(() => {
    if (existingBL) {
      setBLNumber(existingBL.bl_number);
      setBLType(existingBL.bl_type);
      setContainerNumber(existingBL.container_number);
      setVesselName(existingBL.vessel_name);
      setVoyageNumber(existingBL.voyage_number);
      setShipper(existingBL.shipper);
      setConsignee(existingBL.consignee);
      setNotifyParty(existingBL.notify_party || '');
      setCargoDescription(existingBL.cargo_description || '');
    }
  }, [existingBL]);

  const autoFillData = existingBL
    ? {}
    : {
        vessel_name: vesselName || undefined,
        voyage_number: voyageNumber || undefined,
        container_number: containerNumber || undefined,
        shipper_name: shippers.find((s) => s.id === shipper)?.name,
        consignee_name: consignees.find((c) => c.id === consignee)?.name,
      };

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!blNumber.trim()) {
      setFormError('BL Number is required.');
      return;
    }
    if (!shipper || !consignee) {
      setFormError('Shipper and Consignee are required.');
      return;
    }

    const payload = {
      bl_number: blNumber,
      bl_type: blType,
      container_number: containerNumber,
      vessel_name: vesselName,
      voyage_number: voyageNumber,
      shipper: shipper as number,
      consignee: consignee as number,
      notify_party: notifyParty,
      cargo_description: cargoDescription,
    };

    const mutation = isExisting ? updateMutation : createMutation;

    mutation.mutate(payload, {
      onSuccess: () => {
        navigate(`/bookings/${bookingId}/bl`);
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

  if (blQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {isExisting ? 'Edit Bill of Lading' : 'Create Bill of Lading'}
        </Typography>
        <Button variant="outlined" onClick={() => navigate(`/bookings/${bookingId}`)}>
          Back to Booking
        </Button>
      </Box>

      {!isExisting && <BLAutoFillPreview data={autoFillData} />}

      {formError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {formError}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSubmit} noValidate>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="BL Number"
                value={blNumber}
                onChange={(e) => setBLNumber(e.target.value)}
                fullWidth
                required
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>BL Type</InputLabel>
                <Select
                  value={blType}
                  label="BL Type"
                  onChange={(e) => setBLType(e.target.value as BLType)}
                >
                  <MenuItem value="LINE">Line BL</MenuItem>
                  <MenuItem value="DIRECT">Direct BL</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Container Number"
                value={containerNumber}
                onChange={(e) => setContainerNumber(e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Vessel Name</InputLabel>
                <Select
                  value={vesselName}
                  label="Vessel Name"
                  onChange={(e) => setVesselName(e.target.value as string)}
                >
                  {vessels.map((v) => (
                    <MenuItem key={v.id} value={v.name}>{v.name}</MenuItem>
                  ))}
                  {vesselName && !vessels.some((v) => v.name === vesselName) && (
                    <MenuItem value={vesselName}>{vesselName}</MenuItem>
                  )}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Voyage Number"
                value={voyageNumber}
                onChange={(e) => setVoyageNumber(e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth required>
                <InputLabel>Shipper</InputLabel>
                <Select
                  value={shipper}
                  label="Shipper"
                  onChange={(e) => setShipper(e.target.value as number)}
                >
                  {shippers.map((s) => (
                    <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth required>
                <InputLabel>Consignee</InputLabel>
                <Select
                  value={consignee}
                  label="Consignee"
                  onChange={(e) => setConsignee(e.target.value as number)}
                >
                  {consignees.map((c) => (
                    <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField
                label="Notify Party"
                value={notifyParty}
                onChange={(e) => setNotifyParty(e.target.value)}
                fullWidth
                multiline
                rows={2}
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField
                label="Cargo Description"
                value={cargoDescription}
                onChange={(e) => setCargoDescription(e.target.value)}
                fullWidth
                multiline
                rows={3}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isPending}
            >
              {isPending ? (
                <CircularProgress size={24} color="inherit" />
              ) : isExisting ? (
                'Save Changes'
              ) : (
                'Create BL'
              )}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
