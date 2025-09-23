import { ButtonItem, ConfirmModal, Focusable, PanelSection, PanelSectionRow, QuickAccessTab, showModal } from "decky";
import { useEffect, useState } from "react";
import { api, SaveEntry } from "../lib/api";
import { readableSize } from "../lib/validate";

type Props = {
  onLoad: (content: string) => void;
};

export function Saves({ onLoad }: Props) {
  const [saves, setSaves] = useState<SaveEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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

  const loadSave = async (id: string) => {
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

  const deleteSave = (entry: SaveEntry) => {
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
          <QuickAccessTab
            title="Actualizar"
            onClick={refresh}
            icon="steamdeck"
            buttonClassName="DeckyButton"
          />
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
