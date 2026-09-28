/** Brand comes from config (Addendum 1: a rename must never touch code). */
export const brand = {
  nameAr: process.env.NEXT_PUBLIC_BRAND_NAME_AR ?? "قمرة",
  nameEn: process.env.NEXT_PUBLIC_BRAND_NAME_EN ?? "Qamra",
  domain: process.env.NEXT_PUBLIC_BRAND_DOMAIN ?? "qamra.app",
};

export function brandName(locale: string): string {
  return locale === "ar" ? brand.nameAr : brand.nameEn;
}
