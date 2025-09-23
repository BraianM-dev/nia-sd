import { definePlugin, PanelSection, PanelSectionRow, QuickAccessTab, Router } from "decky";
import { useEffect, useState } from "react";
import { Controls } from "./components/Controls";
import { Output } from "./components/Output";
import { Saves } from "./components/Saves";
import { SettingsView } from "./components/Settings";
import { api, Settings, StoryChunk, StoryParams } from "./lib/api";

function useSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
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

function GenerarTab() {
  const { settings, setSettings } = useSettings();
  const [story, setStory] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [generating, setGenerating] = useState<boolean>(false);

  const handleGenerate = async (params: StoryParams) => {
    setGenerating(true);
    setStory("");
    setStatus("Conectando...");
    try {
      await api.generateStory(params, (chunk: StoryChunk) => {
        if (chunk.error) {
          setStatus(chunk.error);
        }
        setStory((prev) => prev + chunk.text);
        setStatus(chunk.done ? "Completado" : "Generando...");
      });
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
      const result = await api.speak(story, settings?.tts.voice);
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
      <Output
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
          seed: undefined,
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

function PartidasTab() {
  const [loadedStory, setLoadedStory] = useState<string>("");

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
      <Saves onLoad={setLoadedStory} />
      <PanelSection title="Vista previa">
        <PanelSectionRow>
          <div style={{ whiteSpace: "pre-wrap", maxHeight: "260px", overflowY: "auto" }}>{loadedStory}</div>
        </PanelSectionRow>
      </PanelSection>
    </div>
  );
}

function AjustesTab() {
  const { settings, setSettings, loading } = useSettings();

  return (
    <div style={{ padding: "16px" }}>
      {loading ? <div>Cargando...</div> : <SettingsView settings={settings} onSettingsChange={setSettings} />}
    </div>
  );
}

function AcercaTab() {
  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
      <h2>NIA – Generador Narrativo IA</h2>
      <p>
        Proyecto experimental para Steam Deck. Genera relatos interactivos utilizando modelos locales o remotos y
        narración TTS en español.
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
          { title: "Generar", content: <GenerarTab /> },
          { title: "Partidas", content: <PartidasTab /> },
          { title: "Ajustes", content: <AjustesTab /> },
          { title: "Acerca de", content: <AcercaTab /> },
        ]}
      />
    ),
    quickAccessItem: <QuickAccessTab title="NIA" icon="Deck" onClick={() => null} />,
  };
});
