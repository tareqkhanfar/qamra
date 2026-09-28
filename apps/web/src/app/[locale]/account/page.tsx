import { AccountView } from "@/components/AccountView";
import { PageShell } from "@/components/site/PageShell";

export default function AccountPage() {
  return (
    <PageShell footer={false}>
      <AccountView />
    </PageShell>
  );
}
