import { Noto_Naskh_Arabic } from "next/font/google";

/** The books' story font (as in the print PDF): full tashkeel that never collides. Loaded only where used. */
export const naskh = Noto_Naskh_Arabic({
  subsets: ["arabic", "latin"],
  weight: ["400", "600", "700"],
  display: "swap",
});
