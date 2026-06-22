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
  CircularProgress,
  Alert,
  IconButton,
} from '@mui/material';
import StockLevelIndicator from './components/StockLevelIndicator';
import { useStockList } from './hooks';

export default function StockListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  const { data, isLoading, isError, refetch } = useStockList({
    page: page + 1,
    pageSize,
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Inventory / Stock
        </Typography>
        <Button
          variant="contained"
          startIcon={<span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>}
          onClick={() => navigate('/inventory/new')}
        >
          New Stock Item
        </Button>
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
          Failed to load stock items. Please try again.
        </Alert>
      )}

      {/* Table */}
      {data && (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Product Name</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Available Stock</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Reserved Stock</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Shipped Stock</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Unit</TableCell>
                  <TableCell sx={{ fontWeight: 600, minWidth: 120 }}>Level</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                        No stock items found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.results.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>{item.product_name}</TableCell>
                    <TableCell align="right">{item.available_stock}</TableCell>
                    <TableCell align="right">{item.reserved_stock}</TableCell>
                    <TableCell align="right">{item.shipped_stock}</TableCell>
                    <TableCell>{item.unit}</TableCell>
                    <TableCell>
                      <StockLevelIndicator
                        availableStock={item.available_stock}
                        reservedStock={item.reserved_stock}
                        shippedStock={item.shipped_stock}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        onClick={() => navigate(`/inventory/${item.id}/edit`)}
                        aria-label={`Edit ${item.product_name}`}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                          edit
                        </span>
                      </IconButton>
                    </TableCell>
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
