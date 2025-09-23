import React, { useEffect, useRef, useState } from "react";
import {
  ButtonItem,
  ConfirmModal,
  Field,
  Focusable,
  FormDivider,
  PanelSection,
  PanelSectionRow,
  QuickAccessTab,
  Router,
  Spinner,
  TextField,
  ToggleField,
  definePlugin,
  showModal,
} from "decky";
import { serverAPI } from "decky";

const GENRES = ["fantasía", "ciencia ficción", "misterio", "aventura", "terror", "histórico"];

function sanitizeList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
    .slice(0, 10);
}

function clampSeed(seed) {
  if (seed === undefined || seed === null || Number.isNaN(seed)) {
    return undefined;
  }
  const n = Math.max(0, Math.min(1_000_000, Math.floor(seed)));
  return n;
}

function validateStoryParams(params) {
  if (!GENRES.includes(params.genre)) {
    return "Selecciona un género válido";
  }
  if (!params.tone.trim()) {
    return "El tono no puede estar vacío";
  }
  if (params.length === "long" && params.keywords.length > 20) {
    return "Demasiadas palabras clave";
  }
  return null;
}

async function callPlugin(method, args) {
  const response = await serverAPI.callPluginMethod(method, args ?? {});
  if (!response.success) {
    throw new Error(response.result ?? "Plugin call failed");
  }
  return response.result;
}

const api = {
  getSettings: () => callPlugin("settings_get"),
  setSettings: (settings) => callPlugin("settings_set", { settings }),
  generateStory: (params) => callPlugin("story_generate", { params }),
  listSaves: () => callPlugin("save_list"),
  loadSave: (id) => callPlugin("save_load", { id }),
  deleteSave: (id) => callPlugin("save_delete", { id }),
  createSave: (payload) => callPlugin("save_create", payload),
  speak: (text, voice) => callPlugin("tts_speak", { text, voice }),
  verifyResources: () => callPlugin("verify_resources"),
};

function Controls({ disabled, onGenerate }) {
  const [genre, setGenre] = useState(GENRES[0]);
  const [tone, setTone] = useState("Épico, envolvente");
  const [keywordsText, setKeywordsText] = useState("");
  const [charactersText, setCharactersText] = useState("");
  const [length, setLength] = useState("medium");
  const [seed, setSeed] = useState("");
  const [error, setError] = useState(null);

  const submit = () => {
    const params = {
      genre,
      tone,
      keywords: sanitizeList(keywordsText),
      characters: sanitizeList(charactersText),
      length,
      seed: clampSeed(seed ? Number(seed) : undefined),
    };
    const validation = validateStoryParams(params);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    onGenerate(params);
  };

  return (
    <Focusable flow-children="down" style={{ gap: "12px" }}>
      <Field label="Género" description="Selecciona el estilo base de la historia" childrenContainerWidth="full">
        <div className="decky-select">
          <select
            className="DeckySelectable"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            disabled={disabled}
          >
            {GENRES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      </Field>
      <TextField
        label="Tono"
        description="Describe la atmósfera que deseas"
        value={tone}
        onChange={(e) => setTone(e.target.value)}
        disabled={disabled}
      />
      <TextField
        label="Palabras clave"
        description="Separa con comas"
        value={keywordsText}
        onChange={(e) => setKeywordsText(e.target.value)}
        disabled={disabled}
      />
      <TextField
        label="Personajes"
        description="Nombres o roles principales"
        value={charactersText}
        onChange={(e) => setCharactersText(e.target.value)}
        disabled={disabled}
      />
      <Field label="Longitud">
        <div className="decky-select">
          <select
            className="DeckySelectable"
            value={length}
            onChange={(e) => setLength(e.target.value)}
            disabled={disabled}
          >
            <option value="short">Corta</option>
            <option value="medium">Media</option>
            <option value="long">Larga</option>
          </select>
        </div>
      </Field>
      <TextField
        label="Semilla (opcional)"
        description="Número para reproducibilidad"
        value={seed}
        onChange={(e) => setSeed(e.target.value)}
        disabled={disabled}
      />
      {error && <div style={{ color: "var(--color-error)", fontSize: "14px" }}>{error}</div>}
      <FormDivider />
      <ButtonItem disabled={disabled} layout="below" onClick={submit}>
        {disabled ? "Generando..." : "Generar"}
      </ButtonItem>
    </Focusable>
  );
}

function OutputView({ text, isGenerating, onSpeak, onClear, onSave, onContinue, statusMessage }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [text]);

  return (
    <PanelSection title="Narrativa generada">
      <PanelSectionRow>
        <Focusable flow-children="down" style={{ gap: "8px", width: "100%" }}>
          <div
            ref={scrollRef}
            style={{
              maxHeight: "320px",
              overflowY: "auto",
              backgroundColor: "rgba(255,255,255,0.04)",
              padding: "12px",
              borderRadius: "8px",
              lineHeight: 1.5,
              fontSize: "16px",
            }}
          >
            {text ? text : isGenerating ? "Generando historia..." : "Aquí aparecerá la historia."}
            {isGenerating && <Spinner style={{ marginTop: "8px" }} />}
          </div>
          {statusMessage && <div style={{ fontSize: "13px", opacity: 0.7 }}>{statusMessage}</div>}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <ButtonItem onClick={onSpeak} disabled={!text}>
              ► Narrar
            </ButtonItem>
            <ButtonItem onClick={onSave} disabled={!text}>
              Guardar
            </ButtonItem>
            <ButtonItem onClick={onContinue} disabled={!text || isGenerating}>
              Continuar historia
            </ButtonItem>
            <ButtonItem onClick={onClear} disabled={!text && !statusMessage}>
              Reiniciar
            </ButtonItem>
          </div>
        </Focusable>
      </PanelSectionRow>
    </PanelSection>
  );
}

