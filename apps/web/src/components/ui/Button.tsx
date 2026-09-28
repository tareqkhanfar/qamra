import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "solid" | "secondary" | "ghost" | "danger";
type Size = "lg" | "md" | "sm";

const variants: Record<Variant, string> = {
  // amber = conversion moments only (design README); night = normal "continue"
  primary: "bg-amber-500 text-night-950 hover:shadow-lamp active:bg-amber-600",
  solid: "bg-night-900 text-paper-raised hover:bg-night-800 active:bg-night-950",
  secondary: "border-2 border-night-900 text-night-900 hover:bg-night-100",
  ghost: "text-night-900 underline underline-offset-4 hover:text-night-700",
  danger: "bg-danger text-white hover:brightness-110",
};

const sizes: Record<Size, string> = {
  lg: "min-h-14 px-7 text-body-l",
  md: "min-h-12 px-6 text-body",
  sm: "min-h-11 px-4 text-small",
};

export function buttonClasses(variant: Variant = "solid", size: Size = "md", extra = ""): string {
  return [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-display font-bold transition",
    "disabled:cursor-not-allowed disabled:bg-paper-sunk disabled:text-ink-faint disabled:shadow-none",
    variants[variant],
    sizes[size],
    extra,
  ].join(" ");
}

export function Spinner() {
  return (
    <svg className="size-5 animate-spin" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** Points "forward": left in RTL, right in LTR. */
export function ArrowForward() {
  return (
    <svg className="size-5 rtl:-scale-x-100" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M5 12h14M13 6l6 6-6 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  loadingLabel?: string;
  children: ReactNode;
};

export function Button({
  variant = "solid",
  size = "md",
  loading,
  loadingLabel,
  className = "",
  children,
  disabled,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, size, className)}
    >
      {loading ? (
        <>
          <Spinner />
          {loadingLabel ?? children}
        </>
      ) : (
        children
      )}
    </button>
  );
}
