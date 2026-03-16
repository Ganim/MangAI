type PsdLayerInput = {
  name: string;
  width: number;
  height: number;
  rgba: Uint8ClampedArray;
  opacity?: number;
};

type PsdDocumentInput = {
  width: number;
  height: number;
  compositeRgba: Uint8ClampedArray;
  layers: PsdLayerInput[];
};

type LayerChannelData = {
  id: number;
  data: Uint8Array;
};

export function buildPsdBinary(input: PsdDocumentInput) {
  const writer = new BinaryWriter();
  writer.writeAscii("8BPS");
  writer.writeUint16(1);
  writer.writeBytes(new Uint8Array(6));
  writer.writeUint16(4);
  writer.writeUint32(input.height);
  writer.writeUint32(input.width);
  writer.writeUint16(8);
  writer.writeUint16(3);

  writer.writeUint32(0);
  writer.writeUint32(0);

  const layerInfoData = buildLayerInfoSection(input.layers);
  const globalMaskInfo = new Uint8Array(4);
  const layerAndMaskSection = concatUint8Arrays([
    encodeUint32(layerInfoData.length),
    layerInfoData,
    globalMaskInfo,
  ]);
  writer.writeUint32(layerAndMaskSection.length);
  writer.writeBytes(layerAndMaskSection);

  writer.writeUint16(0);
  writer.writeBytes(extractPlanarChannels(input.compositeRgba));
  return writer.toUint8Array();
}

function buildLayerInfoSection(layers: PsdLayerInput[]) {
  const recordWriter = new BinaryWriter();
  recordWriter.writeInt16(layers.length);

  const channelPayloads: Uint8Array[] = [];

  for (const layer of layers) {
    const channels = buildLayerChannels(layer);
    recordWriter.writeInt32(0);
    recordWriter.writeInt32(0);
    recordWriter.writeInt32(layer.height);
    recordWriter.writeInt32(layer.width);
    recordWriter.writeUint16(channels.length);
    for (const channel of channels) {
      recordWriter.writeInt16(channel.id);
      recordWriter.writeUint32(channel.data.length + 2);
      channelPayloads.push(concatUint8Arrays([encodeUint16(0), channel.data]));
    }
    recordWriter.writeAscii("8BIM");
    recordWriter.writeAscii("norm");
    recordWriter.writeUint8(layer.opacity ?? 255);
    recordWriter.writeUint8(0);
    recordWriter.writeUint8(0);
    recordWriter.writeUint8(0);

    const extraWriter = new BinaryWriter();
    extraWriter.writeUint32(0);
    extraWriter.writeUint32(0);
    extraWriter.writeBytes(encodePascalString(layer.name));
    const extraData = extraWriter.toUint8Array();
    recordWriter.writeUint32(extraData.length);
    recordWriter.writeBytes(extraData);
  }

  let layerInfoBody = concatUint8Arrays([recordWriter.toUint8Array(), ...channelPayloads]);
  if (layerInfoBody.length % 2 === 1) {
    layerInfoBody = concatUint8Arrays([layerInfoBody, new Uint8Array([0])]);
  }
  return layerInfoBody;
}

function buildLayerChannels(layer: PsdLayerInput): LayerChannelData[] {
  const planar = extractPlanarChannels(layer.rgba);
  const channelSize = layer.width * layer.height;
  return [
    { id: 0, data: planar.slice(0, channelSize) },
    { id: 1, data: planar.slice(channelSize, channelSize * 2) },
    { id: 2, data: planar.slice(channelSize * 2, channelSize * 3) },
    { id: -1, data: planar.slice(channelSize * 3, channelSize * 4) },
  ];
}

function extractPlanarChannels(rgba: Uint8ClampedArray) {
  const pixelCount = rgba.length / 4;
  const red = new Uint8Array(pixelCount);
  const green = new Uint8Array(pixelCount);
  const blue = new Uint8Array(pixelCount);
  const alpha = new Uint8Array(pixelCount);

  for (let index = 0; index < pixelCount; index += 1) {
    const offset = index * 4;
    red[index] = rgba[offset] ?? 0;
    green[index] = rgba[offset + 1] ?? 0;
    blue[index] = rgba[offset + 2] ?? 0;
    alpha[index] = rgba[offset + 3] ?? 0;
  }

  return concatUint8Arrays([red, green, blue, alpha]);
}

function encodePascalString(value: string) {
  const encoded = new TextEncoder().encode(value.slice(0, 255));
  const length = encoded.length;
  const base = new Uint8Array(1 + length);
  base[0] = length;
  base.set(encoded, 1);
  const remainder = base.length % 4;
  if (remainder === 0) {
    return base;
  }
  return concatUint8Arrays([base, new Uint8Array(4 - remainder)]);
}

function encodeUint16(value: number) {
  const buffer = new Uint8Array(2);
  new DataView(buffer.buffer).setUint16(0, value, false);
  return buffer;
}

function encodeUint32(value: number) {
  const buffer = new Uint8Array(4);
  new DataView(buffer.buffer).setUint32(0, value, false);
  return buffer;
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

class BinaryWriter {
  private readonly chunks: Uint8Array[] = [];

  writeAscii(value: string) {
    this.chunks.push(new TextEncoder().encode(value));
  }

  writeBytes(value: Uint8Array) {
    this.chunks.push(value);
  }

  writeUint8(value: number) {
    this.chunks.push(Uint8Array.of(value & 0xff));
  }

  writeUint16(value: number) {
    this.chunks.push(encodeUint16(value));
  }

  writeUint32(value: number) {
    this.chunks.push(encodeUint32(value));
  }

  writeInt16(value: number) {
    const buffer = new Uint8Array(2);
    new DataView(buffer.buffer).setInt16(0, value, false);
    this.chunks.push(buffer);
  }

  writeInt32(value: number) {
    const buffer = new Uint8Array(4);
    new DataView(buffer.buffer).setInt32(0, value, false);
    this.chunks.push(buffer);
  }

  toUint8Array() {
    return concatUint8Arrays(this.chunks);
  }
}
