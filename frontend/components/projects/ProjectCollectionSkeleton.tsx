import { Skeleton } from "@/components/ui/skeleton";

export function ProjectCollectionSkeleton({ compact = false }: { compact?: boolean }) {
    return (
        <div role="status">
            <span className="sr-only">Loading your projects…</span>
            <div
                aria-hidden="true"
                className={
                    compact
                        ? "flex flex-col gap-3"
                        : "grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3"
                }
            >
                {[0, 1, 2, 3].map((item) =>
                    compact ? (
                        <div key={item} className="rounded-xl border border-border bg-card p-4">
                            <Skeleton className="h-4 w-20" />
                            <Skeleton className="mt-4 h-5 w-3/4" />
                            <Skeleton className="mt-3 h-4 w-32" />
                        </div>
                    ) : (
                        <div key={item}>
                            <Skeleton className="aspect-[16/10] w-full rounded-2xl" />
                            <Skeleton className="mt-3 h-5 w-3/4" />
                            <Skeleton className="mt-4 h-3 w-28" />
                        </div>
                    ),
                )}
            </div>
        </div>
    );
}
