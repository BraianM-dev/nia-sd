import { ButtonItem, Focusable, PanelSection, PanelSectionRow, Spinner } from "@decky/ui";
import { useEffect, useRef } from "react";

type Props = {
  text: string;
  isGenerating: boolean;
  onSpeak: () => void;
  onClear: () => void;
  onSave: () => void;
  onContinue: () => void;
  statusMessage?: string;
};

export function Output({ text, isGenerating, onSpeak, onClear, onSave, onContinue, statusMessage }: Props) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

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
