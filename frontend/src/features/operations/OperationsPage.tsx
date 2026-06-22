import { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  TablePagination,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Button,
  Grid,
} from '@mui/material';
import { useOperationsView } from './hooks';
import type { OperationsFilters } from './hooks';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'BOOKED', label: 'Booked' },
  { value: 'STUFFING', label: 'Stuffing' },
  { value: 'SHIPPED', label: 'Shipped' },
  { value: 'COMPLETED', label: 'Completed' },
];

type SortField = 'pi_number' | 'booking_number' | 'consignee' | 'shipping_line' | 'vessel_name' | 'etd' | 'eta' | 'pol' | 'pod';

export default function OperationsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [filters, setFilters] = useState<OperationsFilters>({});
  const [sortField, setSortField] = useState<SortField | undefined>();
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const { data, isLoading, isError, refetch } = useOperationsView({
    page: page + 1,
    pageSize,
    filters,
    sortField,
    sortDirection,
  });

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }

  function handleFilterChange(key: keyof OperationsFilters, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
    setPage(0);
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        Operations Tracking
      </Typography>

      {/* Filter Bar */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              label="Customer"
              size="small"
              fullWidth
              value={filters.customer ?? ''}
              onChange={(e) => handleFilterChange('customer', e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              label="Shipping Line"
              size="small"
              fullWidth
              value={filters.shipping_line ?? ''}
              onChange={(e) => handleFilterChange('shipping_line', e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={filters.status ?? ''}
                label="Status"
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              label="ETD From"
              type="date"
              size="small"
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
              value={filters.etd_from ?? ''}
              onChange={(e) => handleFilterChange('etd_from', e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              label="ETD To"
              type="date"
              size="small"
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
              value={filters.etd_to ?? ''}
              onChange={(e) => handleFilterChange('etd_to', e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              label="POL"
              size="small"
              fullWidth
              value={filters.pol ?? ''}
              onChange={(e) => handleFilterChange('pol', e.target.value)}
            />
          </Grid>
        </Grid>
      </Paper>

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
          Failed to load operations data. Please try again.
        </Alert>
      )}

      {/* Table */}
      {data && (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'pi_number'}
                      direction={sortField === 'pi_number' ? sortDirection : 'asc'}
                      onClick={() => handleSort('pi_number')}
                    >
                      PI No
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'booking_number'}
                      direction={sortField === 'booking_number' ? sortDirection : 'asc'}
                      onClick={() => handleSort('booking_number')}
                    >
                      Booking No
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'consignee'}
                      direction={sortField === 'consignee' ? sortDirection : 'asc'}
                      onClick={() => handleSort('consignee')}
                    >
                      Consignee
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'shipping_line'}
                      direction={sortField === 'shipping_line' ? sortDirection : 'asc'}
                      onClick={() => handleSort('shipping_line')}
                    >
                      Shipping Line
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Container Type</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'vessel_name'}
                      direction={sortField === 'vessel_name' ? sortDirection : 'asc'}
                      onClick={() => handleSort('vessel_name')}
                    >
                      Vessel
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Voyage</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'pol'}
                      direction={sortField === 'pol' ? sortDirection : 'asc'}
                      onClick={() => handleSort('pol')}
                    >
                      POL
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'pod'}
                      direction={sortField === 'pod' ? sortDirection : 'asc'}
                      onClick={() => handleSort('pod')}
                    >
                      POD
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>FPD</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'etd'}
                      direction={sortField === 'etd' ? sortDirection : 'asc'}
                      onClick={() => handleSort('etd')}
                    >
                      ETD
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortField === 'eta'}
                      direction={sortField === 'eta' ? sortDirection : 'asc'}
                      onClick={() => handleSort('eta')}
                    >
                      ETA
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Forwarder</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={13} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                        No operations records found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.results.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.pi_number}</TableCell>
                    <TableCell>{row.booking_number}</TableCell>
                    <TableCell>{row.consignee}</TableCell>
                    <TableCell>{row.shipping_line}</TableCell>
                    <TableCell>{row.container_type}</TableCell>
                    <TableCell>{row.vessel_name}</TableCell>
                    <TableCell>{row.voyage}</TableCell>
                    <TableCell>{row.pol}</TableCell>
                    <TableCell>{row.pod}</TableCell>
                    <TableCell>{row.fpd}</TableCell>
                    <TableCell>{row.etd || '—'}</TableCell>
                    <TableCell>{row.eta || '—'}</TableCell>
                    <TableCell>{row.forwarder}</TableCell>
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
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        </>
      )}
    </Box>
  );
}
