import { Box, Tooltip, LinearProgress } from '@mui/material';

interface StockLevelIndicatorProps {
  availableStock: number;
  reservedStock: number;
  shippedStock: number;
}

/**
 * Visual bar indicator for stock levels.
 * - Green when available > 75% of total
 * - Yellow when available is 25–75% of total
 * - Red when available < 25% of total
 */
export default function StockLevelIndicator({
  availableStock,
  reservedStock,
  shippedStock,
}: StockLevelIndicatorProps) {
  const total = availableStock + reservedStock + shippedStock;

  if (total === 0) {
    return (
      <Tooltip title="No stock recorded">
        <Box sx={{ width: '100%', minWidth: 80 }}>
          <LinearProgress
            variant="determinate"
            value={0}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                backgroundColor: 'grey.400',
                borderRadius: 4,
              },
            }}
          />
        </Box>
      </Tooltip>
    );
  }

  const percentage = (availableStock / total) * 100;

  let color: string;
  if (percentage > 75) {
    color = '#4caf50'; // green
  } else if (percentage >= 25) {
    color = '#ff9800'; // yellow/amber
  } else {
    color = '#f44336'; // red
  }

  const tooltipText = `Available: ${availableStock} / Total: ${total} (${Math.round(percentage)}%)`;

  return (
    <Tooltip title={tooltipText}>
      <Box sx={{ width: '100%', minWidth: 80 }}>
        <LinearProgress
          variant="determinate"
          value={percentage}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: 'grey.200',
            '& .MuiLinearProgress-bar': {
              backgroundColor: color,
              borderRadius: 4,
            },
          }}
        />
      </Box>
    </Tooltip>
  );
}
