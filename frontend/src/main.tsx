import React, { FormEvent, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Circle,
  Loader2,
  Play,
  Settings2,
  SquareTerminal,
} from "lucide-react";
import "./styles.css";

type AgentConfig = {
  doc_id: string;
  teacher_doc: string;
  domain: string;
  course_id: string;
  base_course_id: string;
  create_new_course: boolean;
  openrouter_model: string;
};

type FlowStep = {
  id: string;
  label: string;
  description: string;
};

type RunSummary = {
  canvasCourseId?: string | null;
  isValid: boolean;
  errors: string[];
  course: {
    name?: string | null;
    academicProgram?: string | null;
    semester?: number | null;
    teacher?: string | null;
    modulesCount: number;
    activitiesCount: number;
  };
  urls: Record<string, string | null | undefined>;
  forumDiscussionId?: number | null;
  moduleMapping: Record<string, number>;
  canvasAssignmentIds: Record<string, number>;
};

type RunResponse = {
  ok: boolean;
  exitCode?: number;
  error?: string;
  logs?: string;
  summary?: RunSummary | null;
};

const defaultSteps: FlowStep[] = [
  { id: "analyst", label: "Analista", description: "Lee Google Docs e infiere la estructura del curso." },
  { id: "setup_course", label: "Configurar curso", description: "Prepara el curso de Canvas." },
  { id: "module_generator", label: "Unidades", description: "Crea las unidades principales." },
  { id: "content_creators", label: "Contenido paralelo", description: "Agenda, alineacion, foro y creditos." },
  { id: "page_creator", label: "Pagina de inicio", description: "Construye la portada del curso." },
  { id: "unit_pages_creator", label: "Paginas de unidad", description: "Crea paginas por unidad." },
  { id: "activity_creator", label: "Actividades", description: "Crea assignments." },
  { id: "rubrics_creator", label: "Rubricas", description: "Asocia rubricas." },
  { id: "syllabus_creator", label: "Syllabus", description: "Actualiza el programa." },
];

const initialConfig: AgentConfig = {
  doc_id: "",
  teacher_doc: "",
  domain: "univallecolombia.instructure.com",
  course_id: "",
  base_course_id: "",
  create_new_course: false,
  openrouter_model: "inclusionai/ring-2.6-1t",
};

function App() {
  const [config, setConfig] = useState<AgentConfig>(initialConfig);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [logs, setLogs] = useState("");

  const stepState = useMemo(() => {
    if (isRunning) return "running";
    if (!result) return "idle";
    return result.ok ? "success" : "error";
  }, [isRunning, result]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsRunning(true);
    setResult(null);
    setLogs("Ejecutando agente...");

    try {
      const response = await fetch("/api/run-agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config }),
      });
      const data = (await response.json()) as RunResponse;
      setResult(data);
      setLogs(data.logs || data.error || "");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error desconocido";
      setResult({ ok: false, error: message });
      setLogs(message);
    } finally {
      setIsRunning(false);
    }
  }

  function updateField<K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <p className="eyebrow">Canvas LMS Agent</p>
          <h1>Configurador de ejecucion</h1>
        </div>
        <div className={`status-pill ${stepState}`}>
          {isRunning ? <Loader2 className="spin" size={16} /> : result?.ok ? <CheckCircle2 size={16} /> : <Circle size={16} />}
          <span>{isRunning ? "Ejecutando" : result?.ok ? "Completado" : result ? "Revisar" : "Listo"}</span>
        </div>
      </section>

      <section className="workspace">
        <form className="config-panel" onSubmit={handleSubmit}>
          <PanelTitle icon={<Settings2 size={18} />} title="Configuracion" />
          <Field label="Google Doc ID" required>
            <input value={config.doc_id} onChange={(event) => updateField("doc_id", event.target.value)} placeholder="Documento principal" />
          </Field>
          <Field label="Profesor Doc ID">
            <input value={config.teacher_doc} onChange={(event) => updateField("teacher_doc", event.target.value)} placeholder="Opcional" />
          </Field>
          <div className="field-row">
            <Field label="Dominio Canvas">
              <input value={config.domain} onChange={(event) => updateField("domain", event.target.value)} />
            </Field>
            <Field label="Modelo">
              <input value={config.openrouter_model} onChange={(event) => updateField("openrouter_model", event.target.value)} />
            </Field>
          </div>
          <label className="toggle-line">
            <input
              type="checkbox"
              checked={config.create_new_course}
              onChange={(event) => updateField("create_new_course", event.target.checked)}
            />
            <span>Crear curso nuevo en Canvas</span>
          </label>
          <div className="field-row">
            <Field label="Course ID" required={!config.create_new_course}>
              <input
                value={config.course_id}
                onChange={(event) => updateField("course_id", event.target.value)}
                disabled={config.create_new_course}
                placeholder={config.create_new_course ? "Se genera automaticamente" : "Curso existente"}
              />
            </Field>
            <Field label="Base Course ID">
              <input value={config.base_course_id} onChange={(event) => updateField("base_course_id", event.target.value)} placeholder="Opcional" />
            </Field>
          </div>
          <button className="run-button" type="submit" disabled={isRunning}>
            {isRunning ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            <span>Ejecutar agente</span>
          </button>
        </form>

        <section className="flow-panel">
          <PanelTitle icon={<BookOpen size={18} />} title="Flujo visual" />
          <div className="flow-track">
            {defaultSteps.map((step, index) => (
              <FlowNode key={step.id} step={step} index={index} status={stepState} active={isRunning && index === 0} />
            ))}
          </div>
        </section>

        <section className="output-panel">
          <PanelTitle icon={<SquareTerminal size={18} />} title="Resultado" />
          <Summary result={result} />
          <pre className="logs">{logs || "Los logs de ejecucion apareceran aqui."}</pre>
        </section>
      </section>
    </main>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <label className="field">
      <span>
        {label}
        {required ? " *" : ""}
      </span>
      {children}
    </label>
  );
}

function FlowNode({ step, index, status, active }: { step: FlowStep; index: number; status: string; active: boolean }) {
  return (
    <article className={`flow-node ${status} ${active ? "active" : ""}`}>
      <div className="node-marker">
        {status === "success" ? <CheckCircle2 size={18} /> : status === "error" ? <AlertCircle size={18} /> : <span>{index + 1}</span>}
      </div>
      <div>
        <h3>{step.label}</h3>
        <p>{step.description}</p>
      </div>
    </article>
  );
}

function Summary({ result }: { result: RunResponse | null }) {
  if (!result) {
    return <div className="empty-summary">Configura y ejecuta el agente para ver el resumen.</div>;
  }

  if (!result.ok && result.error) {
    return <div className="error-box">{result.error}</div>;
  }

  const summary = result.summary;
  if (!summary) return <div className="error-box">No se recibio resumen de la ejecucion.</div>;

  return (
    <div className="summary-grid">
      <Metric label="Canvas ID" value={summary.canvasCourseId || "N/A"} />
      <Metric label="Unidades" value={summary.course.modulesCount} />
      <Metric label="Actividades" value={summary.course.activitiesCount} />
      <Metric label="Errores" value={summary.errors.length} tone={summary.errors.length ? "bad" : "good"} />
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: "good" | "bad" }) {
  return (
    <div className={`metric ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
