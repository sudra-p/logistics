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
  useCommercialInvoice,
  useCreateInvoice,
  useUpdateInvoice,
  useFinalizeInvoice,
} from './hooks';
import type { CommercialInvoiceLineItem } from './hooks';

interface LineItemRow {
  product_name: string;
  quantity: string;
  rate: string;
  amount: string;
  net_weight: string;
  gross_weight: string;
  hs_code: string;
  num_packages: string;
}

const emptyLineItem: LineItemRow = {
  product_name: '',
  quantity: '0',
  rate: '0',
  amount: '0',
  net_weight: '',
  gross_weight: '',
  hs_code: '',
  num_packages: '',
};

export default function CommercialInvoicePage() {
  const { id: bookingIdParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bookingId = bookingIdParam ? parseInt(bookingIdParam, 10) : null;

  const [lineItems, setLineItems] = useState<LineItemRow[]>([{ ...emptyLineItem }]);
  const [formError, setFormError] = useState('');
  const [showFinalizeDialog, setShowFinalizeDialog] = useState(false);

  // Fetch existing invoice
  const invoiceQuery = useCommercialInvoice(bookingId);
  const invoice = invoiceQuery.data;

  // Mutations
  const createMutation = useCreateInvoice(bookingId ?? 0);
  const updateMutation = useUpdateInvoice(invoice?.id ?? 0);
  const finalizeMutation = useFinalizeInvoice(invoice?.id ?? 0);

  const isFinalized = invoice?.status === 'FINALIZED';
  const isExisting = Boolean(invoice);

  // Populate form from existing invoice
  useEffect(() => {
    if (invoice?.line_items && invoice.line_items.length > 0) {
      setLineItems(
        invoice.line_items.map((item: CommercialInvoiceLineItem) => ({
          product_name: item.product_name,
          quantity: String(item.quantity),
          rate: String(item.rate),
          amount: String(item.amount),
          net_weight: item.net_weight != null ? String(item.net_weight) : '',
          gross_weight: item.gross_weight != null ? String(item.gross_weight) : '',
          hs_code: item.hs_code || '',
          num_packages: item.num_packages != null ? String(item.num_packages) : '',
        }))
      );
    }
  }, [invoice]);

  function handleLineItemChange(index: number, field: keyof LineItemRow, value: string) {
    setLineItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value } as LineItemRow;
      // Auto-compute amount when quantity or rate change
      if (field === 'quantity' || field === 'rate') {
        const qty = parseFloat(updated[index]!.quantity) || 0;
        const rate = parseFloat(updated[index]!.rate) || 0;
        updated[index]!.amount = (qty * rate).toFixed(2);
      }
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
        rate: parseFloat(item.rate) || 0,
        amount: parseFloat(item.amount) || 0,
        net_weight: item.net_weight ? parseFloat(item.net_weight) : null,
        gross_weight: item.gross_weight ? parseFloat(item.gross_weight) : null,
        hs_code: item.hs_code,
        num_packages: item.num_packages ? parseInt(item.num_packages, 10) : null,
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
    // Create a new revision by POSTing to the booking endpoint again
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

  // Build revision history from current invoice
  const revisions: RevisionEntry[] = invoice
    ? [
        {
          revision: invoice.revision,
          status: invoice.status,
          created_at: invoice.created_at || new Date().toISOString(),
          created_by_name: undefined,
        },
      ]
    : [];

  // Loading state
  if (invoiceQuery.isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  // 404 is expected when no invoice exists yet — don't treat as error

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Commercial Invoice
          {invoice && (
            <Chip
              label={invoice.status}
              size="small"
              color={isFinalized ? 'success' : 'default'}
              sx={{ ml: 2 }}
            />
          )}
          {invoice && (
            <Typography variant="body2" component="span" sx={{ ml: 2, color: 'text.secondary' }}>
              {invoice.invoice_number} (Rev {invoice.revision})
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
                  <TableCell>Rate</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Net Weight</TableCell>
                  <TableCell>Gross Weight</TableCell>
                  <TableCell>HS Code</TableCell>
                  <TableCell>Packages</TableCell>
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
                        value={item.rate}
                        onChange={(e) => handleLineItemChange(index, 'rate', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={item.amount}
                        disabled
                        sx={{ width: 100 }}
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
                        value={item.hs_code}
                        onChange={(e) => handleLineItemChange(index, 'hs_code', e.target.value)}
                        disabled={isFinalized}
                        sx={{ width: 100 }}
                        placeholder="HS Code"
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
                  'Create Invoice'
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
        <DialogTitle>Finalize Commercial Invoice</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to finalize this commercial invoice? Once finalized, the document
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
