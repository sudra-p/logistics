import { Chip } from '@mui/material';
import type { ChipProps } from '@mui/material';
import type { PIStatus } from '../hooks';

interface PIStatusBadgeProps {
  status: PIStatus;
}

const STATUS_CONFIG: Record<PIStatus, { label: string; color: ChipProps['color'] }> = {
  DRAFT: { label: 'Draft', color: 'default' },
  SENT: { label: 'Sent', color: 'info' },
  APPROVED: { label: 'Approved', color: 'primary' },
  PAYMENT_PENDING: { label: 'Payment Pending', color: 'warning' },
  PAID: { label: 'Paid', color: 'success' },
};

export default function PIStatusBadge({ status }: PIStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, color: 'default' as const };

  return (
    <Chip
      label={config.label}
      color={config.color}
      size="small"
      variant="outlined"
    />
  );
}
