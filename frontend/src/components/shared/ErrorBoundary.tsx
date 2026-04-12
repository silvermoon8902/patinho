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
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, color: "#001F3F" }}>
          <h2>Algo deu errado</h2>
          <pre style={{ background: "#f5f5f5", padding: 12, borderRadius: 8, overflow: "auto", fontSize: 13 }}>
            {this.state.error?.message}
            {"\n"}
            {this.state.error?.stack}
          </pre>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/";
            }}
            style={{ marginTop: 12, padding: "8px 16px", background: "#FFD10D", border: "none", borderRadius: 6, cursor: "pointer" }}
          >
            Voltar ao inicio
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
