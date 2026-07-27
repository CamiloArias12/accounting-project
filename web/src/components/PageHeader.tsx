import { cn } from "@/lib/utils";

interface Props {
  title: string;
  subtitle?: React.ReactNode;
  // Buttons and filters that belong to the page as a whole.
  actions?: React.ReactNode;
  eyebrow?: string;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
  className,
}: Props) {
  return (
    <header
      className={cn(
        "flex flex-wrap items-end justify-between gap-x-6 gap-y-4",
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        {eyebrow && (
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-primary">
            {eyebrow}
          </p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>

      {actions && (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </header>
  );
}

export function PageShell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main
      className={cn(
        "mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 p-4 pt-16 sm:p-6 lg:pt-8",
        className,
      )}
    >
      {children}
    </main>
  );
}

export function LoadError({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive ring-1 ring-destructive/20"
    >
      {message}
    </p>
  );
}
