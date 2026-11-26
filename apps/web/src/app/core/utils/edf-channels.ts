const EEG = ['EEG Fpz-Cz', 'EEG Pz-Oz'];
const EMG = 'EMG submental';
const MODEL_CHANNELS = [...EEG, 'EOG horizontal', EMG];

export interface EdfChannel {
  name: string;
  hz: number;
  selectable: boolean;
  reason?: string;
}

export function hasEeg(channels: string[]): boolean {
  return channels.some((name) => EEG.includes(name));
}

function readHeaderPart(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new TextDecoder('latin1').decode(reader.result as ArrayBuffer));
    reader.onerror = () => reject(new Error('No se pudo leer el archivo.'));
    reader.readAsArrayBuffer(blob);
  });
}

export async function readEdfChannels(file: File): Promise<EdfChannel[]> {
  // Los campos de la cabecera EDF tienen posiciones y anchos fijos en bytes.
  const header = await readHeaderPart(file.slice(0, 256));
  const count = Number(header.slice(252, 256).trim());
  const duration = Number(header.slice(244, 252).trim());
  const headerBytes = 256 + 256 * count;
  if (header.length !== 256 || header.slice(0, 8).trim() !== '0' ||
      !Number.isInteger(count) || count < 1 || !Number.isFinite(duration) || duration <= 0 ||
      Number(header.slice(184, 192)) !== headerBytes || file.size <= headerBytes) {
    throw new Error('La cabecera EDF es inválida o está incompleta.');
  }
  const signals = await readHeaderPart(file.slice(256, headerBytes));
  const channels: EdfChannel[] = [];
  let samplesPerRecord = 0;
  for (let i = 0; i < count; i++) {
    const name = signals.slice(i * 16, (i + 1) * 16).trim();
    const offset = 216 * count + 8 * i;
    const samples = Number(signals.slice(offset, offset + 8).trim());
    if (!Number.isInteger(samples) || samples < 1) {
      throw new Error('La cabecera EDF contiene una frecuencia inválida.');
    }
    samplesPerRecord += samples;
    if (name === 'EDF Annotations') continue;
    const hz = samples / duration;
    let reason: string | undefined;
    if (!MODEL_CHANNELS.includes(name)) reason = 'Fuera del modelo';
    else if (hz !== 100 && !(name === EMG && hz === 1)) reason = 'Frecuencia incompatible';
    const duplicate = channels.find((channel) => channel.name === name);
    if (duplicate) {
      duplicate.selectable = false;
      duplicate.reason = 'Etiqueta repetida';
    } else {
      channels.push({ name, hz, selectable: !reason, reason });
    }
  }
  const records = (file.size - headerBytes) / (2 * samplesPerRecord);
  const declared = Number(header.slice(236, 244).trim());
  if (!Number.isInteger(records) || (declared !== -1 && declared !== records)) {
    throw new Error('El tamaño del EDF no coincide con su cabecera.');
  }
  if (records * duration < 30) throw new Error('El EDF debe contener al menos 30 segundos.');
  return channels;
}
