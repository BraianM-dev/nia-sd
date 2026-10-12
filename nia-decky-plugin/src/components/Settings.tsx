import {
  ButtonItem, Field, Focusable, PanelSection, PanelSectionRow, TextField, ToggleField,
} from "@decky/ui";
import { useEffect, useState } from "react";
import { api, GameInfo, GameProfile, LocalRuntimeStatus, Persona, Provider, Settings } from "../lib/api";

type Props = { settings: Settings | null; activeGame: GameInfo | null; onSettingsChange: (settings: Settings) => void };

const PROVIDER_PRESETS: Partial<Record<Provider, { endpoint: string; model: string }>> = {
  "local-llama": { endpoint: "", model: "qwen2.5-1.5b-instruct-q4_k_m" },
  ollama: { endpoint: "http://127.0.0.1:11434", model: "qwen2.5:3b" },
  openai: { endpoint: "https://api.openai.com/v1/chat/completions", model: "gpt-5.6-terra" },
  grok: { endpoint: "https://api.x.ai/v1/chat/completions", model: "grok-4.7" },
  deepseek: { endpoint: "https://api.deepseek.com/chat/completions", model: "deepseek-v4-flash" },
  gemini: {
    endpoint: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    model: "gemini-3.8-flash",
  },
};

function LocalRuntimePanel({ settings }: { settings: Settings }) {
  const [runtime, setRuntime] = useState<LocalRuntimeStatus | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");
  const modelPath = settings.model.path || "";

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const result = await api.localRuntimeStatus(modelPath);
        if (active) setRuntime(result);
      } catch (error) {
        console.error(error);
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1800);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [modelPath]);

  const install = async () => {
    setWorking(true);
    try {
      setRuntime(await api.installLocalRuntime(modelPath));
    } catch (error) {
      console.error(error);
      setActionError(error instanceof Error ? error.message : "No se pudo instalar el motor local");
    } finally {
      setWorking(false);
    }
  };
  const remove = async () => {
    setWorking(true);
    try {
      setRuntime(await api.removeLocalRuntime());
    } catch (error) {
      console.error(error);
      setActionError(error instanceof Error ? error.message : "No se pudo eliminar el motor local");
    } finally {
      setWorking(false);
    }
  };
  const cancel = async () => {
    setWorking(true);
    setActionError("");
    try {
      setRuntime(await api.cancelLocalRuntimeInstall());
    } catch (error) {
      console.error(error);
      setActionError(error instanceof Error ? error.message : "No se pudo cancelar la instalación");
    } finally {
      setWorking(false);
    }
  };

  const installed = Boolean(runtime?.engine_installed && runtime?.model_installed);
  const usesCustomModel = Boolean(modelPath.trim());
  const progress = Math.max(0, Math.min(100, runtime?.progress ?? 0));
  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "8px" }}>
      <Field label="Motor local de NIA">
        <div style={{ fontSize: "12px", opacity: 0.8 }}>
          {runtime?.message || "Consultando instalación…"}
          {runtime?.server_running ? " · servidor activo" : ""}
          {runtime?.error ? " · " + runtime.error : ""}
        </div>
      </Field>
      {runtime?.installing && (
        <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.15)", borderRadius: "4px" }}>
          <div style={{ width: progress + "%", height: "100%", background: "#8bc34a", borderRadius: "4px" }} />
        </div>
      )}
      {actionError && <div role="alert" style={{ color: "var(--color-error)", fontSize: "12px" }}>{actionError}</div>}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <ButtonItem disabled={working || Boolean(runtime?.installing) || installed} onClick={install}>
          {runtime?.installing ? "Instalando…" : installed ? "Motor y modelo instalados" : usesCustomModel ? "Instalar motor llama.cpp" : "Descargar e instalar (aprox. 1,12 GB)"}
        </ButtonItem>
        {runtime?.installing && (
          <ButtonItem disabled={working} onClick={cancel}>Cancelar instalación</ButtonItem>
        )}
        {installed && (
          <ButtonItem disabled={working || Boolean(runtime?.installing)} onClick={remove}>
            Eliminar motor y modelo de NIA
          </ButtonItem>
        )}
      </div>
      <div style={{ fontSize: "12px", opacity: 0.7 }}>
        {usesCustomModel ? "Se usará el GGUF indicado arriba; esa ruta no se borra al eliminar el motor." : "Usa Qwen 1.5B Q4_K_M."}
        {" "}Se instala en los datos de NIA, sin root. Corre en localhost, limita CPU a 2 hilos por defecto
        y descarga el modelo de memoria tras quedar inactivo.
      </div>
    </div>
  );
}

