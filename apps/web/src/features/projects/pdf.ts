type PdfDocumentInput = {
  width: number;
  height: number;
  jpegBytes: Uint8Array;
};

export function buildPdfBinary(input: PdfDocumentInput) {
  const objects: Uint8Array[] = [];
  objects.push(encodeAscii("<< /Type /Catalog /Pages 2 0 R >>"));
  objects.push(encodeAscii("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"));
  objects.push(
    encodeAscii(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${input.width} ${input.height}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`,
    ),
  );
  objects.push(
    concatUint8Arrays([
      encodeAscii(
        `<< /Type /XObject /Subtype /Image /Width ${input.width} /Height ${input.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${input.jpegBytes.length} >>\nstream\n`,
      ),
      input.jpegBytes,
      encodeAscii("\nendstream"),
    ]),
  );
  const contents = encodeAscii(`q\n${input.width} 0 0 ${input.height} 0 0 cm\n/Im0 Do\nQ\n`);
  objects.push(
    concatUint8Arrays([
      encodeAscii(`<< /Length ${contents.length} >>\nstream\n`),
      contents,
      encodeAscii("endstream"),
    ]),
  );

  return buildPdfFile(objects);
}

function buildPdfFile(objects: Uint8Array[]) {
  const header = encodeAscii("%PDF-1.4\n");
  const chunks: Uint8Array[] = [header];
  const offsets: number[] = [0];
  let currentOffset = header.length;

  objects.forEach((objectBytes, index) => {
    offsets.push(currentOffset);
    const objectHeader = encodeAscii(`${index + 1} 0 obj\n`);
    const objectFooter = encodeAscii("\nendobj\n");
    chunks.push(objectHeader, objectBytes, objectFooter);
    currentOffset += objectHeader.length + objectBytes.length + objectFooter.length;
  });

  const xrefOffset = currentOffset;
  const xrefHeader = encodeAscii(`xref\n0 ${objects.length + 1}\n`);
  chunks.push(xrefHeader);
  currentOffset += xrefHeader.length;

  for (const offset of offsets) {
    const line = encodeAscii(`${offset.toString().padStart(10, "0")} 00000 ${offset === 0 ? "f" : "n"} \n`);
    chunks.push(line);
    currentOffset += line.length;
  }

  const trailer = encodeAscii(
    `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`,
  );
  chunks.push(trailer);
  return concatUint8Arrays(chunks);
}

function encodeAscii(value: string) {
  return new TextEncoder().encode(value);
}

function concatUint8Arrays(chunks: Uint8Array[]) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.length;
  }
  return output;
}
