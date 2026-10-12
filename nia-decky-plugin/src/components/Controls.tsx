import { ButtonItem, Field, Focusable, TextField } from "@decky/ui";
import { useState } from "react";
import { StoryParams } from "../lib/api";
import { clampSeed, getGenres, sanitizeList, validateStoryParams } from "../lib/validate";

type Props = {
  disabled?: boolean;
  onGenerate: (params: StoryParams) => void;
};

export function Controls({ disabled, onGenerate }: Props) {
  const [genre, setGenre] = useState<string>(getGenres()[0]);
  const [tone, setTone] = useState<string>("Épico, envolvente");
  const [keywordsText, setKeywordsText] = useState<string>("");
  const [charactersText, setCharactersText] = useState<string>("");
  const [length, setLength] = useState<"short" | "medium" | "long">("medium");
  const [seed, setSeed] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const genres = getGenres();

  const submit = () => {
    const params: StoryParams = {
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
      <Field
        label="Género"
        description="Selecciona el estilo base de la historia"
      >
        <div className="decky-select">
          <select
            className="DeckySelectable"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            disabled={disabled}
          >
            {genres.map((option) => (
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
            onChange={(e) => setLength(e.target.value as "short" | "medium" | "long")}
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
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", width: "100%" }} />
      <ButtonItem disabled={disabled} layout="below" onClick={submit}>
        {disabled ? "Generando..." : "Generar"}
      </ButtonItem>
    </Focusable>
  );
}
