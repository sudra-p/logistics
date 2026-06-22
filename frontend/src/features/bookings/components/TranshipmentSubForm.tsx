import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  Grid,
  Button,
  IconButton,
  Alert,
  CircularProgress,
  Paper,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { useTranshipments } from '../useTranshipments';
import type { TranshipmentLegPayload } from '../useTranshipments';

/** Max number of transhipment legs allowed. */
const MAX_LEGS = 4;

/** Master data option shape. */
interface PortOption {
  id: number;
  name: string;
}

/** Local state for a single leg in the form. */
interface LegFormState {
  /** If this leg already exists on the server, its ID. */
  id: number | null;
  port: number | '';
  eta: string;
  connecting_vessel_voyage: string;
  etd: string;
}

/** Validation errors for a single leg. */
interface LegErrors {
  port?: string;
  eta?: string;
  connecting_vessel_voyage?: string;
  etd?: string;
}

/** Creates a blank leg form state. */
function createEmptyLeg(): LegFormState {
  return { id: null, port: '', eta: '', connecting_vessel_voyage: '', etd: '' };
}

/**
 * Validates a single leg and returns field-level errors.
 */
function validateLeg(leg: LegFormState): LegErrors {
  const errors: LegErrors = {};

  if (!leg.port) {
    errors.port = 'Port is required';
  }
  if (!leg.eta) {
    errors.eta = 'ETA is required';
  }
  if (!leg.connecting_vessel_voyage.trim()) {
    errors.connecting_vessel_voyage = 'Connecting vessel/voyage is required';
  } else if (leg.connecting_vessel_voyage.length > 200) {
    errors.connecting_vessel_voyage = 'Maximum 200 characters';
  }
  if (!leg.etd) {
    errors.etd = 'ETD is required';
  }

  // ETD must be after ETA
  if (leg.eta && leg.etd) {
    const etaDate = new Date(leg.eta);
    const etdDate = new Date(leg.etd);
    if (etdDate <= etaDate) {
      errors.etd = 'ETD must be after ETA';
    }
  }

  return errors;
}

/**
 * Validates chronological ordering between legs.
 * Each subsequent leg's eta must be >= previous leg's etd.
 * Returns an array of leg-index-to-error mappings.
 */
function validateChronologicalOrder(legs: LegFormState[]): Map<number, string> {
  const orderErrors = new Map<number, string>();

  for (let i = 1; i < legs.length; i++) {
    const prevLeg = legs[i - 1]!;
    const currLeg = legs[i]!;

    if (prevLeg.etd && currLeg.eta) {
      const prevEtd = new Date(prevLeg.etd);
      const currEta = new Date(currLeg.eta);
      if (currEta < prevEtd) {
        orderErrors.set(
          i,
          `Leg ${i + 1} ETA must be on or after Leg ${i} ETD`,
        );
      }
    }
  }

  return orderErrors;
}

interface TranshipmentSubFormProps {
  bookingId: number | null;
}

/**
 * TranshipmentSubForm: Repeatable section for managing transhipment legs (max 4).
 * Integrates with the booking form page for create and edit flows.
 */
