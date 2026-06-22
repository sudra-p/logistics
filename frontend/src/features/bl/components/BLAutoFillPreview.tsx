import { Alert, Box, Typography, List, ListItem, ListItemText } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';

interface AutoFillData {
  vessel_name?: string;
  voyage_number?: string;
  container_number?: string;
  shipper_name?: string;
  consignee_name?: string;
  cargo_description?: string;
}

interface BLAutoFillPreviewProps {
  data: AutoFillData;
}

export default function BLAutoFillPreview({ data }: BLAutoFillPreviewProps) {
  const hasData = Object.values(data).some((v) => v);

  if (!hasData) return null;

  return (
    <Alert severity="info" icon={<InfoIcon />} sx={{ mb: 3 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Auto-filled from Booking / Commercial Invoice
      </Typography>
      <Box>
        <List dense disablePadding>
          {data.vessel_name && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Vessel: ${data.vessel_name}`} />
            </ListItem>
          )}
          {data.voyage_number && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Voyage: ${data.voyage_number}`} />
            </ListItem>
          )}
          {data.container_number && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Container: ${data.container_number}`} />
            </ListItem>
          )}
          {data.shipper_name && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Shipper: ${data.shipper_name}`} />
            </ListItem>
          )}
          {data.consignee_name && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Consignee: ${data.consignee_name}`} />
            </ListItem>
          )}
          {data.cargo_description && (
            <ListItem disableGutters disablePadding>
              <ListItemText primary={`Cargo: ${data.cargo_description}`} />
            </ListItem>
          )}
        </List>
      </Box>
    </Alert>
  );
}
