type PageJobLike = {
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
};

const ACTIVE_JOB_STATUSES = new Set<PageJobLike["status"]>(["queued", "running"]);
const QUEUED_JOB_STATUSES = new Set<PageJobLike["status"]>(["queued"]);
const RUNNING_JOB_STATUSES = new Set<PageJobLike["status"]>(["running"]);

export function hasPendingPageJobs(jobs: ReadonlyArray<PageJobLike>) {
  return jobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));
}

export function hasQueuedPageJobs(jobs: ReadonlyArray<PageJobLike>) {
  return jobs.some((job) => QUEUED_JOB_STATUSES.has(job.status));
}

export function hasRunningPageJobs(jobs: ReadonlyArray<PageJobLike>) {
  return jobs.some((job) => RUNNING_JOB_STATUSES.has(job.status));
}
