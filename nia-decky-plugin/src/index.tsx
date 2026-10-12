import { definePlugin } from "@decky/api";
import { ButtonItem, Field, Focusable, PanelSection, PanelSectionRow, Spinner, staticClasses, TextField } from "@decky/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import { SettingsView } from "./components/Settings";
import { api, GameEventType, GameState, NarrationResult, Settings } from "./lib/api";

function App() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [narration, setNarration] = useState("");
  const [status, setStatus] = useState("");
  const [detail, setDetail] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const currentGameId = useRef("");

  const refresh = useCallback(async () => {
    try {
      const newState = await api.getGameState();
      setGameState(newState);
      const gameId = newState.active_game?.id || "";
      if (gameId !== currentGameId.current) {
        currentGameId.current = gameId;
        setNarration(newState.latest_narration?.text || "");
      } else if (newState.latest_narration?.text) {
        setNarration(newState.latest_narration.text);
      }
    } catch (error) {
      console.error(error);
      setStatus("NIA no pudo leer el estado del juego");
    }
  }, []);

  useEffect(() => {
    void refresh();
    void api.getSettings().then(setSettings).catch((error) => {
      console.error(error);
      setStatus("NIA no pudo cargar los ajustes");
    });
    const timer = window.setInterval(() => void refresh(), 12000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const act = async (event: GameEventType) => {
    setBusy(true);
    setStatus("Preparando una intervención breve…");
    try {
      const result: NarrationResult = await api.recordGameEvent(event, detail);
      setNarration(result.text);
      setStatus(result.status);
      setDetail("");
      setGameState(await api.getGameState());
    } catch (error) {
      console.error(error);
      setStatus(error instanceof Error ? error.message : "No se pudo generar la intervención");
    } finally {
      setBusy(false);
    }
  };

  const speak = async () => {
    if (!narration) return;
    setBusy(true);
    try {
      const result = await api.speak(narration);
      setStatus("Reproduciendo con " + result.player);
    } catch (error) {
      console.error(error);
      setStatus(error instanceof Error ? error.message : "No se pudo reproducir la voz");
    } finally {
      setBusy(false);
    }
  };

  const game = gameState?.active_game;
  const stats = gameState?.stats;
  return (
    <div>
      <div className={staticClasses.Title}>NIA · narrador de juegos</div>
      <PanelSection title="Juego activo">
        <PanelSectionRow>
          <Focusable flow-children="down" style={{ gap: "8px", width: "100%" }}>
            {game ? (
              <>
                <div style={{ fontSize: "18px", fontWeight: 600 }}>{game.title}</div>
                <div style={{ opacity: 0.72 }}>{game.platform} · sesión {gameState?.session_minutes ?? 0} min</div>
                <div style={{ opacity: 0.72 }}>
                  Caídas registradas {stats?.deaths ?? 0} · checkpoints {stats?.checkpoints ?? 0} · objetivos {stats?.objectives ?? 0}
                </div>
              </>
            ) : (
              <div>{gameState?.message ?? "Buscando un juego activo…"} <Spinner /></div>
            )}
            <ButtonItem layout="below" disabled={busy} onClick={() => void refresh()}>Actualizar detección</ButtonItem>
          </Focusable>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Registrar un momento">
        <PanelSectionRow>
          <Focusable flow-children="down" style={{ gap: "8px", width: "100%" }}>
            <Field label="Detalle opcional">
              <TextField value={detail} onChange={(event) => setDetail(event.target.value)}
                disabled={!game || busy} />
            </Field>
            <ButtonItem layout="below" disabled={!game || busy} onClick={() => void act("death")}>Morí / repetí una sección</ButtonItem>
            <ButtonItem layout="below" disabled={!game || busy} onClick={() => void act("checkpoint")}>Llegué a un checkpoint</ButtonItem>
            <ButtonItem layout="below" disabled={!game || busy} onClick={() => void act("objective")}>Avancé / descubrí algo</ButtonItem>
            <ButtonItem layout="below" disabled={!game || busy} onClick={() => void act("victory")}>Gané / terminé</ButtonItem>
            <ButtonItem layout="below" disabled={!game || busy} onClick={() => void act("commentary")}>NIA, comenta la partida</ButtonItem>
          </Focusable>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Narración de NIA">
        <PanelSectionRow>
          <Focusable flow-children="down" style={{ gap: "8px", width: "100%" }}>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.45, padding: "8px" }}>
              {busy ? "Generando en segundo plano…" : narration || "NIA mostrará aquí la última intervención."}
            </div>
            {status && <div style={{ fontSize: "12px", opacity: 0.72 }}>{status}</div>}
            <ButtonItem layout="below" disabled={!narration || busy || !settings?.tts.enabled} onClick={() => void speak()}>
              Reproducir última intervención
            </ButtonItem>
          </Focusable>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Ajustes">
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setSettingsOpen((open) => !open)}>
            {settingsOpen ? "Ocultar ajustes" : "Personalizar voz, tono y detección"}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
      {settingsOpen && <SettingsView settings={settings} onSettingsChange={setSettings} />}
    </div>
  );
}

export default definePlugin(() => ({
  name: "NIA · Narrador de juegos",
  titleView: <div className={staticClasses.Title}>Narrador inteligente asistido</div>,
  content: <App />,
  icon: <div aria-label="NIA" style={{ fontSize: "18px" }}>🎙</div>,
}));
