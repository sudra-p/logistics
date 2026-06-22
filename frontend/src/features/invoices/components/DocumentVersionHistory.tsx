import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import type { DocumentStatus } from '../hooks';

export interface RevisionEntry {
  revision: number;
  status: DocumentStatus;
  created_at: string;
  created_by_name?: string;
}

interface DocumentVersionHistoryProps {
  revisions: RevisionEntry[];
}

/**
 * Displays revision history for Commercial Invoices or Packing Lists.
 * Shows revision number, date, status, and user who created the revision.
 */
export default function DocumentVersionHistory({ revisions }: DocumentVersionHistoryProps) {
  if (!revisions || revisions.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Revision History
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Revision</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>User</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {revisions.map((rev) => (
              <TableRow key={rev.revision}>
                <TableCell>v{rev.revision}</TableCell>
                <TableCell>
                  {new Date(rev.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Chip
                    label={rev.status}
                    size="small"
                    color={rev.status === 'FINALIZED' ? 'success' : 'default'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{rev.created_by_name || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
