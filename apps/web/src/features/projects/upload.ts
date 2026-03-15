import { parseRegisterProjectPagesRequest } from "@mangai/shared";

export const SUPPORTED_UPLOAD_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export const MAX_UPLOAD_FILE_SIZE_BYTES = 25 * 1024 * 1024;

export type UploadFileLike = {
  name: string;
  type: string;
  size: number;
};

export type UploadQueueItem = {
  client_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
};

export type UploadQueueRejection = {
  file_name: string;
  reason: "unsupported_type" | "too_large" | "duplicate_name";
};

const fileNameCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

export function createUploadQueue(files: readonly UploadFileLike[]): {
  accepted: UploadQueueItem[];
  rejected: UploadQueueRejection[];
} {
  const accepted: UploadQueueItem[] = [];
  const rejected: UploadQueueRejection[] = [];
  const seenNames = new Set<string>();

  const sortedFiles = [...files].sort((left, right) => fileNameCollator.compare(left.name, right.name));

  for (const [index, file] of sortedFiles.entries()) {
    const normalizedName = file.name.trim().toLowerCase();
    if (!SUPPORTED_UPLOAD_MIME_TYPES.includes(file.type as (typeof SUPPORTED_UPLOAD_MIME_TYPES)[number])) {
      rejected.push({
        file_name: file.name,
        reason: "unsupported_type",
      });
      continue;
    }

    if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
      rejected.push({
        file_name: file.name,
        reason: "too_large",
      });
      continue;
    }

    if (seenNames.has(normalizedName)) {
      rejected.push({
        file_name: file.name,
        reason: "duplicate_name",
      });
      continue;
    }

    seenNames.add(normalizedName);
    accepted.push({
      client_id: `${normalizedName}-${index + 1}-${file.size}`,
      file_name: file.name,
      mime_type: file.type,
      size_bytes: file.size,
      width: null,
      height: null,
    });
  }

  return { accepted, rejected };
}

export function removeUploadQueueItem(
  queue: readonly UploadQueueItem[],
  clientId: string,
): UploadQueueItem[] {
  return queue.filter((item) => item.client_id !== clientId);
}

export function buildRegisterPagesPayload(queue: readonly UploadQueueItem[]) {
  return parseRegisterProjectPagesRequest({
    pages: queue.map((item) => ({
      file_name: item.file_name,
      mime_type: item.mime_type,
      size_bytes: item.size_bytes,
      width: item.width,
      height: item.height,
    })),
  });
}

export function formatBytes(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}
