import { Chip } from '@mui/material';
import type { BLStatus } from '../hooks';

const STATUS_CONFIG: Record<BLStatus, { label: string; color: 'default' | 'info' | 'warning' | 'success' }> = {
  DRAFT: { label: 'Draft', color: 'default' },
  SUBMITTED: { label: 'Submitted', color: 'warning' },
  RELEASED: { label: 'Released', color: 'success' },
};

interface BLStatusBadgeProps {
  status: BLStatus;
}

export default function BLStatusBadge({ status }: BLStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, color: 'default' as const };

  return (
    <Chip
      label={config.label}
      color={config.color}
      size="small"
      variant="filled"
    />
  );
}
