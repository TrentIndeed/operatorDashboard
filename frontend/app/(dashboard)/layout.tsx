import { Sidebar } from "@/components/layout/Sidebar";
import { SupportChat } from "./support-chat";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 ml-0 lg:ml-60 mt-14 lg:mt-0 min-h-screen overflow-y-auto">
        {children}
      </main>
      <SupportChat />
    </div>
  );
}
