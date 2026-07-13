import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  error: Error | null;
};

class AppErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("React render error:", error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return <StartupErrorScreen error={this.state.error} title="React-Fehler beim Rendern" />;
    }

    return this.props.children;
  }
}

function StartupErrorScreen({ error, title }: { error: unknown; title: string }) {
  const message = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : null;

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "32px",
        background: "#f4f7fb",
        color: "#15253c",
        fontFamily: "Aptos, Segoe UI, sans-serif",
      }}
    >
      <div
        style={{
          maxWidth: "960px",
          margin: "0 auto",
          background: "#ffffff",
          border: "1px solid #d7e2ec",
          borderRadius: "18px",
          padding: "24px",
          boxShadow: "0 18px 40px rgba(13, 31, 52, 0.08)",
        }}
      >
        <h1 style={{ marginTop: 0, marginBottom: "12px" }}>{title}</h1>
        <p style={{ marginTop: 0, color: "#607286" }}>
          Die Anwendung ist geladen, aber beim Start ist ein Laufzeitfehler aufgetreten.
        </p>
        <pre
          style={{
            whiteSpace: "pre-wrap",
            overflowX: "auto",
            padding: "16px",
            borderRadius: "12px",
            background: "#fff1ef",
            border: "1px solid #f5c0b9",
            color: "#a33629",
          }}
        >
          {message}
          {stack ? `\n\n${stack}` : ""}
        </pre>
      </div>
    </div>
  );
}

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Das Root-Element '#root' wurde nicht gefunden.");
}

const root = ReactDOM.createRoot(rootElement);

async function mountApp() {
  try {
    const { default: App } = await import("./App");
    root.render(
      <React.StrictMode>
        <AppErrorBoundary>
          <App />
        </AppErrorBoundary>
      </React.StrictMode>,
    );
  } catch (error) {
    console.error("Startup error while importing App:", error);
    root.render(<StartupErrorScreen error={error} title="Fehler beim Laden der Anwendung" />);
  }
}

void mountApp();
