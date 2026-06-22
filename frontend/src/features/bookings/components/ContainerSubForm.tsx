import { useState } from 'react';
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
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { containerSchema } from '../schema';
import type { ContainerFormValues } from '../schema';
import { useContainers } from '../useContainers';
import type { ContainerFieldErrors } from '../useContainers';

const CONTAINER_SIZES = ['20FT', '40FT', '40FT_HC', '45FT'] as const;

const MAX_CONTAINERS = 50;

interface MasterDataOption {
  id: number;
  name: string;
}

interface ContainerSubFormProps {
  bookingId: number | null;
}

/**
 * Repeatable container entry section within the booking form.
 * Supports adding up to 50 containers, displaying existing ones,
 * and removing individual entries.
 */
export default function ContainerSubForm({ bookingId }: ContainerSubFormProps) {
  const {
    containers,
    isLoading,
    isError,
    createMutation,
    deleteMutation,
    extractFieldErrors,
  } = useContainers(bookingId);

  const [apiErrors, setApiErrors] = useState<ContainerFieldErrors>({});
  const [limitError, setLimitError] = useState<string | null>(null);

  // ─── Load container types from master data ────────────────────────────────
  const containerTypesQuery = useQuery<MasterDataOption[]>({
    queryKey: ['master-data', 'container-types', 'active'],
    queryFn: async () => {
      const response = await apiClient.get(
        ENDPOINTS.MASTER_DATA('container-types'),
        { params: { is_active: true, page_size: 1000 } },
      );
      const data = response.data;
      const results = Array.isArray(data) ? data : data.results ?? [];
      return results.map((item: { id: number; name: string }) => ({
        id: item.id,
        name: item.name,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });

  // ─── Form for adding a new container entry ────────────────────────────────
  const form = useForm<ContainerFormValues>({
    resolver: zodResolver(containerSchema),
    defaultValues: {
      container_type: undefined as unknown as number,
      container_size: '20FT',
      container_count: 1,
      container_no: '',
      seal_no: '',
    },
    mode: 'onBlur',
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = form;

  const canAddMore = containers.length < MAX_CONTAINERS;

  const onAdd = handleSubmit((data) => {
    if (!bookingId) return;

    setApiErrors({});
    setLimitError(null);

    if (containers.length >= MAX_CONTAINERS) {
      setLimitError(`Maximum of ${MAX_CONTAINERS} container entries reached.`);
      return;
    }

    createMutation.mutate(data, {
      onSuccess: () => {
        reset();
        setApiErrors({});
      },
      onError: (error) => {
        const fieldErrs = extractFieldErrors(error);
        // Check if it's a limit error from the API
        if (error.response?.status === 400) {
          const responseData = error.response.data;
          if (
            responseData &&
            typeof responseData === 'object' &&
            'non_field_errors' in responseData
          ) {
            const nonFieldErrors = (responseData as Record<string, string[]>)['non_field_errors'];
            if (nonFieldErrors && nonFieldErrors.length > 0) {
              setLimitError(nonFieldErrors[0]!);
              return;
            }
          }
          if (
            responseData &&
            typeof responseData === 'object' &&
            'detail' in responseData
          ) {
            setLimitError((responseData as unknown as { detail: string }).detail);
            return;
          }
        }
        setApiErrors(fieldErrs);
      },
    });
  });

  const handleDelete = (containerId: number) => {
    setLimitError(null);
    deleteMutation.mutate(containerId);
  };

  // Merge client-side and server-side errors for display
  const getFieldError = (field: keyof ContainerFormValues): string | undefined => {
    return errors[field]?.message ?? apiErrors[field];
  };

  if (!bookingId) {
    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Containers
        </Typography>
        <Alert severity="info">
          Save the booking first to add container entries.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Containers
      </Typography>

      {/* ─── Existing containers table ──────────────────────────────────── */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load existing containers.
        </Alert>
      )}

      {!isLoading && containers.length > 0 && (
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Count</TableCell>
                <TableCell>Container No.</TableCell>
                <TableCell>Seal No.</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {containers.map((container) => {
                const typeName =
                  containerTypesQuery.data?.find(
                    (t) => t.id === container.container_type,
                  )?.name ?? `Type #${container.container_type}`;

                return (
                  <TableRow key={container.id}>
                    <TableCell>{typeName}</TableCell>
                    <TableCell>{container.container_size}</TableCell>
                    <TableCell>{container.container_count}</TableCell>
                    <TableCell>{container.container_no || '—'}</TableCell>
                    <TableCell>{container.seal_no || '—'}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDelete(container.id)}
                        disabled={deleteMutation.isPending}
                        aria-label={`Delete container ${container.container_no || container.id}`}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {!isLoading && containers.length === 0 && !isError && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No containers added yet.
        </Alert>
      )}

      {/* ─── Add container form ─────────────────────────────────────────── */}
      {limitError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {limitError}
        </Alert>
      )}

      {canAddMore && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Add Container
          </Typography>
          <Grid container spacing={2} sx={{ alignItems: 'flex-start' }}>
            {/* Container Type */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl
                fullWidth
                size="small"
                error={!!getFieldError('container_type')}
                disabled={containerTypesQuery.isError}
              >
                <InputLabel id="container-type-label">Type *</InputLabel>
                <Controller
                  name="container_type"
                  control={control}
                  render={({ field }) => (
                    <Select
                      labelId="container-type-label"
                      label="Type *"
                      value={field.value ?? ''}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      onBlur={field.onBlur}
                    >
                      {containerTypesQuery.isLoading && (
                        <MenuItem disabled value="">
                          Loading...
                        </MenuItem>
                      )}
                      {containerTypesQuery.data?.map((option) => (
                        <MenuItem key={option.id} value={option.id}>
                          {option.name}
                        </MenuItem>
                      ))}
                    </Select>
                  )}
                />
                {getFieldError('container_type') && (
                  <FormHelperText>
                    {getFieldError('container_type')}
                  </FormHelperText>
                )}
                {containerTypesQuery.isError && (
                  <FormHelperText>Failed to load container types</FormHelperText>
                )}
              </FormControl>
            </Grid>

            {/* Container Size */}
            <Grid size={{ xs: 12, sm: 6, md: 2 }}>
              <FormControl
                fullWidth
                size="small"
                error={!!getFieldError('container_size')}
              >
                <InputLabel id="container-size-label">Size *</InputLabel>
                <Controller
                  name="container_size"
                  control={control}
                  render={({ field }) => (
                    <Select
                      labelId="container-size-label"
                      label="Size *"
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                    >
                      {CONTAINER_SIZES.map((size) => (
                        <MenuItem key={size} value={size}>
                          {size}
                        </MenuItem>
                      ))}
                    </Select>
                  )}
                />
                {getFieldError('container_size') && (
                  <FormHelperText>
                    {getFieldError('container_size')}
                  </FormHelperText>
                )}
              </FormControl>
            </Grid>

            {/* Container Count */}
            <Grid size={{ xs: 12, sm: 4, md: 2 }}>
              <TextField
                {...register('container_count', { valueAsNumber: true })}
                label="Count *"
                type="number"
                size="small"
                fullWidth
                slotProps={{ htmlInput: { min: 1 } }}
                error={!!getFieldError('container_count')}
                helperText={getFieldError('container_count')}
              />
            </Grid>

            {/* Container No. */}
            <Grid size={{ xs: 12, sm: 4, md: 2 }}>
              <TextField
                {...register('container_no')}
                label="Container No."
                size="small"
                fullWidth
                slotProps={{ htmlInput: { maxLength: 20 } }}
                error={!!getFieldError('container_no')}
                helperText={getFieldError('container_no')}
              />
            </Grid>

            {/* Seal No. */}
            <Grid size={{ xs: 12, sm: 4, md: 2 }}>
              <TextField
                {...register('seal_no')}
                label="Seal No."
                size="small"
                fullWidth
                slotProps={{ htmlInput: { maxLength: 20 } }}
                error={!!getFieldError('seal_no')}
                helperText={getFieldError('seal_no')}
              />
            </Grid>

            {/* Add Button */}
            <Grid size={{ xs: 12, md: 1 }} sx={{ display: 'flex', alignItems: 'center' }}>
              <Button
                variant="contained"
                size="small"
                onClick={onAdd}
                disabled={createMutation.isPending}
                startIcon={
                  createMutation.isPending ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <AddIcon />
                  )
                }
                aria-label="Add container"
              >
                Add
              </Button>
            </Grid>
          </Grid>
        </Paper>
      )}

      {!canAddMore && (
        <Alert severity="info">
          Maximum of {MAX_CONTAINERS} container entries reached.
        </Alert>
      )}
    </Box>
  );
}
