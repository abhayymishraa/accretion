import { Skeleton } from "@/components/ui/skeleton";

export function ProfileSkeleton() {
    return (
        <div role="status">
            <span className="sr-only">Loading your profile…</span>
            <div aria-hidden="true">
                <div className="border border-border bg-card">
                    <div className="grid sm:grid-cols-[minmax(0,1fr)_180px]">
                        <div className="p-6 sm:p-8">
                            <Skeleton className="h-12 w-64 max-w-full rounded-none" />
                            <Skeleton className="mt-5 h-4 w-80 max-w-full" />
                            <Skeleton className="mt-3 h-4 w-60 max-w-full" />
                            <Skeleton className="mt-7 h-11 w-32 rounded-none" />
                        </div>
                        <div className="hidden flex-col justify-between border-l border-border bg-surface-2 p-6 sm:flex">
                            <Skeleton className="h-3 w-28" />
                            <Skeleton className="h-20 w-full rounded-none" />
                        </div>
                    </div>
                    <div className="grid border-t border-border sm:grid-cols-[minmax(0,1fr)_180px]">
                        <div className="px-6 py-5 sm:px-8">
                            <Skeleton className="h-3 w-24" />
                            <Skeleton className="mt-3 h-4 w-56 max-w-full" />
                        </div>
                        <div className="border-t border-border px-6 py-5 sm:border-t-0 sm:border-l">
                            <Skeleton className="h-3 w-24" />
                            <Skeleton className="mt-3 h-4 w-28" />
                        </div>
                    </div>
                </div>
                <div className="mt-9 grid gap-8 md:grid-cols-2 md:gap-12">
                    <div>
                        <Skeleton className="h-5 w-28" />
                        <Skeleton className="mt-4 h-9 w-36" />
                        <Skeleton className="mt-3 h-4 w-60 max-w-full" />
                    </div>
                    <div>
                        <Skeleton className="h-5 w-36" />
                        <Skeleton className="mt-3 h-4 w-48" />
                        <div className="mt-5 space-y-3">
                            {[0, 1, 2].map((item) => (
                                <Skeleton key={item} className="h-16 w-full" />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
