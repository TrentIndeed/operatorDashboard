import { Suspense } from "react";
import { CommandCenterClient } from "./CommandCenterClient";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function HomePage() {
  return (
    <Suspense fallback={<CommandCenterSkeleton />}>
      <CommandCenterClient />
    </Suspense>
  );
}

function CommandCenterSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-muted rounded" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-48 bg-card rounded-lg border border-border/50" />
        ))}
      </div>
    </div>
  );
}
