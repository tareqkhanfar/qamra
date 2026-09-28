import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { AuthCard } from "@/components/AuthCard";
import { AuthForm } from "@/components/AuthForm";
import { PageShell } from "@/components/site/PageShell";
import { getPublicSettings } from "@/lib/catalog";

export default async function RegisterPage() {
  const [t, site] = await Promise.all([getTranslations("auth"), getPublicSettings()]);
  return (
    <PageShell>
      <div className="px-4 pb-16">
        <AuthCard title={t("registerTitle")} subtitle={t("registerSubtitle")}>
          <Suspense>
            <AuthForm mode="register" googleEnabled={site?.google_login_enabled ?? false} />
          </Suspense>
        </AuthCard>
      </div>
    </PageShell>
  );
}
