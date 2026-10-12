import {
  ButtonItem, Field, Focusable, PanelSection, PanelSectionRow, TextField, ToggleField,
} from "@decky/ui";
import { useEffect, useState } from "react";
import { api, Settings } from "../lib/api";

type Props = { settings: Settings | null; onSettingsChange: (settings: Settings) => void };

export function SettingsView({ settings, onSettingsChange }: Props) {
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
              onChange={(event) => updateNarrator("provider", event.target.value as Settings["narrator"]["provider"])}>
              <option value="ollama">Ollama local (recomendado)</option>
              <option value="openai-compatible">API compatible con OpenAI</option>
              <option value="template">Comentario contextual sin LLM</option>
            </select>
          </Field>
          <TextField label="Endpoint"
            description="Ollama: http://127.0.0.1:11434 · API compatible: URL completa de chat/completions"
            value={settings.narrator.endpoint}
            onChange={(event) => updateNarrator("endpoint", event.target.value)} />
          <TextField label="Modelo" description="Debe estar disponible en el servidor configurado"
            value={settings.narrator.model}
            onChange={(event) => updateNarrator("model", event.target.value)} />
          {settings.narrator.provider === "openai-compatible" && (
            <TextField label="API key (guardada localmente)" value={settings.narrator.api_key}
              onChange={(event) => updateNarrator("api_key", event.target.value)} />
          )}
          <Field label="Personalidad de NIA">
            <select className="DeckySelectable" value={settings.narrator.persona}
              onChange={(event) => updateNarrator("persona", event.target.value as Settings["narrator"]["persona"])}>
              <option value="amable">Amable</option>
              <option value="sarcastico">Sarcástica</option>
              <option value="grosero">Grosera, con humor</option>
              <option value="epico">Épica</option>
            </select>
          </Field>
          <TextField label="Tiempo máximo de respuesta (segundos)" value={String(settings.narrator.timeout)}
            onChange={(event) => updateNarrator("timeout", Number.parseInt(event.target.value, 10) || 8)} />
          <TextField label="Máximo de tokens por intervención" value={String(settings.narrator.max_tokens)}
            onChange={(event) => updateNarrator("max_tokens", Number.parseInt(event.target.value, 10) || 96)} />
          <ToggleField label="Generar comentario al iniciar un juego" checked={settings.narrator.auto_on_start}
            onChange={(value) => updateNarrator("auto_on_start", value)} />
          <ToggleField label="Reproducir automáticamente (requiere voz)" checked={settings.narrator.auto_speak}
            onChange={(value) => updateNarrator("auto_speak", value)} />
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
