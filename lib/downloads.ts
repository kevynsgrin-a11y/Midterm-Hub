import manifest from "@/generated/downloads-manifest.json";

export type DownloadFile = {
  name: string;
  format: "JSON" | "CSV" | "ICS";
  description: string;
  bytes: number;
  sha256: string;
  records: number;
};

/** The open-data files written next to the site by the release build (see scripts/build-frontend-data.py). */
export const downloads = manifest.files as DownloadFile[];

/** Static files are not rewritten by next/link, so the base path (empty on midtermwatch.com) is added here. */
export const downloadHref = (name: string, base: string = process.env.NEXT_PUBLIC_BASE_PATH ?? "") => `${base}/downloads/${name}`;

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
