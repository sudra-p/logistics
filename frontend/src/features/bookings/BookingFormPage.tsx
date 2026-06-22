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
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  Paper,
  Divider,
} from '@mui/material';
import { Controller } from 'react-hook-form';
import { useBookingForm } from './useBookingForm';
import type { DropdownState } from './useBookingForm';
import type { BookingFormValues } from './schema';

/** Renders an asterisk indicator for required fields. */
function RequiredLabel({ children }: { children: string }) {
  return (
    <>
      {children} <span aria-hidden="true">*</span>
    </>
  );
}

/** Section header for form organization. */
function SectionHeader({ title }: { title: string }) {
  return (
    <>
      <Divider sx={{ my: 3 }} />
      <Typography variant="h6" sx={{ mb: 2 }}>
        {title}
      </Typography>
    </>
  );
}

/** Renders a dropdown field backed by master data. */
function MasterDataSelect({
  name,
  label,
  required,
  control,
  errors,
  dropdown,
}: {
  name: keyof BookingFormValues;
  label: string;
  required?: boolean;
  control: ReturnType<typeof useBookingForm>['form']['control'];
  errors: ReturnType<typeof useBookingForm>['form']['formState']['errors'];
  dropdown: DropdownState;
}) {
  const fieldError = errors[name];
  const hasError = !!fieldError || dropdown.isError;
  const helperText = fieldError?.message ?? dropdown.errorMessage ?? '';

  return (
    <FormControl fullWidth error={hasError} disabled={dropdown.isError}>
      <InputLabel id={`${name}-label`}>
        {required ? <RequiredLabel>{label}</RequiredLabel> : label}
      </InputLabel>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <Select
            labelId={`${name}-label`}
            label={required ? `${label} *` : label}
            value={field.value ?? ''}
            onChange={(e) => field.onChange(Number(e.target.value))}
            onBlur={field.onBlur}
          >
            {dropdown.isLoading && (
              <MenuItem disabled value="">
                Loading...
              </MenuItem>
            )}
            {dropdown.options.map((option) => (
              <MenuItem key={option.id} value={option.id}>
                {option.name}
              </MenuItem>
            ))}
          </Select>
        )}
      />
      {hasError && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
}

