import React, { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className='min-h-screen bg-command text-white flex items-center justify-center p-4'>
          <div className='glass-panel max-w-md w-full p-8 text-center'>
            <div className='text-red-400 text-6xl mb-4'>!</div>
            <h2 className='text-xl font-bold mb-2'>Something went wrong</h2>
            <p className='text-slate-400 mb-4'>
              {this.props.fallbackMessage || 'An unexpected error occurred. Please try refreshing the page.'}
            </p>
            <details className='text-left text-xs text-slate-500 mb-4'>
              <summary>Error Details</summary>
              <pre className='mt-2 p-2 bg-slate-900/50 rounded overflow-auto max-h-40'>
                {this.state.error && this.state.error.toString()}
              </pre>
            </details>
            <button
              onClick={() => window.location.reload()}
              className='px-6 py-2 bg-alert-500 text-white rounded-lg hover:bg-alert-600 transition-colors'
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;