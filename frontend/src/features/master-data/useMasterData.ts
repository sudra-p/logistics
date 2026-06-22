import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { PaginatedResponse } from '@/api/types';

/**
 * Entity types supported by the master data module.
 */
export const ENTITY_TYPES = [
  'clients',
  'consignees',
  'shippers',
  'brokers',
  'shipping-lines',
  'vessels',
  'ports',
  'commodities',
  'container-types',
  'marketing-persons',
  'transporters',
  'forwarders',
] as const;

export type EntityType = (typeof ENTITY_TYPES)[number];

/** Human-readable labels for each entity type. */
export const ENTITY_LABELS: Record<EntityType, string> = {
  clients: 'Client',
  consignees: 'Consignee',
  shippers: 'Shipper',
  brokers: 'Broker',
  'shipping-lines': 'Shipping Line',
  vessels: 'Vessel',
  ports: 'Port',
  commodities: 'Commodity',
  'container-types': 'Container Type',
  'marketing-persons': 'Marketing Person',
  transporters: 'Transporter',
  forwarders: 'Forwarder',
};

/** Generic master data entity shape. */
export interface MasterDataEntity {
  id: number;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  [key: string]: unknown;
}

/** Parameters for fetching a paginated entity list. */
export interface FetchEntitiesParams {
  entityType: EntityType;
  page: number;
  pageSize: number;
  search: string;
}

/** Payload for creating or updating an entity. */
export interface EntityPayload {
  name: string;
  is_active?: boolean;
  [key: string]: unknown;
}

/**
 * Fetch paginated master data entities.
 */
async function fetchEntities(
  params: FetchEntitiesParams,
): Promise<PaginatedResponse<MasterDataEntity>> {
  const { entityType, page, pageSize, search } = params;
  const queryParams: Record<string, string | number> = {
    page,
    page_size: pageSize,
  };
  if (search) {
    queryParams.search = search;
  }
  const { data } = await apiClient.get<PaginatedResponse<MasterDataEntity>>(
    ENDPOINTS.MASTER_DATA(entityType),
    { params: queryParams },
  );
  return data;
}

/**
 * Create a new entity.
 */
async function createEntity(
  entityType: EntityType,
  payload: EntityPayload,
): Promise<MasterDataEntity> {
  const { data } = await apiClient.post<MasterDataEntity>(
    ENDPOINTS.MASTER_DATA(entityType),
    payload,
  );
  return data;
}

/**
 * Update an existing entity via PATCH.
 */
async function updateEntity(
  entityType: EntityType,
  id: number,
  payload: Partial<EntityPayload>,
): Promise<MasterDataEntity> {
  const { data } = await apiClient.patch<MasterDataEntity>(
    ENDPOINTS.MASTER_DATA_DETAIL(entityType, id),
    payload,
  );
  return data;
}

/**
 * Delete an entity.
 */
async function deleteEntity(entityType: EntityType, id: number): Promise<void> {
  await apiClient.delete(ENDPOINTS.MASTER_DATA_DETAIL(entityType, id));
}

/**
 * Hook for querying paginated master data entities.
 */
export function useMasterDataList(params: FetchEntitiesParams) {
  return useQuery({
    queryKey: ['master-data', params.entityType, params.page, params.pageSize, params.search],
    queryFn: () => fetchEntities(params),
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Hook for creating a master data entity.
 */
export function useCreateEntity(entityType: EntityType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: EntityPayload) => createEntity(entityType, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['master-data', entityType] });
    },
  });
}

/**
 * Hook for updating a master data entity.
 */
export function useUpdateEntity(entityType: EntityType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<EntityPayload> }) =>
      updateEntity(entityType, id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['master-data', entityType] });
    },
  });
}

/**
 * Hook for toggling entity active status.
 */
export function useToggleEntityActive(entityType: EntityType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateEntity(entityType, id, { is_active }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['master-data', entityType] });
    },
  });
}

/**
 * Hook for deleting a master data entity.
 */
export function useDeleteEntity(entityType: EntityType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteEntity(entityType, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['master-data', entityType] });
    },
  });
}
