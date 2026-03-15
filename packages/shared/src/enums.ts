export const SCHEMA_VERSION = 1;

export const SUPPORTED_UI_LOCALES = ["en-US", "pt-BR"] as const;
export const SUPPORTED_SOURCE_LANGUAGE_CODES = ["ja", "ko", "zh", "en"] as const;
export const SUPPORTED_TARGET_LANGUAGE_CODES = ["pt", "en"] as const;

export const ProjectStatus = ["draft", "active", "archived"] as const;
export const PageStatus = [
  "uploaded",
  "analyzed",
  "cleanup_ready",
  "cleaned",
  "text_ready",
  "typeset_ready",
  "export_ready",
  "error",
] as const;
export const RegionType = ["speech_balloon", "narration_box", "free_text", "sfx", "unknown"] as const;
export const RegionOrigin = ["detected", "user_created", "user_split", "user_merged"] as const;
export const RegionState = ["draft", "reviewed", "approved", "rejected"] as const;
export const DialogueSource = ["ocr", "manual", "imported_script"] as const;
export const DialogueStatus = ["draft", "reviewed", "approved", "rejected"] as const;
export const TranslationStatus = ["draft", "reviewed", "approved"] as const;
export const AssignmentOrigin = ["automatic", "manual"] as const;
export const TextDirection = ["ltr", "rtl", "ttb"] as const;
export const JobType = [
  "detect_regions",
  "generate_cleanup",
  "run_ocr",
  "generate_translation",
  "match_dialogue",
  "generate_typesetting",
  "export_project",
] as const;
export const JobStatus = ["queued", "running", "succeeded", "failed", "canceled"] as const;
export const ExportFormat = ["jpg", "psd", "pdf"] as const;
export const AssetKind = [
  "original",
  "overlay",
  "mask",
  "cleaned",
  "cleanup_variant",
  "ocr_preview",
  "export",
] as const;

export const RTL_LANGUAGE_CODES = ["ar", "fa", "he", "ur"] as const;

export function isEnumValue<T extends readonly string[]>(
  value: unknown,
  allowedValues: T,
): value is T[number] {
  return typeof value === "string" && allowedValues.includes(value as T[number]);
}