function readableSize(size) {
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

function SavesView({ onLoad }) {
  const [saves, setSaves] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const result = await api.listSaves();
      setSaves(result);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("No se pudieron cargar las partidas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const loadSave = async (id) => {
    try {
      const result = await api.loadSave(id);
      if (result) {
        onLoad(result.content);
      }
    } catch (err) {
      console.error(err);
      setError("Error al cargar la partida");
    }
  };

  const deleteSave = (entry) => {
    showModal(
      <ConfirmModal
        onCancel={() => null}
        onOK={async () => {
          try {
            await api.deleteSave(entry.id);
            refresh();
          } catch (err) {
            console.error(err);
            setError("No se pudo borrar la partida");
          }
        }}
        strTitle="¿Eliminar partida?"
        strDescription={`Se borrará "${entry.title}" permanentemente.`}
      />
    );
  };

  return (
    <PanelSection title="Partidas guardadas">
      <PanelSectionRow>
        <Focusable flow-children="down" style={{ gap: "8px", width: "100%" }}>
          <QuickAccessTab title="Actualizar" onClick={refresh} icon="steamdeck" buttonClassName="DeckyButton" />
          {loading && <div>Cargando...</div>}
          {error && <div style={{ color: "var(--color-error)" }}>{error}</div>}
          {saves.length === 0 && !loading && <div>No hay partidas guardadas.</div>}
          {saves.map((save) => (
            <div
              key={save.id}
              style={{
                backgroundColor: "rgba(255,255,255,0.05)",
                padding: "10px",
                borderRadius: "6px",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <div style={{ fontWeight: 600 }}>{save.title}</div>
              <div style={{ fontSize: "12px", opacity: 0.7 }}>
                {new Date(save.updated_at).toLocaleString()} · {readableSize(save.size)}
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <ButtonItem onClick={() => loadSave(save.id)}>Cargar</ButtonItem>
                <ButtonItem onClick={() => deleteSave(save)}>Eliminar</ButtonItem>
              </div>
            </div>
          ))}
        </Focusable>
      </PanelSectionRow>
    </PanelSection>
  );
}

function SettingsViewWrapper({ settings, onSettingsChange }) {
  const [working, setWorking] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    setStatus(settings?.status ?? "");
  }, [settings]);

  if (!settings) {
    return <div>Cargando ajustes...</div>;
  }

  const verifyResources = async () => {
    setWorking(true);
    try {
      const result = await api.verifyResources();
      setStatus(result.status + ": " + result.details.join(" · "));
    } catch (err) {
      console.error(err);
      setStatus("Error al verificar recursos");
    } finally {
      setWorking(false);
    }
  };

  const persist = async () => {
    setWorking(true);
    try {
      const saved = await api.setSettings(settings);
      onSettingsChange(saved);
      setStatus("Ajustes guardados");
    } catch (err) {
      console.error(err);
      setStatus("No se pudieron guardar los ajustes");
    } finally {
      setWorking(false);
    }
  };

  return (
    <PanelSection title="Ajustes">
      <PanelSectionRow>
        <Focusable flow-children="down" style={{ gap: "12px", width: "100%" }}>
          <Field label="Modo de generación">
            <div className="decky-select">
              <select
                className="DeckySelectable"
                value={settings.mode}
                onChange={(e) => onSettingsChange({ ...settings, mode: e.target.value })}
              >
                <option value="offline">Offline (modelo local)</option>
                <option value="remote">Endpoint remoto</option>
                <option value="template">Plantillas (emergencia)</option>
              </select>
            </div>
          </Field>
          <FormDivider />
          <ToggleField
            label="Habilitar endpoint remoto"
            checked={settings.remote.enabled}
            onChange={(checked) =>
              onSettingsChange({ ...settings, remote: { ...settings.remote, enabled: checked } })
            }
          />
          <TextField
            label="URL del endpoint"
            value={settings.remote.endpoint}
            onChange={(e) => onSettingsChange({ ...settings, remote: { ...settings.remote, endpoint: e.target.value } })}
          />
          <TextField
            label="Token/Bearer"
            value={settings.remote.auth}
            onChange={(e) => onSettingsChange({ ...settings, remote: { ...settings.remote, auth: e.target.value } })}
          />
          <FormDivider />
          <TextField
            label="Temperatura"
            value={String(settings.model.temperature)}
            onChange={(e) =>
              onSettingsChange({
                ...settings,
                model: {
                  ...settings.model,
                  temperature: Number.parseFloat(e.target.value) || settings.model.temperature,
                },
              })
            }
          />
          <TextField
            label="Top P"
            value={String(settings.model.top_p)}
            onChange={(e) =>
              onSettingsChange({
                ...settings,
                model: {
                  ...settings.model,
                  top_p: Number.parseFloat(e.target.value) || settings.model.top_p,
                },
              })
            }
          />
          <TextField
            label="Contexto"
            value={String(settings.model.ctx)}
            onChange={(e) =>
              onSettingsChange({
                ...settings,
                model: {
                  ...settings.model,
                  ctx: Number.parseInt(e.target.value) || settings.model.ctx,
                },
              })
            }
          />
          <TextField
            label="Ruta voz Piper"
            value={settings.tts.path}
            onChange={(e) => onSettingsChange({ ...settings, tts: { ...settings.tts, path: e.target.value } })}
          />
          <TextField
            label="Voz predeterminada"
            value={settings.tts.voice ?? "es-ES"}
            onChange={(e) => onSettingsChange({ ...settings, tts: { ...settings.tts, voice: e.target.value } })}
          />
          <TextField
            label="Velocidad"
            value={String(settings.tts.speed ?? 1.0)}
            onChange={(e) =>
              onSettingsChange({
                ...settings,
                tts: {
                  ...settings.tts,
                  speed: Number(e.target.value) || 1,
                },
              })
            }
          />
          <FormDivider />
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <ButtonItem disabled={working} onClick={verifyResources}>
              Verificar recursos
            </ButtonItem>
            <ButtonItem disabled={working} onClick={persist}>
              Guardar ajustes
            </ButtonItem>
          </div>
          {status && <div style={{ fontSize: "12px", opacity: 0.7 }}>{status}</div>}
        </Focusable>
      </PanelSectionRow>
    </PanelSection>
  );
}

function useSettingsHook() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getSettings()
      .then((value) => setSettings(value))
      .catch((err) => {
        console.error(err);
        setSettings(null);
      })
      .finally(() => setLoading(false));
  }, []);

  return { settings, setSettings, loading };
}

