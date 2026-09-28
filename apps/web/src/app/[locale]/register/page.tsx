import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { AuthCard } from "@/components/AuthCard";
import { AuthForm } from "@/components/AuthForm";

export default async function RegisterPage() {
  const t = await getTranslations("auth");
  return (
    <AuthCard title={t("registerTitle")} subtitle={t("registerSubtitle")}>
      <Suspense>
        <AuthForm mode="register" />
      </Suspense>
    </AuthCard>
  );
}