export default function TranshipmentSubForm({ bookingId }: TranshipmentSubFormProps) {
  const {
    legs: existingLegs,
    isLoading,
    isError,
    refetch,
    createLegs,
    updateLeg,
    deleteLeg,
  } = useTranshipments(bookingId);

  // ─── Port options (active ports only) ──────────────────────────────────────
  const portsQuery = useQuery<PortOption[]>({
    queryKey: ['master-data', 'ports', 'active'],
    queryFn: async () => {
      const response = await apiClient.get(ENDPOINTS.MASTER_DATA('ports'), {
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

  const portOptions = portsQuery.data ?? [];

  // ─── Local leg state ───────────────────────────────────────────────────────
  const [legs, setLegs] = useState<LegFormState[]>([]);
  const [legErrors, setLegErrors] = useState<Map<number, LegErrors>>(new Map());
  const [orderErrors, setOrderErrors] = useState<Map<number, string>>(new Map());
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Sync local state when existing legs load from the API
  useEffect(() => {
    if (existingLegs.length > 0) {
      setLegs(
        existingLegs.map((leg) => ({
          id: leg.id,
          port: leg.port,
          eta: leg.eta,
          connecting_vessel_voyage: leg.connecting_vessel_voyage,
          etd: leg.etd,
        })),
      );
    }
  }, [existingLegs]);

  // ─── Handlers ──────────────────────────────────────────────────────────────

  const addLeg = useCallback(() => {
    if (legs.length >= MAX_LEGS) return;
    setLegs((prev) => [...prev, createEmptyLeg()]);
  }, [legs.length]);

  const removeLeg = useCallback(
    async (index: number) => {
      const leg = legs[index];
      if (!leg) return;

      // If the leg exists on the server, delete it
      if (leg.id !== null && bookingId) {
        try {
          await deleteLeg.mutateAsync(leg.id);
        } catch {
          setGeneralError('Failed to delete transhipment leg. Please try again.');
          return;
        }
      }

      // Remove from local state
      setLegs((prev) => prev.filter((_, i) => i !== index));
      // Clear errors for removed leg
      setLegErrors((prev) => {
        const next = new Map(prev);
        next.delete(index);
        return next;
      });
      setOrderErrors(new Map());
    },
    [legs, bookingId, deleteLeg],
  );

  const updateLegField = useCallback(
    (index: number, field: keyof LegFormState, value: string | number) => {
      setLegs((prev) =>
        prev.map((leg, i) => (i === index ? { ...leg, [field]: value } : leg)),
      );
      // Clear field error on change
      setLegErrors((prev) => {
        const next = new Map(prev);
        const existing = next.get(index);
        if (existing) {
          const updated = { ...existing };
          delete updated[field as keyof LegErrors];
          next.set(index, updated);
        }
        return next;
      });
    },
    [],
  );

  // ─── Validation & Save ─────────────────────────────────────────────────────

  const validateAll = useCallback((): boolean => {
    let valid = true;
    const newLegErrors = new Map<number, LegErrors>();

    for (let i = 0; i < legs.length; i++) {
      const leg = legs[i]!;
      const errors = validateLeg(leg);
      if (Object.keys(errors).length > 0) {
        newLegErrors.set(i, errors);
        valid = false;
      }
    }

    setLegErrors(newLegErrors);

    // Chronological ordering validation
    const chronoErrors = validateChronologicalOrder(legs);
    setOrderErrors(chronoErrors);
    if (chronoErrors.size > 0) {
      valid = false;
    }

    return valid;
  }, [legs]);

  const handleSave = useCallback(async () => {
    setGeneralError(null);

    if (legs.length === 0) {
      return; // Nothing to save
    }

    if (!validateAll()) {
      return;
    }

    if (!bookingId) {
      setGeneralError('Please save the booking first before adding transhipment legs.');
      return;
    }

    // Separate new legs from existing legs
    const newLegs = legs.filter((l) => l.id === null);
    const existingLegsToUpdate = legs.filter((l) => l.id !== null);

    try {
      // Create new legs
      if (newLegs.length > 0) {
        const payload: TranshipmentLegPayload[] = newLegs.map((l) => ({
          port: l.port as number,
          eta: l.eta,
          connecting_vessel_voyage: l.connecting_vessel_voyage,
          etd: l.etd,
        }));
        await createLegs.mutateAsync(payload);
      }

      // Update existing legs
      for (const leg of existingLegsToUpdate) {
        await updateLeg.mutateAsync({
          legId: leg.id!,
          data: {
            port: leg.port as number,
            eta: leg.eta,
            connecting_vessel_voyage: leg.connecting_vessel_voyage,
            etd: leg.etd,
          },
        });
      }
    } catch {
      setGeneralError('Failed to save transhipment legs. Please try again.');
    }
  }, [legs, bookingId, validateAll, createLegs, updateLeg]);

  // ─── Render ────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (isError) {
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={() => void refetch()}>
            Retry
          </Button>
        }
      >
        Failed to load transhipment legs.
      </Alert>
    );
  }

  const isSaving = createLegs.isPending || updateLeg.isPending;
  const canAddLeg = legs.length < MAX_LEGS;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Transhipment Legs</Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={addLeg}
          disabled={!canAddLeg}
        >
          Add Leg
        </Button>
      </Box>

      {generalError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setGeneralError(null)}>
          {generalError}
        </Alert>
      )}

      {legs.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          No transhipment legs defined. Click "Add Leg" to add one.
        </Typography>
      )}

      {legs.map((leg, index) => {
        const errors = legErrors.get(index) ?? {};
        const orderError = orderErrors.get(index);

        return (
          <Paper
            key={leg.id ?? `new-${index}`}
            variant="outlined"
            sx={{ p: 2, mb: 2 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="subtitle2">
                Leg {index + 1}
              </Typography>
              <IconButton
                size="small"
                color="error"
                onClick={() => void removeLeg(index)}
                aria-label={`Delete leg ${index + 1}`}
                disabled={deleteLeg.isPending}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>

            {orderError && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                {orderError}
              </Alert>
            )}

            <Grid container spacing={2}>
              {/* Port dropdown */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <FormControl fullWidth error={!!errors.port} size="small">
                  <InputLabel id={`transhipment-port-${index}-label`}>
                    Port *
                  </InputLabel>
                  <Select
                    labelId={`transhipment-port-${index}-label`}
                    label="Port *"
                    value={leg.port}
                    onChange={(e) =>
                      updateLegField(index, 'port', Number(e.target.value))
                    }
                  >
                    {portsQuery.isLoading && (
                      <MenuItem disabled value="">
                        Loading...
                      </MenuItem>
                    )}
                    {portOptions.map((port) => (
                      <MenuItem key={port.id} value={port.id}>
                        {port.name}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.port && <FormHelperText>{errors.port}</FormHelperText>}
                </FormControl>
              </Grid>

              {/* ETA */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  label="ETA *"
                  type="datetime-local"
                  size="small"
                  fullWidth
                  slotProps={{ inputLabel: { shrink: true } }}
                  value={leg.eta}
                  onChange={(e) => updateLegField(index, 'eta', e.target.value)}
                  error={!!errors.eta}
                  helperText={errors.eta}
                />
              </Grid>

              {/* Connecting Vessel/Voyage */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  label="Vessel/Voyage *"
                  size="small"
                  fullWidth
                  value={leg.connecting_vessel_voyage}
                  onChange={(e) =>
                    updateLegField(index, 'connecting_vessel_voyage', e.target.value)
                  }
                  error={!!errors.connecting_vessel_voyage}
                  helperText={errors.connecting_vessel_voyage}
                  slotProps={{ htmlInput: { maxLength: 200 } }}
                />
              </Grid>

              {/* ETD */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  label="ETD *"
                  type="datetime-local"
                  size="small"
                  fullWidth
                  slotProps={{ inputLabel: { shrink: true } }}
                  value={leg.etd}
                  onChange={(e) => updateLegField(index, 'etd', e.target.value)}
                  error={!!errors.etd}
                  helperText={errors.etd}
                />
              </Grid>
            </Grid>
          </Paper>
        );
      })}

      {/* Save button – only show when there are legs */}
      {legs.length > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
          <Button
            variant="contained"
            size="small"
            onClick={() => void handleSave()}
            disabled={isSaving}
          >
            {isSaving ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              'Save Legs'
            )}
          </Button>
        </Box>
      )}
    </Box>
  );
}
