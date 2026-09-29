import type { Metadata } from "next";
import { AdminShell } from "@/components/admin/AdminShell";
import { AdminLeads } from "@/components/admin/leads/AdminLeads";

export const metadata: Metadata = { title: "طلبات عروض الأسعار", robots: { index: false, follow: false } };

export default function AdminLeadsPage() {
  return (
    <AdminShell active="leads">
      <AdminLeads />
    </AdminShell>
  );
}
