import type { ReactNode } from "react";

const tones = {
  error: "border-danger/30 bg-danger-bg text-danger",
  success: "border-success/30 bg-success-bg text-success",
  info: "border-info/20 bg-info-bg text-info",
};

export function Alert({ tone = "error", children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-sm border px-4 py-3 text-small font-medium ${tones[tone]}`}
    >
      {children}
    </div>
  );
}
