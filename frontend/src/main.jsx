import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./style.css";

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("ReelPilot render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: "100vh", padding: 24, background: "#10131c", color: "#f3f4f8", fontFamily: "Arial, sans-serif" }}>
          <h1>ReelPilot could not load</h1>
          <p>The dashboard encountered a browser error. Share this message with support:</p>
          <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", color: "#ffbd9c" }}>
            {String(this.state.error?.stack || this.state.error?.message || this.state.error)}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const rootElement = document.getElementById("root");

if (!rootElement) {
  document.body.innerHTML = '<main style="padding:24px;font-family:Arial">ReelPilot error: #root element is missing.</main>';
} else {
  window.addEventListener("error", (event) => {
    console.error("ReelPilot browser error:", event.error || event.message);
  });

  window.addEventListener("unhandledrejection", (event) => {
    console.error("ReelPilot promise error:", event.reason);
  });

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AppErrorBoundary>
        <App />
      </AppErrorBoundary>
    </React.StrictMode>
  );
}
