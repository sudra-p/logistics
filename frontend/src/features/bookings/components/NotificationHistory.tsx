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
  Alert,
} from '@mui/material';

export interface CommunicationLog {
  id: number;
  email_type: string;
  recipients: string[];
  sent_at: string | null;
  status: string;
  error_message: string;
  created_at: string;
}

interface NotificationHistoryProps {
  logs: CommunicationLog[];
}

/**
 * Displays communication log entries for a booking.
 * Shows email_type, recipients, sent_at, and status per entry.
 * Failed entries are styled with red. Pending entries show "Pending" instead of a timestamp.
 * Entries are sorted by created_at descending (most recent first).
 */
export default function NotificationHistory({ logs }: NotificationHistoryProps) {
  if (!logs || logs.length === 0) {
    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="h6" component="h2" gutterBottom>
          Notification History
        </Typography>
        <Alert severity="info">No notifications sent yet</Alert>
      </Box>
    );
  }

  const sortedLogs = [...logs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="h6" component="h2" gutterBottom>
        Notification History
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="notification history">
          <TableHead>
            <TableRow>
              <TableCell>Email Type</TableCell>
              <TableCell>Recipients</TableCell>
              <TableCell>Sent At</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedLogs.map((log) => {
              const isFailed = log.status === 'failed';
              return (
                <TableRow
                  key={log.id}
                  sx={isFailed ? { backgroundColor: 'error.light' } : undefined}
                >
                  <TableCell>{log.email_type}</TableCell>
                  <TableCell>{log.recipients.join(', ')}</TableCell>
                  <TableCell>
                    {log.sent_at ? new Date(log.sent_at).toLocaleString() : 'Pending'}
                  </TableCell>
                  <TableCell>
                    {isFailed ? (
                      <Chip
                        label={log.status}
                        color="error"
                        size="small"
                        title={log.error_message}
                      />
                    ) : (
                      <Chip label={log.status} color="success" size="small" />
                    )}
                    {isFailed && log.error_message && (
                      <Typography
                        variant="caption"
                        component="span"
                        sx={{ color: 'error.main', mt: 0.5, display: 'block' }}
                      >
                        {log.error_message}
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