export function SettingsView({ settings, activeGame, onSettingsChange }: Props) {
  const [working, setWorking] = useState(false);
  const [status, setStatus] = useState("");
  useEffect(() => setStatus(settings?.status ?? ""), [settings]);
  if (!settings) return <div>Cargando ajustes…</div>;

  const updateNarrator = <K extends keyof Settings["narrator"],>(key: K, value: Settings["narrator"][K]) =>
    onSettingsChange({ ...settings, narrator: { ...settings.narrator, [key]: value } });
  const updateDetection = <K extends keyof Settings["game_detection"],>(
    key: K, value: Settings["game_detection"][K],
  ) => onSettingsChange({ ...settings, game_detection: { ...settings.game_detection, [key]: value } });
  const updateTTS = <K extends keyof Settings["tts"],>(key: K, value: Settings["tts"][K]) =>
    onSettingsChange({ ...settings, tts: { ...settings.tts, [key]: value } });
  const gameProfiles: Record<string, GameProfile> = settings.game_profiles || {};
  const activeProfile = activeGame ? gameProfiles[activeGame.id] || {} : {};
  const updateGameProfile = (key: keyof GameProfile, value: string) => {
    if (!activeGame) return;
    const nextProfile: GameProfile = { ...activeProfile };
    if (key === "persona") {
      if (value === "default") delete nextProfile.persona;
      else nextProfile.persona = value as Persona;
    } else if (value.trim()) {
      nextProfile.voice_model = value;
    } else {
      delete nextProfile.voice_model;
    }
    const nextProfiles = { ...gameProfiles };
    if (Object.keys(nextProfile).length) nextProfiles[activeGame.id] = nextProfile;
    else delete nextProfiles[activeGame.id];
    onSettingsChange({ ...settings, game_profiles: nextProfiles });
  };

  const verify = async () => {
    setWorking(true);
    try {
      const result = await api.verifyResources();
      setStatus(result.status + ": " + result.details.join(" · "));
    } catch (error) {
      console.error(error);
      setStatus("No se pudieron verificar los recursos");
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
    } catch (error) {
      console.error(error);
      setStatus("No se pudieron guardar los ajustes");
    } finally {
      setWorking(false);
    }
  };

  return (
    <PanelSection title="Configuración de NIA">
      <PanelSectionRow>
        <Focusable flow-children="down" style={{ gap: "12px", width: "100%" }}>
          <Field label="Motor de narración">
            <select className="DeckySelectable" value={settings.narrator.provider}
              onChange={(event) => {
                const provider = event.target.value as Provider;
                const preset = PROVIDER_PRESETS[provider];
                const nextNarrator = { ...settings.narrator, provider, api_key: "" };
                if (preset) {
                  nextNarrator.endpoint = preset.endpoint;
                  nextNarrator.model = preset.model;
                }
                onSettingsChange({ ...settings, narrator: nextNarrator });
              }}>
              <option value="local-llama">NIA local · llama.cpp (recomendado)</option>
              <option value="ollama">Ollama en este equipo o en otro equipo</option>
              <option value="openai">OpenAI API</option>
              <option value="grok">xAI Grok API</option>
              <option value="deepseek">DeepSeek API</option>
              <option value="gemini">Google Gemini API</option>
              <option value="openai-compatible">Otro endpoint compatible</option>
              <option value="template">Comentario contextual sin LLM</option>
            </select>
          </Field>
          {settings.narrator.provider !== "local-llama" && settings.narrator.provider !== "template" && (
            <TextField label="Endpoint"
              description="Usa la dirección del proveedor seleccionado; solo cámbiala si necesitas un proxy."
              value={settings.narrator.endpoint}
              onChange={(event) => updateNarrator("endpoint", event.target.value)} />
          )}
          {settings.narrator.provider !== "local-llama" && settings.narrator.provider !== "template" && (
            <TextField label="Modelo" description="Nombre de modelo aceptado por el proveedor; puedes cambiarlo."
              value={settings.narrator.model}
              onChange={(event) => updateNarrator("model", event.target.value)} />
          )}
          {["openai", "grok", "deepseek", "gemini", "openai-compatible"].includes(settings.narrator.provider) && (
            <Field label="Clave API (guardada localmente)"
              description="NIA la envía solo al proveedor seleccionado y la borra al cambiar de proveedor. Las API se facturan por separado de suscripciones de chat.">
              <input type="password" autoComplete="off" value={settings.narrator.api_key}
                onChange={(event) => updateNarrator("api_key", event.target.value)}
                style={{ width: "100%", boxSizing: "border-box", padding: "8px", color: "inherit", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: "3px" }} />
            </Field>
          )}
          {settings.narrator.provider === "local-llama" && <LocalRuntimePanel settings={settings} />}
          <Field label="Personalidad predeterminada de NIA">
            <select className="DeckySelectable" value={settings.narrator.persona}
              onChange={(event) => updateNarrator("persona", event.target.value as Settings["narrator"]["persona"])}>
              <option value="amable">Amable</option>
              <option value="sarcastico">Sarcástica</option>
              <option value="grosero">Grosera, con humor</option>
              <option value="epico">Épica</option>
            </select>
          </Field>
          <Field label={activeGame ? `Perfil de ${activeGame.title}` : "Perfil por juego"}
            description={activeGame ? "Personalidad y voz específicas para este juego; los campos vacíos heredan los ajustes predeterminados." : "Inicia un juego para configurar una personalidad y una voz exclusivas."}>
            {activeGame ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
                <select className="DeckySelectable" value={activeProfile.persona || "default"}
                  onChange={(event) => updateGameProfile("persona", event.target.value)}>
                  <option value="default">Personalidad predeterminada ({settings.narrator.persona})</option>
                  <option value="amable">Amable</option>
                  <option value="sarcastico">Sarcástica</option>
                  <option value="grosero">Grosera, con humor</option>
                  <option value="epico">Épica</option>
                </select>
                <TextField label="Voz Piper exclusiva (.onnx, opcional)"
                  description="Ruta vacía usa la voz predeterminada. La reproducción requiere Piper y un reproductor de audio instalado."
                  value={activeProfile.voice_model || ""}
                  onChange={(event) => updateGameProfile("voice_model", event.target.value)} />
              </div>
            ) : <div style={{ fontSize: "12px", opacity: 0.75 }}>No hay un juego activo; abre el panel NIA cuando un juego esté en ejecución.</div>}
          </Field>
          <TextField label="Tiempo máximo de respuesta (segundos, APIs remotas)"
            value={String(settings.narrator.timeout)}
            onChange={(event) => updateNarrator("timeout", Number.parseInt(event.target.value, 10) || 8)} />
          <TextField label="Máximo de tokens por intervención" value={String(settings.narrator.max_tokens)}
            onChange={(event) => updateNarrator("max_tokens", Number.parseInt(event.target.value, 10) || 96)} />
          <ToggleField label="Generar comentario al iniciar un juego" checked={settings.narrator.auto_on_start}
            onChange={(value) => updateNarrator("auto_on_start", value)} />
          <ToggleField label="Reproducir automáticamente (requiere voz)" checked={settings.narrator.auto_speak}
            onChange={(value) => updateNarrator("auto_speak", value)} />
          {settings.narrator.provider === "local-llama" && (
            <>
              <TextField label="Hilos de CPU para el modelo (1–4)"
                value={String(settings.local_runtime.threads)}
                onChange={(event) => onSettingsChange({
                  ...settings, local_runtime: { ...settings.local_runtime, threads: Number.parseInt(event.target.value, 10) || 2 },
                })} />
              <TextField label="Contexto del modelo (1024–4096 tokens)"
                value={String(settings.local_runtime.context_size)}
                onChange={(event) => onSettingsChange({
                  ...settings, local_runtime: { ...settings.local_runtime, context_size: Number.parseInt(event.target.value, 10) || 2048 },
                })} />
              <TextField label="Segundos inactivo antes de descargar el modelo de RAM"
                value={String(settings.local_runtime.idle_sleep_seconds)}
                onChange={(event) => onSettingsChange({
                  ...settings, local_runtime: { ...settings.local_runtime, idle_sleep_seconds: Number.parseInt(event.target.value, 10) || 90 },
                })} />
              <TextField label="Ruta a otro modelo GGUF (opcional)"
                description="Vacía usa el Qwen incluido. Si indicas otra ruta, NIA no descargará el modelo recomendado."
                value={settings.model.path}
                onChange={(event) => onSettingsChange({
                  ...settings, model: { ...settings.model, path: event.target.value },
                })} />
            </>
          )}
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", width: "100%" }} />
          <ToggleField label="Detectar el juego activo" checked={settings.game_detection.enabled}
            onChange={(value) => updateDetection("enabled", value)} />
          <TextField label="Intervalo de detección (8–60 segundos)"
            value={String(settings.game_detection.scan_interval_seconds)}
            onChange={(event) => updateDetection("scan_interval_seconds", Number.parseInt(event.target.value, 10) || 12)} />
          <TextField label="Carpetas de juegos adicionales"
            description="Rutas separadas por comas. Útil para Heroic, GOG, Epic o Lutris."
            value={settings.game_detection.roots.join(", ")}
            onChange={(event) => updateDetection("roots", event.target.value.split(",").map((path) => path.trim()).filter(Boolean))} />
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", width: "100%" }} />
          <ToggleField label="Habilitar voz Piper" checked={settings.tts.enabled}
            onChange={(value) => updateTTS("enabled", value)} />
          <TextField label="Ruta al modelo de voz Piper (.onnx)" value={settings.tts.voice_model}
            onChange={(event) => updateTTS("voice_model", event.target.value)} />
          <TextField label="Ruta al ejecutable Piper"
            description="Vacía usa el comando piper instalado en el sistema"
            value={settings.tts.piper_binary}
            onChange={(event) => updateTTS("piper_binary", event.target.value)} />
          <TextField label="Velocidad de voz (0.5–2.0)" value={String(settings.tts.speed)}
            onChange={(event) => updateTTS("speed", Number.parseFloat(event.target.value) || 1)} />
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", width: "100%" }} />
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <ButtonItem disabled={working} onClick={verify}>Probar recursos</ButtonItem>
            <ButtonItem disabled={working} onClick={persist}>Guardar ajustes</ButtonItem>
          </div>
          {status && <div style={{ fontSize: "12px", opacity: 0.75 }}>{status}</div>}
        </Focusable>
      </PanelSectionRow>
    </PanelSection>
  );
}
