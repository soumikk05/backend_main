import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught a render crash:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 my-4 max-w-2xl mx-auto shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-3 text-rose-400 font-mono font-bold text-base mb-2">
            <AlertTriangle size={22} />
            <span>Display Rendering Recovered</span>
          </div>
          <p className="text-xs text-rose-200/90 font-mono mb-4 leading-relaxed">
            {this.state.error?.message || 'An unexpected rendering error occurred while visualizing module outputs.'}
          </p>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 font-mono text-xs font-semibold transition-all cursor-pointer shadow-lg"
          >
            <RotateCcw size={14} />
            <span>Reset & Try Again</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
