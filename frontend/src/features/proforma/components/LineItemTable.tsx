import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableFooter,
  TextField,
  IconButton,
  Button,
  Paper,
  Typography,
} from '@mui/material';
import type { ProformaLineItem } from '../hooks';

interface LineItemTableProps {
  items: ProformaLineItem[];
  onChange: (items: ProformaLineItem[]) => void;
  readOnly?: boolean;
  currency?: string;
}

/**
 * Editable table for proforma invoice line items.
 * Auto-calculates amount (qty × rate) and total.
 */
export default function LineItemTable({
  items,
  onChange,
  readOnly = false,
  currency = 'USD',
}: LineItemTableProps) {
  const total = items.reduce((sum, item) => sum + (item.amount || 0), 0);

  function handleFieldChange(
    index: number,
    field: keyof ProformaLineItem,
    value: string,
  ) {
    const updated = [...items];
    const item = { ...updated[index] };

    if (field === 'product_name') {
      item.product_name = value;
    } else if (field === 'quantity') {
      item.quantity = parseFloat(value) || 0;
      item.amount = item.quantity * (item.rate ?? 0);
    } else if (field === 'rate') {
      item.rate = parseFloat(value) || 0;
      item.amount = (item.quantity ?? 0) * item.rate;
    }

    updated[index] = item as ProformaLineItem;
    onChange(updated);
  }

  function handleAddRow() {
    onChange([...items, { product_name: '', quantity: 0, rate: 0, amount: 0 }]);
  }

  function handleRemoveRow(index: number) {
    const updated = items.filter((_, i) => i !== index);
    onChange(updated);
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600 }}>#</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Product Name</TableCell>
            <TableCell sx={{ fontWeight: 600 }} align="right">Quantity</TableCell>
            <TableCell sx={{ fontWeight: 600 }} align="right">Rate ({currency})</TableCell>
            <TableCell sx={{ fontWeight: 600 }} align="right">Amount ({currency})</TableCell>
            {!readOnly && <TableCell sx={{ fontWeight: 600 }} align="center">Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {items.length === 0 && (
            <TableRow>
              <TableCell colSpan={readOnly ? 5 : 6} align="center">
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No line items added yet.
                </Typography>
              </TableCell>
            </TableRow>
          )}
          {items.map((item, index) => (
            <TableRow key={index}>
              <TableCell>{index + 1}</TableCell>
              <TableCell>
                {readOnly ? (
                  item.product_name
                ) : (
                  <TextField
                    size="small"
                    value={item.product_name}
                    onChange={(e) => handleFieldChange(index, 'product_name', e.target.value)}
                    placeholder="Product name"
                    fullWidth
                    variant="standard"
                  />
                )}
              </TableCell>
              <TableCell align="right">
                {readOnly ? (
                  item.quantity
                ) : (
                  <TextField
                    size="small"
                    type="number"
                    value={item.quantity || ''}
                    onChange={(e) => handleFieldChange(index, 'quantity', e.target.value)}
                    placeholder="0"
                    variant="standard"
                    slotProps={{ htmlInput: { min: 0, step: 'any', style: { textAlign: 'right' } } }}
                    sx={{ width: 100 }}
                  />
                )}
              </TableCell>
              <TableCell align="right">
                {readOnly ? (
                  item.rate.toFixed(2)
                ) : (
                  <TextField
                    size="small"
                    type="number"
                    value={item.rate || ''}
                    onChange={(e) => handleFieldChange(index, 'rate', e.target.value)}
                    placeholder="0.00"
                    variant="standard"
                    slotProps={{ htmlInput: { min: 0, step: 'any', style: { textAlign: 'right' } } }}
                    sx={{ width: 120 }}
                  />
                )}
              </TableCell>
              <TableCell align="right">
                {item.amount.toFixed(2)}
              </TableCell>
              {!readOnly && (
                <TableCell align="center">
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleRemoveRow(index)}
                    aria-label={`Remove item ${index + 1}`}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                      delete
                    </span>
                  </IconButton>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell colSpan={readOnly ? 4 : 4} align="right">
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Total
              </Typography>
            </TableCell>
            <TableCell align="right">
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {total.toFixed(2)} {currency}
              </Typography>
            </TableCell>
            {!readOnly && <TableCell />}
          </TableRow>
        </TableFooter>
      </Table>
      {!readOnly && (
        <Button
          startIcon={<span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>}
          onClick={handleAddRow}
          sx={{ m: 1 }}
          size="small"
        >
          Add Line Item
        </Button>
      )}
    </TableContainer>
  );
}
