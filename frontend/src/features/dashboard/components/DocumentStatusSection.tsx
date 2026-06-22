import { useNavigate } from 'react-router-dom';
import { Box, Typography, Paper, Grid, Button } from '@mui/material';
import { useDocumentStatus } from '../dashboardHooks';

export default function DocumentStatusSection() {
  const navigate = useNavigate();
  const { data } = useDocumentStatus();

  const items = [
    {
      label: 'Pending Commercial Invoices',
      count: data?.pending_commercial_invoices ?? 0,
      icon: 'description',
      path: '/search',
    },
    {
      label: 'Pending Packing Lists',
      count: data?.pending_packing_lists ?? 0,
      icon: 'inventory_2',
      path: '/search',
    },
    {
      label: 'Pending Bills of Lading',
      count: data?.pending_bls ?? 0,
      icon: 'sailing',
      path: '/search',
    },
  ];

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Document Status
      </Typography>
      <Grid container spacing={2}>
        {items.map((item) => (
          <Grid size={{ xs: 12, sm: 4 }} key={item.label}>
            <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', borderRadius: 2 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 28, color: '#666' }}>
                {item.icon}
              </span>
              <Typography variant="h5" sx={{ fontWeight: 600, mt: 1 }}>
                {item.count}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {item.label}
              </Typography>
              {item.count > 0 && (
                <Button
                  size="small"
                  sx={{ mt: 1 }}
                  onClick={() => navigate(item.path)}
                >
                  View
                </Button>
              )}
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
