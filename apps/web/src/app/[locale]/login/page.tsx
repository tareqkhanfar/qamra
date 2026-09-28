import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { AuthCard } from "@/components/AuthCard";
import { AuthForm } from "@/components/AuthForm";
import { PageShell } from "@/components/site/PageShell";

export default async function LoginPage() {
  const t = await getTranslations("auth");
  return (
    <PageShell>
      <div className="px-4 pb-16">
        <AuthCard title={t("loginTitle")} subtitle={t("loginSubtitle")}>
          <Suspense>
            <AuthForm mode="login" />
          </Suspense>
        </AuthCard>
      </div>
    </PageShell>
  );
}
