import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  CircularProgress,
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import InfoIcon from '@mui/icons-material/Info';
import CloseIcon from '@mui/icons-material/Close';
import { useAlerts } from '../dashboardHooks';

const SEVERITY_CONFIG = {
  error: { icon: <ErrorIcon color="error" />, chipColor: 'error' as const },
  warning: { icon: <WarningIcon color="warning" />, chipColor: 'warning' as const },
  info: { icon: <InfoIcon color="info" />, chipColor: 'info' as const },
};

export default function AlertsSection() {
  const { data, isLoading } = useAlerts();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const alerts = (data ?? []).filter((a) => !dismissed.has(a.id));

  function handleDismiss(alertId: string) {
    setDismissed((prev) => new Set(prev).add(alertId));
  }

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Alerts
      </Typography>
      {alerts.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 3, textAlign: 'center', borderRadius: 2 }}>
          <Typography variant="body2" color="text.secondary">
            No active alerts.
          </Typography>
        </Paper>
      ) : (
        <Paper variant="outlined" sx={{ borderRadius: 2 }}>
          <List disablePadding>
            {alerts.map((alert, index) => {
              const config = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info;
              return (
                <ListItem
                  key={alert.id}
                  divider={index < alerts.length - 1}
                  secondaryAction={
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={() => handleDismiss(alert.id)}
                      aria-label="Dismiss alert"
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {config.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {alert.title}
                        </Typography>
                        <Chip label={alert.type} size="small" color={config.chipColor} variant="outlined" />
                      </Box>
                    }
                    secondary={alert.description}
                  />
                </ListItem>
              );
            })}
          </List>
        </Paper>
      )}
    </Box>
  );
}
