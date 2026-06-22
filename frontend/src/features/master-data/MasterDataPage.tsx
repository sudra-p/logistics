import { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  List,
  ListItemButton,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  IconButton,
  Alert,
  InputAdornment,
  CircularProgress,
  Chip,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import type { AxiosError } from 'axios';
import type { ValidationErrorResponse } from '@/api/types';
import {
  ENTITY_TYPES,
  ENTITY_LABELS,
  useMasterDataList,
  useCreateEntity,
  useUpdateEntity,
  useToggleEntityActive,
  useDeleteEntity,
} from './useMasterData';
import type { EntityType, MasterDataEntity } from './useMasterData';

/** Extract field-level validation errors from API response. */
function getValidationErrors(error: unknown): Record<string, string[]> | null {
  const axiosError = error as AxiosError<ValidationErrorResponse>;
  if (axiosError?.response?.status === 400 && axiosError.response.data) {
    return axiosError.response.data as Record<string, string[]>;
  }
  return null;
}

/** Check if an error is a 409 Conflict (entity in use). */
function isConflictError(error: unknown): boolean {
  const axiosError = error as AxiosError;
  return axiosError?.response?.status === 409;
}

export default function MasterDataPage() {
  const [selectedEntity, setSelectedEntity] = useState<EntityType>('clients');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<MasterDataEntity | null>(null);
  const [formName, setFormName] = useState('');
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Queries and mutations
  const { data, isLoading, isError, error: fetchError } = useMasterDataList({
    entityType: selectedEntity,
    page: page + 1, // API is 1-indexed
    pageSize,
    search,
  });

  const createMutation = useCreateEntity(selectedEntity);
  const updateMutation = useUpdateEntity(selectedEntity);
  const toggleActiveMutation = useToggleEntityActive(selectedEntity);
  const deleteMutation = useDeleteEntity(selectedEntity);

  // Handlers
  const handleEntityTypeChange = useCallback((entityType: EntityType) => {
    setSelectedEntity(entityType);
    setPage(0);
    setSearch('');
    setDeleteError(null);
  }, []);

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setPage(0);
  }, []);

  const handleOpenAdd = useCallback(() => {
    setEditingEntity(null);
    setFormName('');
    setFormErrors({});
    setDialogOpen(true);
  }, []);

  const handleOpenEdit = useCallback((entity: MasterDataEntity) => {
    setEditingEntity(entity);
    setFormName(entity.name);
    setFormErrors({});
    setDialogOpen(true);
  }, []);

  const handleCloseDialog = useCallback(() => {
    setDialogOpen(false);
    setEditingEntity(null);
    setFormName('');
    setFormErrors({});
  }, []);

  const handleSubmit = useCallback(() => {
    // Client-side validation
    const errors: Record<string, string[]> = {};
    if (!formName.trim()) {
      errors.name = ['Name is required.'];
    } else if (formName.length > 255) {
      errors.name = ['Name must be at most 255 characters.'];
    }
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    const payload = { name: formName.trim() };

    if (editingEntity) {
      updateMutation.mutate(
        { id: editingEntity.id, payload },
        {
          onSuccess: () => {
            handleCloseDialog();
          },
          onError: (err) => {
            const validationErrors = getValidationErrors(err);
            if (validationErrors) {
              setFormErrors(validationErrors);
            }
          },
        },
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => {
          handleCloseDialog();
        },
        onError: (err) => {
          const validationErrors = getValidationErrors(err);
          if (validationErrors) {
            setFormErrors(validationErrors);
          }
        },
      });
    }
  }, [formName, editingEntity, createMutation, updateMutation, handleCloseDialog]);

  const handleToggleActive = useCallback(
    (entity: MasterDataEntity) => {
      toggleActiveMutation.mutate({ id: entity.id, is_active: !entity.is_active });
    },
    [toggleActiveMutation],
  );

  const handleDelete = useCallback(
    (entity: MasterDataEntity) => {
      setDeleteError(null);
      deleteMutation.mutate(entity.id, {
        onError: (err) => {
          if (isConflictError(err)) {
            setDeleteError(
              `Cannot delete "${entity.name}". This entity is referenced by existing booking records.`,
            );
          } else {
            setDeleteError(`Failed to delete "${entity.name}". Please try again.`);
          }
        },
      });
    },
    [deleteMutation],
  );

  const isMutating = createMutation.isPending || updateMutation.isPending;

  return (
    <Box sx={{ display: 'flex', p: 3, gap: 3, minHeight: '70vh' }}>
      {/* Entity type navigation */}
      <Paper sx={{ width: 220, flexShrink: 0, overflow: 'auto' }}>
        <List component="nav" aria-label="Master data entity types">
          {ENTITY_TYPES.map((type) => (
            <ListItemButton
              key={type}
              selected={selectedEntity === type}
              onClick={() => handleEntityTypeChange(type)}
            >
              <ListItemText primary={ENTITY_LABELS[type]} />
            </ListItemButton>
          ))}
        </List>
      </Paper>

      {/* Main content area */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" component="h1">
            {ENTITY_LABELS[selectedEntity]}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenAdd}
          >
            Add New
          </Button>
        </Box>

        {/* Search filter */}
        <TextField
          size="small"
          placeholder={`Search ${ENTITY_LABELS[selectedEntity].toLowerCase()}...`}
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          sx={{ mb: 2, width: 300 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            },
          }}
        />

        {/* Delete error alert */}
        {deleteError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setDeleteError(null)}>
            {deleteError}
          </Alert>
        )}

        {/* Fetch error */}
        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load data.{' '}
            {(fetchError as AxiosError)?.response?.status === 403
              ? 'Access denied. Admin privileges required.'
              : 'Please try again.'}
          </Alert>
        )}

        {/* Loading state */}
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Entity table */}
        {!isLoading && data && (
          <>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.results.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} align="center">
                        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                          No entities found.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.results.map((entity) => (
                      <TableRow key={entity.id}>
                        <TableCell>{entity.name}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Switch
                              size="small"
                              checked={entity.is_active}
                              onChange={() => handleToggleActive(entity)}
                              slotProps={{
                                input: {
                                  'aria-label': `Toggle active status for ${entity.name}`,
                                },
                              }}
                            />
                            <Chip
                              label={entity.is_active ? 'Active' : 'Inactive'}
                              color={entity.is_active ? 'success' : 'default'}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          {new Date(entity.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenEdit(entity)}
                            aria-label={`Edit ${entity.name}`}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDelete(entity)}
                            aria-label={`Delete ${entity.name}`}
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={data.count}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={pageSize}
              onRowsPerPageChange={(e) => {
                const newSize = Math.min(parseInt(e.target.value, 10), 100);
                setPageSize(newSize);
                setPage(0);
              }}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </>
        )}

        {/* Add/Edit Dialog */}
        <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
          <DialogTitle>
            {editingEntity ? `Edit ${ENTITY_LABELS[selectedEntity]}` : `Add New ${ENTITY_LABELS[selectedEntity]}`}
          </DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Name"
              fullWidth
              required
              value={formName}
              onChange={(e) => {
                setFormName(e.target.value);
                // Clear name errors on change
                if (formErrors.name) {
                  setFormErrors((prev) => {
                    const next = { ...prev };
                    delete next.name;
                    return next;
                  });
                }
              }}
              error={!!formErrors.name}
              helperText={formErrors.name?.join(' ')}
              slotProps={{
                htmlInput: { maxLength: 255 },
              }}
            />
            {/* Display non-field errors */}
            {formErrors.non_field_errors && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {formErrors.non_field_errors.join(' ')}
              </Alert>
            )}
            {formErrors.detail && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {(formErrors.detail as unknown as string[]
                ).join(' ')}
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog} disabled={isMutating}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              variant="contained"
              disabled={isMutating}
              startIcon={isMutating ? <CircularProgress size={16} /> : undefined}
            >
              {editingEntity ? 'Save' : 'Create'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Box>
  );
}
