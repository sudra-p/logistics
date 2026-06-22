import { Box, Paper, Typography } from '@mui/material';

interface KPICardProps {
  title: string;
  value: number | string;
  icon: string;
  trend?: { value: string; direction: 'up' | 'down' | 'neutral' };
  color?: 'primary' | 'success' | 'warning' | 'error' | 'info';
}

const colorMap = {
  primary: { bg: 'primary.50', icon: 'primary.main' },
  success: { bg: 'success.50', icon: 'success.main' },
  warning: { bg: 'warning.50', icon: 'warning.main' },
  error: { bg: 'error.50', icon: 'error.main' },
  info: { bg: 'info.50', icon: 'info.main' },
};

export default function KPICard({ title, value, icon, trend, color = 'primary' }: KPICardProps) {
  const colors = colorMap[color];

  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 1.5,
            bgcolor: colors.bg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 22, color: 'inherit' }}
          >
            {icon}
          </span>
        </Box>
        {trend && (
          <Typography
            variant="caption"
            sx={{
              px: 1,
              py: 0.25,
              borderRadius: 1,
              bgcolor: trend.direction === 'up' ? 'success.50' : trend.direction === 'down' ? 'error.50' : 'grey.100',
              color: trend.direction === 'up' ? 'success.main' : trend.direction === 'down' ? 'error.main' : 'text.secondary',
            }}
          >
            {trend.value}
          </Typography>
        )}
      </Box>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {title}
      </Typography>
    </Paper>
  );
}
