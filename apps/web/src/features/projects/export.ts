import { buildPdfBinary } from "./pdf.ts";
import { buildPsdBinary } from "./psd.ts";

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

export function buildPdfExportFileName(fileName: string) {
  const baseName = fileName.replace(/\.[^.]+$/, "");
  return `${baseName || "mangai-page"}-export.pdf`;
}

export function buildPsdExportFileName(fileName: string) {
  const baseName = fileName.replace(/\.[^.]+$/, "");
  return `${baseName || "mangai-page"}-export.psd`;
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
  const canvases = await renderExportCanvases({
    artworkSrc: args.imageSrc,
    originalSrc: args.imageSrc,
    width: args.width,
    height: args.height,
    entries: args.entries,
  });
  const blob = await canvasToBlob(canvases.compositeCanvas, "image/jpeg", 0.92);
  downloadBlob(blob, args.fileName);
}

export async function exportPageAsPdf(args: {
  imageSrc: string;
  fileName: string;
  width: number | null;
  height: number | null;
  entries: ExportEntryLike[];
}) {
  const canvases = await renderExportCanvases({
    artworkSrc: args.imageSrc,
    originalSrc: args.imageSrc,
    width: args.width,
    height: args.height,
    entries: args.entries,
  });
  const jpegBlob = await canvasToBlob(canvases.compositeCanvas, "image/jpeg", 0.92);
  const pdfBytes = buildPdfBinary({
    width: canvases.compositeCanvas.width,
    height: canvases.compositeCanvas.height,
    jpegBytes: new Uint8Array(await jpegBlob.arrayBuffer()),
  });
  downloadBlob(new Blob([pdfBytes], { type: "application/pdf" }), args.fileName);
}

export async function exportPageAsPsd(args: {
  originalImageSrc: string;
  workingImageSrc: string;
  fileName: string;
  width: number | null;
  height: number | null;
  entries: ExportEntryLike[];
}) {
  const canvases = await renderExportCanvases({
    artworkSrc: args.workingImageSrc,
    originalSrc: args.originalImageSrc,
    width: args.width,
    height: args.height,
    entries: args.entries,
  });
  const psdBytes = buildPsdBinary({
    width: canvases.compositeCanvas.width,
    height: canvases.compositeCanvas.height,
    compositeRgba: readCanvasRgba(canvases.compositeCanvas),
    layers: [
      {
        name: "Original",
        width: canvases.originalCanvas.width,
        height: canvases.originalCanvas.height,
        rgba: readCanvasRgba(canvases.originalCanvas),
      },
      {
        name: "Artwork",
        width: canvases.artworkCanvas.width,
        height: canvases.artworkCanvas.height,
        rgba: readCanvasRgba(canvases.artworkCanvas),
      },
      {
        name: "Translation",
        width: canvases.textCanvas.width,
        height: canvases.textCanvas.height,
        rgba: readCanvasRgba(canvases.textCanvas),
      },
    ],
  });
  downloadBlob(new Blob([psdBytes], { type: "image/vnd.adobe.photoshop" }), args.fileName);
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

async function renderExportCanvases(args: {
  artworkSrc: string;
  originalSrc: string;
  width: number | null;
  height: number | null;
  entries: ExportEntryLike[];
}) {
  const [artworkImage, originalImage] = await Promise.all([
    loadImage(args.artworkSrc),
    loadImage(args.originalSrc),
  ]);
  const width = args.width ?? artworkImage.naturalWidth ?? artworkImage.width;
  const height = args.height ?? artworkImage.naturalHeight ?? artworkImage.height;

  const originalCanvas = createSizedCanvas(width, height);
  const artworkCanvas = createSizedCanvas(width, height);
  const textCanvas = createSizedCanvas(width, height);
  const compositeCanvas = createSizedCanvas(width, height);

  const originalContext = require2dContext(originalCanvas);
  const artworkContext = require2dContext(artworkCanvas);
  const textContext = require2dContext(textCanvas);
  const compositeContext = require2dContext(compositeCanvas);

  originalContext.fillStyle = "#ffffff";
  originalContext.fillRect(0, 0, width, height);
  originalContext.drawImage(originalImage, 0, 0, width, height);

  artworkContext.fillStyle = "#ffffff";
  artworkContext.fillRect(0, 0, width, height);
  artworkContext.drawImage(artworkImage, 0, 0, width, height);

  for (const entry of args.entries) {
    drawPlacementText(textContext, entry);
  }

  compositeContext.fillStyle = "#ffffff";
  compositeContext.fillRect(0, 0, width, height);
  compositeContext.drawImage(artworkCanvas, 0, 0);
  compositeContext.drawImage(textCanvas, 0, 0);

  return {
    originalCanvas,
    artworkCanvas,
    textCanvas,
    compositeCanvas,
  };
}

function createSizedCanvas(width: number, height: number) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function require2dContext(canvas: HTMLCanvasElement) {
  const context = canvas.getContext("2d");
  if (context === null) {
    throw new Error("Canvas 2D context is not available.");
  }
  return context;
}

function readCanvasRgba(canvas: HTMLCanvasElement) {
  return require2dContext(canvas).getImageData(0, 0, canvas.width, canvas.height).data;
}

async function canvasToBlob(
  canvas: HTMLCanvasElement,
  mimeType: string,
  quality?: number,
) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((result) => {
      if (result === null) {
        reject(new Error(`Could not serialize export to ${mimeType}.`));
        return;
      }
      resolve(result);
    }, mimeType, quality);
  });
}

function downloadBlob(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}
