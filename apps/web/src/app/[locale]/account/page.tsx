import { AccountView } from "@/components/AccountView";
import { PageShell } from "@/components/site/PageShell";

export const metadata = { robots: { index: false, follow: false } }; // private (Phase 5 SEO)

export default function AccountPage() {
  return (
    <PageShell footer={false}>
      <AccountView />
    </PageShell>
  );
}
