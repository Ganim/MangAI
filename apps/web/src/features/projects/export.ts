type BoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type ExportPageLike = {
  file_name: string;
  original_asset_path: string;
  active_cleaned_asset_path: string | null;
  width: number | null;
  height: number | null;
};

type ExportEntryLike = {
  text: string;
  placement: {
    text_box: BoundingBox;
    style: {
      font_family: string;
      font_fallbacks?: string[];
      font_size: number;
      leading: number;
      fill: string;
      alignment: string;
    };
  };
};

export function getPreferredExportAssetPath(page: ExportPageLike) {
  return page.active_cleaned_asset_path ?? page.original_asset_path;
}

export function buildJpegExportFileName(fileName: string) {
  const baseName = fileName.replace(/\.[^.]+$/, "");
  return `${baseName || "mangai-page"}-export.jpg`;
}

export function wrapTextForPlacement(text: string, boxWidth: number, fontSize: number) {
  const normalizedText = text.trim().replace(/\s+/g, " ");
  if (normalizedText.length === 0) {
    return [];
  }

  const approximateCharsPerLine = Math.max(6, Math.floor(boxWidth / Math.max(8, fontSize * 0.58)));
  const words = normalizedText.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    const nextLine = currentLine.length === 0 ? word : `${currentLine} ${word}`;
    if (nextLine.length <= approximateCharsPerLine) {
      currentLine = nextLine;
      continue;
    }
    if (currentLine.length > 0) {
      lines.push(currentLine);
    }
    currentLine = word;
  }

  if (currentLine.length > 0) {
    lines.push(currentLine);
  }

  return lines;
}

export async function exportPageAsJpeg(args: {
  imageSrc: string;
  fileName: string;
  width: number | null;
  height: number | null;
  entries: ExportEntryLike[];
}) {
  const image = await loadImage(args.imageSrc);
  const canvas = document.createElement("canvas");
  const width = args.width ?? image.naturalWidth ?? image.width;
  const height = args.height ?? image.naturalHeight ?? image.height;
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (context === null) {
    throw new Error("Canvas 2D context is not available.");
  }

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);

  for (const entry of args.entries) {
    drawPlacementText(context, entry);
  }

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((result) => {
      if (result === null) {
        reject(new Error("Could not serialize page export to JPEG."));
        return;
      }
      resolve(result);
    }, "image/jpeg", 0.92);
  });

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = args.fileName;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

function drawPlacementText(
  context: CanvasRenderingContext2D,
  entry: ExportEntryLike,
) {
  const box = entry.placement.text_box;
  const style = entry.placement.style;
  const lines = wrapTextForPlacement(entry.text, box.width, style.font_size);
  const fontStack = [style.font_family, ...(style.font_fallbacks ?? [])].join(", ");
  context.save();
  context.fillStyle = style.fill;
  context.font = `${style.font_size}px ${fontStack}`;
  context.textAlign = style.alignment === "left" ? "left" : style.alignment === "right" ? "right" : "center";
  context.textBaseline = "middle";

  const totalHeight = lines.length * style.leading;
  const centerX =
    style.alignment === "left"
      ? box.x + 8
      : style.alignment === "right"
        ? box.x + box.width - 8
        : box.x + box.width / 2;
  let cursorY = box.y + box.height / 2 - totalHeight / 2 + style.leading / 2;
  for (const line of lines) {
    context.fillText(line, centerX, cursorY, box.width - 12);
    cursorY += style.leading;
  }
  context.restore();
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not load page export asset."));
    image.src = src;
  });
}
