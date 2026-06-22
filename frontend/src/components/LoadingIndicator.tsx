import { useState, useEffect, useRef } from 'react';
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import apiClient from '@/api/client';

/**
 * Global loading indicator that appears as a thin progress bar at the top of the viewport.
 * Shows after 300ms of a pending API request to avoid flash for fast requests.
 * Removes within 100ms of response arrival.
 */
export function LoadingIndicator() {
  const [visible, setVisible] = useState(false);
  const pendingCount = useRef(0);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const requestInterceptor = apiClient.interceptors.request.use(
      (config) => {
        pendingCount.current += 1;

        // Clear any pending hide timer since we have a new request
        if (hideTimerRef.current !== null) {
          clearTimeout(hideTimerRef.current);
          hideTimerRef.current = null;
        }

        // Only set show timer if not already visible and no timer pending
        if (showTimerRef.current === null && !visible) {
          showTimerRef.current = setTimeout(() => {
            if (pendingCount.current > 0) {
              setVisible(true);
            }
            showTimerRef.current = null;
          }, 300);
        }

        return config;
      },
      (error) => {
        pendingCount.current = Math.max(0, pendingCount.current - 1);
        scheduleHide();
        return Promise.reject(error);
      },
    );

    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => {
        pendingCount.current = Math.max(0, pendingCount.current - 1);
        scheduleHide();
        return response;
      },
      (error) => {
        pendingCount.current = Math.max(0, pendingCount.current - 1);
        scheduleHide();
        return Promise.reject(error);
      },
    );

    function scheduleHide() {
      if (pendingCount.current === 0) {
        // Clear the show timer if no requests are pending
        if (showTimerRef.current !== null) {
          clearTimeout(showTimerRef.current);
          showTimerRef.current = null;
        }

        // Schedule hide within 100ms
        if (hideTimerRef.current === null) {
          hideTimerRef.current = setTimeout(() => {
            setVisible(false);
            hideTimerRef.current = null;
          }, 100);
        }
      }
    }

    return () => {
      apiClient.interceptors.request.eject(requestInterceptor);
      apiClient.interceptors.response.eject(responseInterceptor);

      if (showTimerRef.current !== null) {
        clearTimeout(showTimerRef.current);
      }
      if (hideTimerRef.current !== null) {
        clearTimeout(hideTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!visible) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
      }}
    >
      <LinearProgress />
    </Box>
  );
}
