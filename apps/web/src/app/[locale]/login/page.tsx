import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { AuthCard } from "@/components/AuthCard";
import { AuthForm } from "@/components/AuthForm";

export default async function LoginPage() {
  const t = await getTranslations("auth");
  return (
    <AuthCard title={t("loginTitle")} subtitle={t("loginSubtitle")}>
      <Suspense>
        <AuthForm mode="login" />
      </Suspense>
    </AuthCard>
  );
}
