import { serverAPI } from "decky";

type PluginMethod =
  | "settings_get"
  | "settings_set"
  | "story_generate"
  | "save_list"
  | "save_load"
  | "save_delete"
  | "save_create"
  | "tts_speak"
  | "verify_resources";

export interface StoryParams {
  genre: string;
  tone: string;
  keywords: string[];
  characters: string[];
  length: "short" | "medium" | "long";
  seed?: number;
}

export interface StoryChunk {
  done: boolean;
  text: string;
  error?: string;
}

export interface SaveEntry {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  size: number;
}

export interface Settings {
  mode: "offline" | "remote" | "template";
  model: {
    gguf_url: string;
    path: string;
    checksum?: string;
    ctx: number;
    temperature: number;
    top_p: number;
  };
  tts: {
    voice_url: string;
    path: string;
    checksum?: string;
    voice?: string;
    speed?: number;
  };
  remote: {
    enabled: boolean;
    endpoint: string;
    auth: string;
    timeout?: number;
  };
  status?: string;
}

async function callPlugin<T>(method: PluginMethod, args?: Record<string, unknown>): Promise<T> {
  const response = await serverAPI.callPluginMethod<T>(method, args ?? {});
  if (!response.success) {
    throw new Error(response.result as unknown as string ?? "Plugin call failed");
  }
  return response.result as T;
}

export const api = {
  async getSettings(): Promise<Settings> {
    return await callPlugin<Settings>("settings_get");
  },
  async setSettings(settings: Settings): Promise<Settings> {
    return await callPlugin<Settings>("settings_set", { settings });
  },
  async generateStory(params: StoryParams, onChunk: (chunk: StoryChunk) => void): Promise<void> {
    const iterator = await callPlugin<StoryChunk[]>("story_generate", { params });
    for (const chunk of iterator) {
      onChunk(chunk);
    }
  },
  async listSaves(): Promise<SaveEntry[]> {
    return await callPlugin<SaveEntry[]>("save_list");
  },
  async loadSave(id: string): Promise<{ content: string; metadata: SaveEntry } | null> {
    return await callPlugin<{ content: string; metadata: SaveEntry } | null>("save_load", { id });
  },
  async deleteSave(id: string): Promise<boolean> {
    return await callPlugin<boolean>("save_delete", { id });
  },
  async createSave(payload: { title: string; content: string; metadata?: Record<string, unknown> }): Promise<SaveEntry> {
    return await callPlugin<SaveEntry>("save_create", payload);
  },
  async speak(text: string, voice?: string): Promise<{ path: string } | null> {
    return await callPlugin<{ path: string } | null>("tts_speak", { text, voice });
  },
  async verifyResources(): Promise<{ status: string; details: string[] }> {
    return await callPlugin<{ status: string; details: string[] }>("verify_resources");
  },
};
