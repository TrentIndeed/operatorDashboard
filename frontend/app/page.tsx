import { redirect } from "next/navigation";

export default function RootPage() {
  // Middleware handles the redirect based on auth state
  // This is a fallback
  redirect("/landing");
}
