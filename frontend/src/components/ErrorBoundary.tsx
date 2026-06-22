import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Paper from '@mui/material/Paper';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Top-level error boundary for unhandled React errors.
 * Displays a fallback UI with the error message and a "Try Again" button
 * that reloads the page.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log the error for debugging purposes
    console.error('Unhandled error caught by ErrorBoundary:', error, errorInfo);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container maxWidth="sm">
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '100vh',
            }}
          >
            <Paper
              elevation={3}
              sx={{ p: 4, textAlign: 'center', width: '100%' }}
            >
              <Typography variant="h5" gutterBottom color="error">
                Something went wrong
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                {this.state.error?.message || 'An unexpected error occurred.'}
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={this.handleReload}
              >
                Try Again
              </Button>
            </Paper>
          </Box>
        </Container>
      );
    }

    return this.props.children;
  }
}
