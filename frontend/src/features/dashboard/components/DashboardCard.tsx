import { Card, CardContent, Typography, Box } from '@mui/material';

interface DashboardCardProps {
  title: string;
  count: number;
  color?: string;
}

export default function DashboardCard({ title, count, color = 'primary.main' }: DashboardCardProps) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <Typography variant="h3" component="span" sx={{ color, fontWeight: 600 }}>
            {count}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
