import { redirect } from "next/navigation";

import { getDefaultLocalePath } from "../i18n/routing.ts";

export default function IndexPage() {
  redirect(getDefaultLocalePath());
}
