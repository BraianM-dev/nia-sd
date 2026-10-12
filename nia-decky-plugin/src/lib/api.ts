import { callable } from "@decky/api";

export type Provider = "ollama" | "openai-compatible" | "template";
export type Persona = "amable" | "sarcastico" | "grosero" | "epico";
export type GameEventType = "death" | "checkpoint" | "objective" | "victory" | "commentary";

export interface NarratorSettings {
  provider: Provider; endpoint: string; model: string; api_key: string;
  timeout: number; max_tokens: number; temperature: number; persona: Persona;
  auto_on_start: boolean; auto_speak: boolean;
}
export interface Settings {
  mode: "offline" | "remote" | "template";
  model: { gguf_url: string; path: string; checksum?: string; ctx: number; temperature: number; top_p: number };
  tts: { enabled: boolean; piper_binary: string; voice_model: string; path: string; voice_url: string; checksum?: string; voice?: string; speed: number };
  remote: { enabled: boolean; endpoint: string; auth: string; timeout?: number };
  narrator: NarratorSettings;
  game_detection: { enabled: boolean; scan_interval_seconds: number; roots: string[] };
  status?: string;
}
export interface GameInfo { id: string; appid?: string; title: string; platform: string; install_path?: string; process_name?: string }
export interface GameState {
  active_game: GameInfo | null;
  stats?: { deaths: number; checkpoints: number; objectives: number; victories: number; sessions: number };
  session_minutes?: number;
  latest_narration?: { event_type: string; text: string; created_at: number } | null;
  message?: string;
  scanned_at: number;
}
export interface NarrationResult { text: string; status: string; game_id?: string; event_type?: string; source?: string }
export interface StoryParams {
  genre: string; tone: string; keywords: string[]; characters: string[];
  length: "short" | "medium" | "long"; seed?: number;
}
export interface StoryChunk { done: boolean; text: string; error?: string }
export interface SaveEntry { id: string; title: string; created_at: string; updated_at: string; size: number }

const settingsGet = callable<[], Settings>("settings_get");
const settingsSet = callable<[settings: Settings], Settings>("settings_set");
const gamesList = callable<[], GameInfo[]>("list_games");
const gameState = callable<[], GameState>("game_state");
const gameEvent = callable<[eventType: GameEventType, detail: string], NarrationResult>("game_event");
const generateCommentary = callable<[], NarrationResult>("narrator_generate");
const storyGenerate = callable<[params: StoryParams], StoryChunk[]>("story_generate");
const saveList = callable<[], SaveEntry[]>("save_list");
const saveLoad = callable<[id: string], { content: string; metadata: SaveEntry } | null>("save_load");
const saveDelete = callable<[id: string], boolean>("save_delete");
const saveCreate = callable<[title: string, content: string, metadata?: Record<string, unknown>], SaveEntry>("save_create");
const speak = callable<[text: string, voice?: string], { playing: boolean; player: string }>("tts_speak");
const verifyResources = callable<[], { status: string; details: string[] }>("verify_resources");

export const api = {
  getSettings: () => settingsGet(),
  setSettings: (settings: Settings) => settingsSet(settings),
  listGames: () => gamesList(),
  getGameState: () => gameState(),
  recordGameEvent: (eventType: GameEventType, detail = "") => gameEvent(eventType, detail),
  generateCommentary: () => generateCommentary(),
  async generateStory(params: StoryParams, onChunk: (chunk: StoryChunk) => void): Promise<void> {
    for (const chunk of await storyGenerate(params)) onChunk(chunk);
  },
  listSaves: () => saveList(),
  loadSave: (id: string) => saveLoad(id),
  deleteSave: (id: string) => saveDelete(id),
  createSave: (payload: { title: string; content: string; metadata?: Record<string, unknown> }) =>
    saveCreate(payload.title, payload.content, payload.metadata),
  speak: (text: string, voice?: string) => speak(text, voice),
  verifyResources: () => verifyResources(),
};
