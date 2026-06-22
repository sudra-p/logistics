import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import InventoryIcon from '@mui/icons-material/Inventory';
import SailingIcon from '@mui/icons-material/Sailing';
import WarningIcon from '@mui/icons-material/Warning';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useBLForBooking } from '@/features/bl/hooks';
import { usePerformStuffing } from './stuffingHooks';
import { useMutation } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { StuffingProduct } from './stuffingHooks';

interface ContainerInfo {
  id: number;
  container_number: string;
  stuffing_status: 'PENDING' | 'STUFFED';
  stuffed_at: string | null;
}

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bookingId = id ? parseInt(id, 10) : null;

  // BL query for alert banner
  const blQuery = useBLForBooking(bookingId);
  const bl = blQuery.data;
  const blMissing = blQuery.isError || !bl;
  const blPending = bl?.status === 'DRAFT' || bl?.status === 'SUBMITTED';

  // Stuffing state
  const [stuffingDialogOpen, setStuffingDialogOpen] = useState(false);
  const [selectedContainer, setSelectedContainer] = useState<ContainerInfo | null>(null);
  const [stuffingProducts, setStuffingProducts] = useState<StuffingProduct[]>([
    { product_name: '', quantity: 0 },
  ]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete(ENDPOINTS.BOOKING_DETAIL(bookingId!)),
    onSuccess: () => { navigate('/search'); },
  });

  const stuffingMutation = usePerformStuffing(
    bookingId ?? 0,
    selectedContainer?.id ?? 0
  );

  // Mock containers replaced by real data from API above

  function openStuffingDialog(container: ContainerInfo) {
    setSelectedContainer(container);
    setStuffingProducts([{ product_name: '', quantity: 0 }]);
    setStuffingDialogOpen(true);
  }

  function handleStuffingProductChange(index: number, field: keyof StuffingProduct, value: string) {
    setStuffingProducts((prev) => {
      const updated = [...prev];
      if (field === 'quantity') {
        updated[index] = { ...updated[index], quantity: parseInt(value, 10) || 0 } as StuffingProduct;
      } else {
        updated[index] = { ...updated[index], [field]: value } as StuffingProduct;
      }
      return updated;
    });
  }

  function addStuffingProduct() {
    setStuffingProducts((prev) => [...prev, { product_name: '', quantity: 0 }]);
  }

  // Status change
  const [newStatus, setNewStatus] = useState('');
  const statusChangeMutation = useMutation({
    mutationFn: (statusValue: string) =>
      apiClient.patch(`bookings/${bookingId}/status/`, { status: statusValue }),
    onSuccess: () => {
      setNewStatus('');
      window.location.reload();
    },
  });

  // Containers
  const [containersList, setContainersList] = useState<ContainerInfo[]>([]);
  const [showAddContainer, setShowAddContainer] = useState(false);
  const [newContainerNo, setNewContainerNo] = useState('');
  const [newSealNo, setNewSealNo] = useState('');
  const [newContainerSize, setNewContainerSize] = useState('20FT');
  const [newContainerType, setNewContainerType] = useState<number | ''>('');
  const [containerTypes, setContainerTypes] = useState<{ id: number; name: string }[]>([]);

  // Fetch containers and container types
  useEffect(() => {
    if (bookingId) {
      apiClient.get(`bookings/${bookingId}/containers/`).then((res) => {
        const data = res.data?.results ?? res.data ?? [];
        setContainersList(data);
      }).catch(() => {});
    }
    apiClient.get('master-data/container-types/').then((res) => {
      const data = res.data?.results ?? res.data ?? [];
      setContainerTypes(data);
      if (data.length > 0) setNewContainerType(data[0].id);
    }).catch(() => {});
  }, [bookingId]);

  const addContainerMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`bookings/${bookingId}/containers/`, {
        container_type: newContainerType,
        container_size: newContainerSize,
        container_count: 1,
        container_no: newContainerNo,
        seal_no: newSealNo,
      }),
    onSuccess: () => {
      setNewContainerNo('');
      setNewSealNo('');
      setShowAddContainer(false);
      // Refresh containers
      apiClient.get(`bookings/${bookingId}/containers/`).then((res) => {
        const data = res.data?.results ?? res.data ?? [];
        setContainersList(data);
      }).catch(() => {});
    },
  });

  function handleConfirmStuffing() {
    setConfirmDialogOpen(false);
    stuffingMutation.mutate(
      { products: stuffingProducts.filter((p) => p.product_name && p.quantity > 0) },
      {
        onSuccess: () => {
          setStuffingDialogOpen(false);
        },
      }
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Booking Detail
        </Typography>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={() => setDeleteDialogOpen(true)}
        >
          Delete Booking
        </Button>
      </Box>

      {/* Status Change Section */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="subtitle2" color="text.secondary">
          Change Status:
        </Typography>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Next Status</InputLabel>
          <Select
            value={newStatus}
            label="Next Status"
            onChange={(e) => setNewStatus(e.target.value)}
          >
            <MenuItem value="BOOKED">Booked</MenuItem>
            <MenuItem value="STUFFING">Stuffing</MenuItem>
            <MenuItem value="SHIPPED">Shipped</MenuItem>
            <MenuItem value="COMPLETED">Completed</MenuItem>
          </Select>
        </FormControl>
        <Button
          variant="contained"
          size="small"
          disabled={!newStatus || statusChangeMutation.isPending}
          onClick={() => statusChangeMutation.mutate(newStatus)}
        >
          {statusChangeMutation.isPending ? <CircularProgress size={18} /> : 'Update Status'}
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
          Flow: Pending → Booked → Stuffing → Shipped → Completed
        </Typography>
        {statusChangeMutation.isError && (
          <Alert severity="error" sx={{ py: 0, flex: '1 0 100%' }}>
            {(() => {
              const err = statusChangeMutation.error as { response?: { data?: Record<string, string | string[]> } };
              const data = err?.response?.data;
              if (data?.status) return Array.isArray(data.status) ? data.status.join(', ') : data.status;
              return 'Failed to change status. Check the allowed transitions.';
            })()}
          </Alert>
        )}
      </Paper>

      {/* BL Alert Banner */}
      {blMissing && !blQuery.isLoading && (
        <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 3 }}>
          Bill of Lading is missing for this booking.{' '}
          <Button
            size="small"
            variant="text"
            onClick={() => navigate(`/bookings/${bookingId}/bl/new`)}
          >
            Create BL
          </Button>
        </Alert>
      )}
      {blPending && bl && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Bill of Lading ({bl.bl_number}) is in <strong>{bl.status}</strong> status.{' '}
          <Button
            size="small"
            variant="text"
            onClick={() => navigate(`/bookings/${bookingId}/bl`)}
          >
            View BL
          </Button>
        </Alert>
      )}

      {/* Documents Section */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Documents
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <List>
          <ListItem
            component="div"
            sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' }, borderRadius: 1 }}
            onClick={() => navigate(`/bookings/${bookingId}/commercial-invoice`)}
          >
            <ListItemIcon>
              <DescriptionIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="Commercial Invoice"
              secondary="Generate or view the formal trade invoice for this booking"
            />
            <Button variant="outlined" size="small">
              Open
            </Button>
          </ListItem>

          <ListItem
            component="div"
            sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' }, borderRadius: 1 }}
            onClick={() => navigate(`/bookings/${bookingId}/packing-list`)}
          >
            <ListItemIcon>
              <InventoryIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="Packing List"
              secondary="Generate or view the packing list for this booking"
            />
            <Button variant="outlined" size="small">
              Open
            </Button>
          </ListItem>

          <ListItem
            component="div"
            sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' }, borderRadius: 1 }}
            onClick={() => navigate(`/bookings/${bookingId}/bl`)}
          >
            <ListItemIcon>
              <SailingIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="Bill of Lading"
              secondary="Manage the Bill of Lading for this booking"
            />
            <Button variant="outlined" size="small">
              Open
            </Button>
          </ListItem>
        </List>
      </Paper>

      {/* Container Stuffing Section */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Containers
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setShowAddContainer(!showAddContainer)}
          >
            Add Container
          </Button>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {showAddContainer && (
          <Box sx={{ mb: 3, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>New Container</Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <TextField
                size="small"
                label="Container No"
                value={newContainerNo}
                onChange={(e) => setNewContainerNo(e.target.value)}
                placeholder="e.g. MSCU1234567"
              />
              <TextField
                size="small"
                label="Seal No"
                value={newSealNo}
                onChange={(e) => setNewSealNo(e.target.value)}
                placeholder="e.g. SL123"
              />
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Container Type</InputLabel>
                <Select
                  value={newContainerType}
                  label="Container Type"
                  onChange={(e) => setNewContainerType(e.target.value as number)}
                >
                  {containerTypes.map((ct) => (
                    <MenuItem key={ct.id} value={ct.id}>{ct.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Size</InputLabel>
                <Select
                  value={newContainerSize}
                  label="Size"
                  onChange={(e) => setNewContainerSize(e.target.value)}
                >
                  <MenuItem value="20FT">20FT</MenuItem>
                  <MenuItem value="40FT">40FT</MenuItem>
                  <MenuItem value="40FT_HC">40FT HC</MenuItem>
                  <MenuItem value="45FT">45FT</MenuItem>
                </Select>
              </FormControl>
              <Button
                variant="contained"
                size="small"
                onClick={() => addContainerMutation.mutate()}
                disabled={addContainerMutation.isPending || !newContainerType}
              >
                {addContainerMutation.isPending ? <CircularProgress size={18} /> : 'Add'}
              </Button>
            </Box>
            {addContainerMutation.isError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Failed to add container. Ensure container type exists in Master Data.
              </Alert>
            )}
          </Box>
        )}

        {containersList.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No containers added yet. Click "Add Container" above to add one.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Container #</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Size</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Seal #</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Stuffing Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Stuffed At</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {containersList.map((container) => (
                  <TableRow key={container.id}>
                    <TableCell>{container.container_number || '—'}</TableCell>
                    <TableCell>{(container as unknown as Record<string, string>).container_size || '—'}</TableCell>
                    <TableCell>{(container as unknown as Record<string, string>).seal_no || '—'}</TableCell>
                    <TableCell>
                      <Chip
                        label={container.stuffing_status}
                        size="small"
                        color={container.stuffing_status === 'STUFFED' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell>
                      {container.stuffed_at
                        ? new Date(container.stuffed_at).toLocaleString()
                        : '—'}
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                        <Button
                          variant="contained"
                          size="small"
                          disabled={container.stuffing_status === 'STUFFED'}
                          onClick={() => openStuffingDialog(container)}
                        >
                          Mark as Stuffed
                        </Button>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => {
                            apiClient.delete(`bookings/${bookingId}/containers/${container.id}/`).then(() => {
                              setContainersList((prev) => prev.filter((c) => c.id !== container.id));
                            }).catch(() => {});
                          }}
                          aria-label="Delete container"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Stuffing Dialog */}
      <Dialog
        open={stuffingDialogOpen}
        onClose={() => setStuffingDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Stuff Container: {selectedContainer?.container_number}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter the product quantities to load into this container.
          </Typography>
          {stuffingProducts.map((product, index) => (
            <Box key={index} sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Product Name"
                size="small"
                value={product.product_name}
                onChange={(e) => handleStuffingProductChange(index, 'product_name', e.target.value)}
                fullWidth
              />
              <TextField
                label="Quantity"
                type="number"
                size="small"
                value={product.quantity || ''}
                onChange={(e) => handleStuffingProductChange(index, 'quantity', e.target.value)}
                sx={{ width: 120 }}
              />
            </Box>
          ))}
          <Button size="small" onClick={addStuffingProduct}>
            + Add Product
          </Button>
          {stuffingMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Failed to perform stuffing. Check available stock and try again.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStuffingDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            onClick={() => setConfirmDialogOpen(true)}
            disabled={stuffingMutation.isPending || !stuffingProducts.some((p) => p.product_name && p.quantity > 0)}
          >
            {stuffingMutation.isPending ? <CircularProgress size={20} /> : 'Perform Stuffing'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Stuffing Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>Confirm Stuffing Action</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This action is irreversible. Stock will be deducted from available inventory for the
            specified products. Are you sure you want to proceed?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleConfirmStuffing}>
            Confirm Stuffing
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Booking Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Booking</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this booking? This action cannot be undone.
            All associated documents (BL, invoices, packing lists) will also be removed.
          </DialogContentText>
          {deleteMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Failed to delete booking. It may have dependencies that prevent deletion.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
