import { ButtonItem, Field, Focusable, FormDivider, PanelSection, PanelSectionRow, TextField, ToggleField } from "decky";
import { useEffect, useState } from "react";
import { api, Settings } from "../lib/api";

type Props = {
  settings: Settings | null;
  onSettingsChange: (settings: Settings) => void;
};

export function SettingsView({ settings, onSettingsChange }: Props) {
  const [working, setWorking] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    setStatus(settings?.status ?? "");
  }, [settings]);

  if (!settings) {
    return <div>Cargando ajustes...</div>;
  }

  const update = (partial: Partial<Settings>) => {
    const next = { ...settings, ...partial } as Settings;
    onSettingsChange(next);
  };

  const updateNested = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    const next = { ...settings, [key]: value };
    onSettingsChange(next);
  };

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
                onChange={(e) => update({ mode: e.target.value as Settings["mode"] })}
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
              updateNested("remote", { ...settings.remote, enabled: checked })
            }
          />
          <TextField
            label="URL del endpoint"
            value={settings.remote.endpoint}
            onChange={(e) => updateNested("remote", { ...settings.remote, endpoint: e.target.value })}
          />
          <TextField
            label="Token/Bearer"
            value={settings.remote.auth}
            onChange={(e) => updateNested("remote", { ...settings.remote, auth: e.target.value })}
          />
          <FormDivider />
          <TextField
            label="Temperatura"
            value={String(settings.model.temperature)}
            onChange={(e) =>
              updateNested("model", {
                ...settings.model,
                temperature: Number.parseFloat(e.target.value) || settings.model.temperature,
              })
            }
          />
          <TextField
            label="Top P"
            value={String(settings.model.top_p)}
            onChange={(e) =>
              updateNested("model", {
                ...settings.model,
                top_p: Number.parseFloat(e.target.value) || settings.model.top_p,
              })
            }
          />
          <TextField
            label="Contexto"
            value={String(settings.model.ctx)}
            onChange={(e) =>
              updateNested("model", {
                ...settings.model,
                ctx: Number.parseInt(e.target.value) || settings.model.ctx,
              })
            }
          />
          <TextField
            label="Ruta voz Piper"
            value={settings.tts.path}
            onChange={(e) => updateNested("tts", { ...settings.tts, path: e.target.value })}
          />
          <TextField
            label="Voz predeterminada"
            value={settings.tts.voice ?? "es-ES"}
            onChange={(e) => updateNested("tts", { ...settings.tts, voice: e.target.value })}
          />
          <TextField
            label="Velocidad"
            value={String(settings.tts.speed ?? 1.0)}
            onChange={(e) => updateNested("tts", { ...settings.tts, speed: Number(e.target.value) || 1 })}
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
