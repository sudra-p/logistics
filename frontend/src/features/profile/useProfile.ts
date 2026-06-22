import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import type { User } from '@/auth/types';

export interface ProfileUpdatePayload {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  department?: string;
}

/**
 * Fetch the current user's profile data.
 */
export function useProfile() {
  return useQuery<User>({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>(ENDPOINTS.USER_PROFILE);
      return data;
    },
  });
}

/**
 * PATCH update the current user's profile.
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation<User, Error, ProfileUpdatePayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.patch<User>(ENDPOINTS.USER_PROFILE, payload);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['profile'], data);
    },
  });
}

/**
 * Upload a new avatar image.
 */
export function useUploadAvatar() {
  const queryClient = useQueryClient();

  return useMutation<{ avatar_url: string }, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('avatar', file);
      const { data } = await apiClient.post<{ avatar_url: string }>(
        ENDPOINTS.USER_AVATAR,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}
