import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
    // Forward to Sentry if the runtime hook is wired.
    const w = window as unknown as { Sentry?: { captureException: (e: Error, ctx?: unknown) => void } };
    if (w.Sentry?.captureException) {
      try {
        w.Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } });
      } catch {
        /* swallow */
      }
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env?.DEV;
      return (
        <div className="error-boundary-page">
          <div className="error-boundary-card card">
            <div className="error-boundary-icon" aria-hidden="true">!</div>
            <h2>Algo deu errado</h2>
            <p className="error-boundary-message">
              Encontramos um erro inesperado. Tente atualizar a página ou
              voltar ao início. Se o problema persistir, entre em contato
              com o suporte.
            </p>
            {isDev && this.state.error && (
              <details className="error-boundary-details">
                <summary>Detalhes técnicos (desenvolvimento)</summary>
                <pre>
                  {this.state.error.message}
                  {"\n\n"}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
            <div className="error-boundary-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={this.handleReload}
              >
                Atualizar página
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={this.handleHome}
              >
                Voltar ao início
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
