type PageJobLike = {
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
};

const ACTIVE_JOB_STATUSES = new Set<PageJobLike["status"]>(["queued", "running"]);

export function hasPendingPageJobs(jobs: ReadonlyArray<PageJobLike>) {
  return jobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));
}