function GenerateTab() {
  const { settings } = useSettingsHook();
  const [story, setStory] = useState("");
  const [status, setStatus] = useState("");
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async (params) => {
    setGenerating(true);
    setStory("");
    setStatus("Conectando...");
    try {
      const chunks = await api.generateStory(params);
      let combined = "";
      for (const chunk of chunks) {
        if (chunk.error) {
          setStatus(chunk.error);
        }
        combined += chunk.text;
        setStory(combined);
        setStatus(chunk.done ? "Completado" : "Generando...");
      }
    } catch (err) {
      console.error(err);
      setStatus("No se pudo generar la historia");
    } finally {
      setGenerating(false);
    }
  };

  const speak = async () => {
    if (!story) return;
    setStatus("Preparando narración...");
    try {
      const result = await api.speak(story, settings?.tts?.voice);
      if (result?.path) {
        const audio = new Audio(result.path);
        audio.play().catch((err) => console.error("No se pudo reproducir", err));
        setStatus("Reproduciendo narración");
      } else {
        setStatus("No se pudo generar audio");
      }
    } catch (err) {
      console.error(err);
      setStatus("Error durante la narración");
    }
  };

  const save = async () => {
    if (!story) return;
    try {
      const entry = await api.createSave({
        title: story.slice(0, 40) || "Historia",
        content: story,
      });
      setStatus(`Guardado como ${entry.title}`);
    } catch (err) {
      console.error(err);
      setStatus("No se pudo guardar");
    }
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
      <Controls disabled={generating} onGenerate={handleGenerate} />
      <OutputView
        text={story}
        isGenerating={generating}
        onSpeak={speak}
        onClear={() => {
          setStory("");
          setStatus("");
        }}
        onSave={save}
        onContinue={() => handleGenerate({
          genre: settings?.mode === "remote" ? "aventura" : "fantasía",
          tone: "Continuación coherente",
          keywords: [],
          characters: [],
          length: "medium",
        })}
        statusMessage={status}
      />
      {settings && (
        <PanelSection title="Modo actual">
          <PanelSectionRow>
            {settings.mode === "remote"
              ? "Usando endpoint remoto"
              : settings.mode === "template"
              ? "Modo plantillas (degradado)"
              : "Modo offline"}
          </PanelSectionRow>
        </PanelSection>
      )}
    </div>
  );
}

