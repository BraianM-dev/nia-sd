import { StoryParams } from "./api";

const GENRES = [
  "fantasía",
  "ciencia ficción",
  "misterio",
  "aventura",
  "terror",
  "histórico"
];

export function getGenres() {
  return GENRES;
}

export function sanitizeList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
    .slice(0, 10);
}

export function validateStoryParams(params: StoryParams): string | null {
  if (!GENRES.includes(params.genre)) {
    return "Selecciona un género válido";
  }
  if (params.tone.trim().length === 0) {
    return "El tono no puede estar vacío";
  }
  if (params.length === "long" && params.keywords.length > 20) {
    return "Demasiadas palabras clave";
  }
  return null;
}

export function clampSeed(seed?: number): number | undefined {
  if (seed === undefined || Number.isNaN(seed)) {
    return undefined;
  }
  const n = Math.max(0, Math.min(1_000_000, Math.floor(seed)));
  return n;
}

export function readableSize(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let idx = 0;
  let value = size;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[idx]}`;
}
