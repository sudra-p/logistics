import { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  TextField,
  Select,
  MenuItem,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  CircularProgress,
  Alert,
  Stack,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import { useAuth } from '@/auth/useAuth';
import {
  useReports,
  exportReport,
  type ReportType,
  type ExportFormat,
} from './useReports';

const PAGE_SIZE = 50;

export default function ReportsPage() {
  const { role } = useAuth();
  const [tabIndex, setTabIndex] = useState(0);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const reportType: ReportType = tabIndex === 0 ? 'pending-do' : 'master';

  const {
    data,
    isLoading,
    isError,
    page,
    setPage,
    filters,
    updateFilters,
    refetch,
  } = useReports(reportType);

  // Access restriction: only Operations and Admin
  if (role !== 'Admin' && role !== 'Operations') {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          You do not have permission to access reports.
        </Alert>
      </Box>
    );
  }

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabIndex(newValue);
  };

  const handleFilterChange = (field: string) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    updateFilters({ [field]: e.target.value });
  };

  const handleSelectChange = (field: string) => (e: SelectChangeEvent) => {
    updateFilters({ [field]: e.target.value });
  };

  const handlePageChange = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleExport = async (format: ExportFormat) => {
    setExportLoading(true);
    setExportError(null);
    try {
      await exportReport(reportType, format, filters);
    } catch {
      setExportError('Failed to export report. Please try again.');
    } finally {
      setExportLoading(false);
    }
  };

  const results = data?.results ?? [];
  const totalCount = data?.count ?? 0;

  // Derive column headers from first result row
  const columns: string[] =
    results.length > 0 ? Object.keys(results[0]!) : [];

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Reports
      </Typography>

      <Tabs value={tabIndex} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Pending DO Report" />
        <Tab label="Master Report" />
      </Tabs>

      {/* Filters */}
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        sx={{ mb: 3, flexWrap: 'wrap' }}
        useFlexGap
      >
        <TextField
          label="Client"
          size="small"
          value={filters.client}
          onChange={handleFilterChange('client')}
        />
        <TextField
          label="Vessel / Voyage"
          size="small"
          value={filters.vessel_voyage}
          onChange={handleFilterChange('vessel_voyage')}
        />
        <TextField
          label="Shipping Line"
          size="small"
          value={filters.shipping_line}
          onChange={handleFilterChange('shipping_line')}
        />
        <TextField
          label={reportType === 'pending-do' ? 'Booking Date From' : 'Created Date From'}
          type="date"
          size="small"
          value={filters.date_from}
          onChange={handleFilterChange('date_from')}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label={reportType === 'pending-do' ? 'Booking Date To' : 'Created Date To'}
          type="date"
          size="small"
          value={filters.date_to}
          onChange={handleFilterChange('date_to')}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        {reportType === 'master' && (
          <Select
            value={filters.status}
            onChange={handleSelectChange('status')}
            displayEmpty
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All Statuses</MenuItem>
            <MenuItem value="PENDING">Pending</MenuItem>
            <MenuItem value="DO_BOOKING_EDIT">DO Booking Edit</MenuItem>
            <MenuItem value="COMPLETED">Completed</MenuItem>
          </Select>
        )}
      </Stack>

      {/* Export Buttons */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => void handleExport('csv')}
          disabled={exportLoading}
        >
          Export CSV
        </Button>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => void handleExport('excel')}
          disabled={exportLoading}
        >
          Export Excel
        </Button>
        {exportLoading && <CircularProgress size={24} />}
      </Stack>

      {exportError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {exportError}
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Error State */}
      {isError && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => void refetch()}>
              Retry
            </Button>
          }
        >
          Failed to load report data.
        </Alert>
      )}

      {/* No Data State */}
      {!isLoading && !isError && results.length === 0 && (
        <Alert severity="info">No data found</Alert>
      )}

      {/* Data Table */}
      {!isLoading && !isError && results.length > 0 && (
        <Paper>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {columns.map((col) => (
                    <TableCell key={col} sx={{ fontWeight: 'bold' }}>
                      {col.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {results.map((row, idx) => (
                  <TableRow key={idx}>
                    {columns.map((col) => (
                      <TableCell key={col}>
                        {row[col] != null ? String(row[col]) : ''}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={totalCount}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={PAGE_SIZE}
            rowsPerPageOptions={[PAGE_SIZE]}
          />
        </Paper>
      )}
    </Box>
  );
}
