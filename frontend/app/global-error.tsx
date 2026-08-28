"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ background: "#f6f5f2", fontFamily: "system-ui, sans-serif" }}>
        <div className="flex min-h-screen items-center justify-center px-6">
          <div
            style={{
              maxWidth: "28rem",
              padding: "2rem",
              borderRadius: "0.75rem",
              border: "1px solid #e4e2db",
              background: "#ffffff",
              textAlign: "center",
            }}
          >
            <h1 style={{ fontSize: "1.125rem", fontWeight: 600 }}>Application error</h1>
            <p style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "#6b6a72" }}>
              SkillLens encountered an unexpected error.
            </p>
            <button
              type="button"
              onClick={() => reset()}
              style={{
                marginTop: "1.5rem",
                padding: "0.625rem 1rem",
                borderRadius: "0.5rem",
                background: "#5b4fd9",
                color: "#ffffff",
                border: "none",
                fontSize: "0.875rem",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