export default function BookingFormPage() {
  const {
    form,
    isEditMode,
    bookingQuery,
    dropdowns,
    submitMutation,
    onSubmit,
  } = useBookingForm();

  const {
    register,
    control,
    watch,
    formState: { errors },
  } = form;

  const isHaz = watch('is_haz');

  // ─── Edit mode: loading / error states ─────────────────────────────────────
  if (isEditMode && bookingQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isEditMode && bookingQuery.isError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => void bookingQuery.refetch()}
            >
              Retry
            </Button>
          }
        >
          Failed to load booking data. Please try again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {isEditMode ? 'Edit Booking' : 'New Booking'}
      </Typography>

      {submitMutation.isError && !submitMutation.error?.response?.data && (
        <Alert severity="error" sx={{ mb: 2 }}>
          An unexpected error occurred. Please try again.
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={onSubmit} noValidate>
          {/* ─── Mandatory Fields ─────────────────────────────────────────── */}
          <Typography variant="h6" sx={{ mb: 2 }}>
            Booking Details
          </Typography>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                {...register('booking_date')}
                label={<RequiredLabel>Booking Date</RequiredLabel>}
                type="date"
                fullWidth
                slotProps={{ inputLabel: { shrink: true } }}
                error={!!errors.booking_date}
                helperText={errors.booking_date?.message}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                {...register('booking_validity_date')}
                label={<RequiredLabel>Validity Date</RequiredLabel>}
                type="date"
                fullWidth
                slotProps={{ inputLabel: { shrink: true } }}
                error={!!errors.booking_validity_date}
                helperText={errors.booking_validity_date?.message}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                {...register('forwarding_window_start')}
                label={<RequiredLabel>Forwarding Start</RequiredLabel>}
                type="date"
                fullWidth
                slotProps={{ inputLabel: { shrink: true } }}
                error={!!errors.forwarding_window_start}
                helperText={errors.forwarding_window_start?.message}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                {...register('forwarding_window_end')}
                label={<RequiredLabel>Forwarding End</RequiredLabel>}
                type="date"
                fullWidth
                slotProps={{ inputLabel: { shrink: true } }}
                error={!!errors.forwarding_window_end}
                helperText={errors.forwarding_window_end?.message}
              />
            </Grid>

            {/* Foreign-key dropdowns */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <MasterDataSelect
                name="shipping_line"
                label="Shipping Line"
                required
                control={control}
                errors={errors}
                dropdown={dropdowns.shipping_line!}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <MasterDataSelect
                name="pol"
                label="Port of Loading"
                required
                control={control}
                errors={errors}
                dropdown={dropdowns.pol!}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <MasterDataSelect
                name="pod"
                label="Port of Discharge"
                required
                control={control}
                errors={errors}
                dropdown={dropdowns.pod!}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <MasterDataSelect
                name="client"
                label="Client"
                required
                control={control}
                errors={errors}
                dropdown={dropdowns.client!}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <MasterDataSelect
                name="commodity"
                label="Commodity"
                required
                control={control}
                errors={errors}
                dropdown={dropdowns.commodity!}
              />
            </Grid>

            {/* Cargo & Shipment type */}
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <FormControl fullWidth error={!!errors.cargo_type}>
                <InputLabel id="cargo-type-label">
                  <RequiredLabel>Cargo Type</RequiredLabel>
                </InputLabel>
                <Controller
                  name="cargo_type"
                  control={control}
                  render={({ field }) => (
                    <Select
                      labelId="cargo-type-label"
                      label="Cargo Type *"
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                    >
                      <MenuItem value="FCL">FCL</MenuItem>
                      <MenuItem value="LCL">LCL</MenuItem>
                    </Select>
                  )}
                />
                {errors.cargo_type && (
                  <FormHelperText>{errors.cargo_type.message}</FormHelperText>
                )}
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <TextField
                {...register('shipment_type')}
                label={<RequiredLabel>Shipment Type</RequiredLabel>}
                fullWidth
                error={!!errors.shipment_type}
                helperText={errors.shipment_type?.message}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <TextField
                {...register('stuffing_type')}
                label={<RequiredLabel>Stuffing Type</RequiredLabel>}
                fullWidth
                error={!!errors.stuffing_type}
                helperText={errors.stuffing_type?.message}
              />
            </Grid>
          </Grid>

          {/* ─── HAZ Details Section ──────────────────────────────────────── */}
          <SectionHeader title="HAZ Details" />

          <Grid container spacing={2}>
            <Grid size={{ xs: 12 }}>
              <Controller
                name="is_haz"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Switch
                        checked={field.value}
                        onChange={(e) => field.onChange(e.target.checked)}
                      />
                    }
                    label="Hazardous Cargo"
                  />
                )}
              />
            </Grid>

            {isHaz && (
              <>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <TextField
                    {...register('haz_class')}
                    label={<RequiredLabel>HAZ Class</RequiredLabel>}
                    fullWidth
                    error={!!errors.haz_class}
                    helperText={errors.haz_class?.message}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <TextField
                    {...register('haz_uin')}
                    label={<RequiredLabel>HAZ UIN</RequiredLabel>}
                    fullWidth
                    error={!!errors.haz_uin}
                    helperText={errors.haz_uin?.message}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <TextField
                    {...register('haz_group')}
                    label={<RequiredLabel>HAZ Group</RequiredLabel>}
                    fullWidth
                    error={!!errors.haz_group}
                    helperText={errors.haz_group?.message}
                  />
                </Grid>
              </>
            )}
          </Grid>

          {/* ─── Submit ───────────────────────────────────────────────────── */}
          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitMutation.isPending}
            >
              {submitMutation.isPending ? (
                <CircularProgress size={24} color="inherit" />
              ) : isEditMode ? (
                'Update Booking'
              ) : (
                'Create Booking'
              )}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