function SavesTab() {
  const [loadedStory, setLoadedStory] = useState("");

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
      <SavesView onLoad={setLoadedStory} />
      <PanelSection title="Vista previa">
        <PanelSectionRow>
          <div style={{ whiteSpace: "pre-wrap", maxHeight: "260px", overflowY: "auto" }}>{loadedStory}</div>
        </PanelSectionRow>
      </PanelSection>
    </div>
  );
}

function SettingsTab() {
  const { settings, setSettings, loading } = useSettingsHook();

  return (
    <div style={{ padding: "16px" }}>
      {loading ? <div>Cargando...</div> : <SettingsViewWrapper settings={settings} onSettingsChange={setSettings} />}
    </div>
  );
}

function AboutTab() {
  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
      <h2>NIA – Generador Narrativo IA</h2>
      <p>
        Proyecto experimental para Steam Deck. Genera relatos interactivos utilizando modelos locales o remotos y narración
        TTS en español.
      </p>
      <p>
        Guarda tus historias en <code>~/.local/share/nia-decky/saves</code> y personaliza la experiencia en la pestaña de
        ajustes.
      </p>
      <p>Licencias y créditos de modelos disponibles en el README.</p>
    </div>
  );
}

export default definePlugin(() => {
  return {
    title: "NIA – Generador Narrativo IA",
    icon: "Deck",
    content: (
      <Router
        tabs={[
          { title: "Generar", content: <GenerateTab /> },
          { title: "Partidas", content: <SavesTab /> },
          { title: "Ajustes", content: <SettingsTab /> },
          { title: "Acerca de", content: <AboutTab /> },
        ]}
      />
    ),
    quickAccessItem: <QuickAccessTab title="NIA" icon="Deck" onClick={() => null} />,
  };
});
