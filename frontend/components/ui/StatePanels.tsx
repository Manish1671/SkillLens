import { Button } from "./Button";

export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="py-10 text-center" role="status" aria-live="polite">
      <div className="mx-auto mb-3 h-1.5 w-24 overflow-hidden rounded-full bg-surface-muted">
        <div className="h-full w-1/2 animate-pulse bg-accent" />
      </div>
      <p className="text-sm text-muted">{message}</p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="border border-danger/20 bg-danger-soft px-5 py-4" role="alert">
      <p className="text-sm text-danger">{message}</p>
      {onRetry ? (
        <Button variant="danger" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border border-dashed border-border bg-surface px-6 py-8">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  breadcrumb,
  eyebrow,
}: {
  title: string;
  description?: string;
  breadcrumb?: React.ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="space-y-1.5">
      {breadcrumb ? <div className="text-sm text-muted">{breadcrumb}</div> : null}
      {eyebrow ? <p className="sl-eyebrow">{eyebrow}</p> : null}
      <h1 className="text-2xl font-semibold tracking-tight sm:text-[1.75rem]">{title}</h1>
      {description ? <p className="max-w-2xl text-sm leading-relaxed text-muted">{description}</p> : null}
    </header>
  );
}
