import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import LockIcon from '@mui/icons-material/Lock';
import EditIcon from '@mui/icons-material/Edit';
import DocumentVersionHistory from './components/DocumentVersionHistory';
import type { RevisionEntry } from './components/DocumentVersionHistory';
import {
  usePackingList,
  useCreatePackingList,
  useUpdatePackingList,
  useFinalizePackingList,
} from './hooks';
import type { PackingListLineItem } from './hooks';

interface LineItemRow {
  product_name: string;
  quantity: string;
  num_packages: string;
  net_weight: string;
  gross_weight: string;
  package_type: string;
}

const emptyLineItem: LineItemRow = {
  product_name: '',
  quantity: '0',
  num_packages: '0',
  net_weight: '0',
  gross_weight: '0',
  package_type: '',
};

export default function PackingListPage() {
  const { id: bookingIdParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bookingId = bookingIdParam ? parseInt(bookingIdParam, 10) : null;

  const [lineItems, setLineItems] = useState<LineItemRow[]>([{ ...emptyLineItem }]);
  const [formError, setFormError] = useState('');
  const [showFinalizeDialog, setShowFinalizeDialog] = useState(false);

  // Fetch existing packing list
  const packingListQuery = usePackingList(bookingId);
  const packingList = packingListQuery.data;

  // Mutations
  const createMutation = useCreatePackingList(bookingId ?? 0);
  const updateMutation = useUpdatePackingList(packingList?.id ?? 0);
  const finalizeMutation = useFinalizePackingList(packingList?.id ?? 0);

  const isFinalized = packingList?.status === 'FINALIZED';
  const isExisting = Boolean(packingList);

  // Populate form from existing packing list
  useEffect(() => {
    if (packingList?.line_items && packingList.line_items.length > 0) {
      setLineItems(
        packingList.line_items.map((item: PackingListLineItem) => ({
          product_name: item.product_name,
          quantity: String(item.quantity),
          num_packages: String(item.num_packages),
          net_weight: String(item.net_weight),
          gross_weight: String(item.gross_weight),
          package_type: item.package_type || '',
        }))
      );
    }
  }, [packingList]);

  function handleLineItemChange(index: number, field: keyof LineItemRow, value: string) {
    setLineItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value } as LineItemRow;
      return updated;
    });
  }

  function addLineItem() {
    setLineItems((prev) => [...prev, { ...emptyLineItem }]);
  }

  function removeLineItem(index: number) {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  }

  function buildPayload() {
    return {
      line_items: lineItems.map((item) => ({
        product_name: item.product_name,
        quantity: parseFloat(item.quantity) || 0,
        num_packages: parseInt(item.num_packages, 10) || 0,
        net_weight: parseFloat(item.net_weight) || 0,
        gross_weight: parseFloat(item.gross_weight) || 0,
        package_type: item.package_type,
      })),
    };
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (lineItems.length === 0 || !lineItems.some((i) => i.product_name.trim())) {
      setFormError('At least one line item with a product name is required.');
      return;
    }

    const payload = buildPayload();
    const mutation = isExisting ? updateMutation : createMutation;

    mutation.mutate(payload, {
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

  function handleFinalize() {
    setShowFinalizeDialog(false);
    finalizeMutation.mutate(undefined, {
      onError: (error: unknown) => {
        const axiosErr = error as { response?: { data?: Record<string, string[]> } };
        if (axiosErr.response?.data) {
          const messages = Object.entries(axiosErr.response.data)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('; ');
          setFormError(messages || 'An error occurred during finalization.');
        } else {
          setFormError('An unexpected error occurred. Please try again.');
        }
      },
    });
  }

  function handleCreateRevision() {
    const payload = buildPayload();
    createMutation.mutate(payload, {
      onError: (error: unknown) => {
        const axiosErr = error as { response?: { data?: Record<string, string[]> } };
        if (axiosErr.response?.data) {
          const messages = Object.entries(axiosErr.response.data)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('; ');
          setFormError(messages || 'An error occurred creating revision.');
        } else {
          setFormError('An unexpected error occurred. Please try again.');
        }
      },
    });
  }

  const isPending =
    createMutation.isPending || updateMutation.isPending || finalizeMutation.isPending;

  // Build revision history
  const revisions: RevisionEntry[] = packingList
    ? [
        {
          revision: packingList.revision,
          status: packingList.status,
          created_at: packingList.created_at || new Date().toISOString(),
          created_by_name: undefined,
        },
      ]
    : [];

  // Loading state
  if (packingListQuery.isLoading) {
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
          Packing List
          {packingList && (
            <Chip
              label={packingList.status}
              size="small"
              color={isFinalized ? 'success' : 'default'}
              sx={{ ml: 2 }}
            />
          )}
          {packingList && (
            <Typography variant="body2" component="span" sx={{ ml: 2, color: 'text.secondary' }}>
              {packingList.packing_list_number} (Rev {packingList.revision})
            </Typography>
          )}
        </Typography>
        <Button variant="outlined" onClick={() => navigate(`/bookings/${bookingId}`)}>
          Back to Booking
        </Button>
      </Box>

      {formError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {formError}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSave} noValidate>
          {/* Line Items Table */}
          <Typography variant="h6" sx={{ mb: 2 }}>
            Line Items
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Product</TableCell>
                  <TableCell>Qty</TableCell>
                  <TableCell>Packages</TableCell>
                  <TableCell>Net Weight</TableCell>
                  <TableCell>Gross Weight</TableCell>
                  <TableCell>Package Type</TableCell>
                  {!isFinalized && <TableCell>Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {lineItems.map((item, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <TextField
                        size="small"
                        value={item.product_name}
                        onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                        disabled={isFinalized}
                        placeholder="Product name"
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={item.quantity}
                        onChange={(e) => handleLineItemChange(index, 'quantity', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={item.num_packages}
                        onChange={(e) => handleLineItemChange(index, 'num_packages', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={item.net_weight}
                        onChange={(e) => handleLineItemChange(index, 'net_weight', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 90 }}
                        placeholder="kg"
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={item.gross_weight}
                        onChange={(e) => handleLineItemChange(index, 'gross_weight', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 90 }}
                        placeholder="kg"
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={item.package_type}
                        onChange={(e) => handleLineItemChange(index, 'package_type', e.target.value)}
                        disabled={isFinalized}
                        placeholder="e.g., Carton"
                        sx={{ width: 120 }}
                      />
                    </TableCell>
                    {!isFinalized && (
                      <TableCell>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => removeLineItem(index)}
                          disabled={lineItems.length <= 1}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {!isFinalized && (
            <Button
              startIcon={<AddIcon />}
              onClick={addLineItem}
              sx={{ mt: 1 }}
              size="small"
            >
              Add Line Item
            </Button>
          )}

          {/* Action Buttons */}
          <Box sx={{ mt: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {!isFinalized && (
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
                  'Create Packing List'
                )}
              </Button>
            )}

            {isExisting && !isFinalized && (
              <Button
                variant="contained"
                color="warning"
                size="large"
                startIcon={<LockIcon />}
                onClick={() => setShowFinalizeDialog(true)}
                disabled={isPending}
              >
                Finalize
              </Button>
            )}

            {isFinalized && (
              <Button
                variant="contained"
                color="primary"
                size="large"
                startIcon={<EditIcon />}
                onClick={handleCreateRevision}
                disabled={isPending}
              >
                Create Revision
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Revision History */}
      <DocumentVersionHistory revisions={revisions} />

      {/* Finalize Confirmation Dialog */}
      <Dialog open={showFinalizeDialog} onClose={() => setShowFinalizeDialog(false)}>
        <DialogTitle>Finalize Packing List</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to finalize this packing list? Once finalized, the document
            cannot be edited. You will need to create a new revision to make changes.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowFinalizeDialog(false)}>Cancel</Button>
          <Button onClick={handleFinalize} color="warning" variant="contained">
            Finalize
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
