import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Dashboard } from "@/components/portal/Dashboard";
import { PortalShell } from "@/components/portal/PortalShell";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.dashboard"), robots: { index: false, follow: false } };
}

/** The kindergarten portal's home (design PortalDashboard). */
export default function PortalPage() {
  return (
    <PortalShell active="dashboard">
      <Dashboard />
    </PortalShell>
  );
}
