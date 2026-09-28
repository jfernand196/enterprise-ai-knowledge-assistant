import type { EmployeeId } from "@/domain/chat"

export type Locale = "es" | "en"

export interface GuidePrompt {
  prompt: string
  expect: string
  userId?: EmployeeId
  employee?: string
}

export interface OpsCopy {
  link: string
  linkLabel: string
  back: string
  kicker: string
  title: string
  lead: string
  loading: string
  loadFailed: string
  requests: string
  avgLatency: string
  p95Latency: string
  tokens: string
  cost: string
  satisfaction: string
  blocked: string
  noFeedback: string
  byVersion: string
  byVersionHint: string
  byModel: string
  group: string
  recentTraces: string
  noTraces: string
  when: string
  question: string
  mode: string
  model: string
  feedback: string
  evaluation: string
  evaluationHint: string
  runEvaluation: string
  runningEvaluation: string
  passRate: string
  history: string
  noHistory: string
  case: string
  checks: string
  passed: string
  failed: string
}

export interface Copy {
  documentTitle: string
  brand: string
  title: string
  languageToggle: string
  languageToggleLabel: string
  guideButton: string
  guideButtonLabel: string
  close: string
  guideKicker: string
  guideTitle: string
  guideLead: string
  policies: string
  aboutEmployee: string
  aboutEmployeeHint: string
  employeeLabel: string
  policiesOnly: string
  employeeHint: string
  questionLabel: string
  placeholder: string
  ask: string
  searching: string
  messageRequired: string
  messageTooLong: string
  reviewing: string
  reviewingHint: string
  sources: string
  alsoChecked: string
  tokensUp: string
  tokensDown: string
  latency: string
  tokenUnit: string
  usageLabel: string
  toolsUsed: string
  categories: Record<string, string>
  tools: Record<string, string>
  timeout: string
  requestFailed: string
  feedbackPrompt: string
  feedbackUp: string
  feedbackDown: string
  feedbackThanks: string
  feedbackFailed: string
  policyPrompts: GuidePrompt[]
  employeePrompts: GuidePrompt[]
  ops: OpsCopy
}

const policyPrompts = [
  "What is the vacation policy?",
  "Do employees need multi-factor authentication?",
  "What are customer support hours?",
] as const

const employeePrompts = [
  {
    employee: "Juan Perez",
    userId: "emp-1" as const,
    prompt: "How many vacation days do I have left?",
  },
  {
    employee: "Ana Gomez",
    userId: "emp-2" as const,
    prompt: "Please submit a time off request for next Friday",
  },
  {
    employee: "Juan Perez",
    userId: "emp-1" as const,
    prompt: "Please submit a time off request for next Friday",
  },
]

export const copy: Record<Locale, Copy> = {
  es: {
    documentTitle: "Asistente de conocimiento",
    brand: "Conocimiento interno",
    title: "Asistente",
    languageToggle: "English",
    languageToggleLabel: "Pasar la interfaz al inglés",
    guideButton: "Guía",
    guideButtonLabel: "Ver qué preguntar",
    close: "Cerrar",
    guideKicker: "Guía",
    guideTitle: "Cómo probar el asistente",
    guideLead: "Las preguntas van en inglés, porque los documentos están en inglés. Pulsa una política para enviarla. En las preguntas de un empleado, elige el nombre y después pulsa Preguntar.",
    policies: "Políticas",
    aboutEmployee: "Sobre un empleado",
    aboutEmployeeHint: "Elige el nombre antes de enviar.",
    employeeLabel: "Empleado",
    policiesOnly: "Solo políticas",
    employeeHint: "Elige un nombre solo si la pregunta es sobre ti. Pregunta en inglés.",
    questionLabel: "Pregunta",
    placeholder: "What is the vacation policy?",
    ask: "Preguntar",
    searching: "Buscando…",
    messageRequired: "Escribe una pregunta.",
    messageTooLong: "La pregunta es demasiado larga.",
    reviewing: "Revisando los documentos",
    reviewingHint: "La primera respuesta puede tardar cerca de un minuto.",
    sources: "Fuentes",
    alsoChecked: "También se consultaron",
    tokensUp: "Subida",
    tokensDown: "Bajada",
    latency: "Latencia",
    tokenUnit: "tokens",
    usageLabel: "Consumo",
    toolsUsed: "Herramientas usadas",
    categories: {
      hr: "Recursos humanos",
      security: "Seguridad",
      product: "Producto",
      customer: "Soporte",
    },
    tools: {
      get_employee_profile: "Perfil",
      get_vacation_balance: "Saldo de vacaciones",
      search_documents: "Documentos",
      create_hr_request: "Solicitud de RR. HH.",
    },
    timeout: "La respuesta tardó demasiado. Vuelve a preguntar.",
    requestFailed: "No pude obtener una respuesta. Inténtalo de nuevo.",
    feedbackPrompt: "¿Te sirvió esta respuesta?",
    feedbackUp: "Sí, me sirvió",
    feedbackDown: "No me sirvió",
    feedbackThanks: "Gracias. Queda registrado en la traza.",
    feedbackFailed: "No se pudo guardar. Inténtalo otra vez.",
    ops: {
      link: "Ops",
      linkLabel: "Ver métricas, trazas y evaluaciones",
      back: "Volver al chat",
      kicker: "LLMOps",
      title: "Operación del asistente",
      lead: "Latencia, tokens, coste y feedback de cada respuesta. Las trazas se guardan en data/llmops y sobreviven a un reinicio.",
      loading: "Cargando…",
      loadFailed: "No se pudo leer el backend.",
      requests: "Peticiones",
      avgLatency: "Latencia media",
      p95Latency: "Latencia p95",
      tokens: "Tokens (entrada / salida)",
      cost: "Coste estimado",
      satisfaction: "Satisfacción",
      blocked: "Bloqueadas",
      noFeedback: "Sin votos",
      byVersion: "Por orquestador",
      byVersionHint: "prompt_version separa native (v1), langchain-v1 y langgraph-v1.",
      byModel: "Por modelo",
      group: "Grupo",
      recentTraces: "Trazas recientes",
      noTraces: "Todavía no hay trazas. Haz una pregunta en el chat.",
      when: "Hora",
      question: "Pregunta",
      mode: "Modo",
      model: "Modelo",
      feedback: "Voto",
      evaluation: "Evaluación",
      evaluationHint: "Corre las 7 preguntas de data/eval/questions.json por el mismo camino que el chat: política, agente, autorización y guardrail. Con Gemini tarda unos minutos.",
      runEvaluation: "Correr evaluación",
      runningEvaluation: "Evaluando…",
      passRate: "Aprobadas",
      history: "Corridas anteriores",
      noHistory: "Aún no hay corridas.",
      case: "Caso",
      checks: "Chequeos",
      passed: "Pasa",
      failed: "Falla",
    },
    policyPrompts: [
      { prompt: policyPrompts[0], expect: "15 días el primer año, 20 después de dos años." },
      { prompt: policyPrompts[1], expect: "Sí, en correo, VPN y Databricks." },
      { prompt: policyPrompts[2], expect: "Lunes a viernes, de 8:00 a 18:00, hora de Colombia." },
    ],
    employeePrompts: [
      { ...employeePrompts[0], expect: "Debe decir 8 días." },
      { ...employeePrompts[1], expect: "La solicitud sí se crea." },
      { ...employeePrompts[2], expect: "Debe negarla. Solo Ana Gomez puede crear solicitudes." },
    ],
  },
  en: {
    documentTitle: "Knowledge assistant",
    brand: "Internal knowledge",
    title: "Assistant",
    languageToggle: "Español",
    languageToggleLabel: "Switch the interface to Spanish",
    guideButton: "Guide",
    guideButtonLabel: "See what to ask",
    close: "Close",
    guideKicker: "Guide",
    guideTitle: "How to try the assistant",
    guideLead: "Ask in English, because the documents are in English. Click a policy to send it. For an employee question, choose the name, then press Ask.",
    policies: "Policies",
    aboutEmployee: "About an employee",
    aboutEmployeeHint: "Choose the name before you send.",
    employeeLabel: "Employee",
    policiesOnly: "Policies only",
    employeeHint: "Choose a name only if the question is about you. Ask in English.",
    questionLabel: "Question",
    placeholder: "What is the vacation policy?",
    ask: "Ask",
    searching: "Searching…",
    messageRequired: "Write a question.",
    messageTooLong: "The question is too long.",
    reviewing: "Checking the documents",
    reviewingHint: "The first answer can take about a minute.",
    sources: "Sources",
    alsoChecked: "Also checked",
    tokensUp: "Input",
    tokensDown: "Output",
    latency: "Latency",
    tokenUnit: "tokens",
    usageLabel: "Usage",
    toolsUsed: "Tools used",
    categories: {
      hr: "Human resources",
      security: "Security",
      product: "Product",
      customer: "Support",
    },
    tools: {
      get_employee_profile: "Profile",
      get_vacation_balance: "Vacation balance",
      search_documents: "Documents",
      create_hr_request: "HR request",
    },
    timeout: "The answer took too long. Ask again.",
    requestFailed: "I could not get an answer. Try again.",
    feedbackPrompt: "Was this answer helpful?",
    feedbackUp: "Yes, helpful",
    feedbackDown: "Not helpful",
    feedbackThanks: "Thanks. It is saved on the trace.",
    feedbackFailed: "Could not save it. Try again.",
    ops: {
      link: "Ops",
      linkLabel: "See metrics, traces, and evaluations",
      back: "Back to chat",
      kicker: "LLMOps",
      title: "Assistant operations",
      lead: "Latency, tokens, cost, and feedback for every answer. Traces are saved in data/llmops and survive a restart.",
      loading: "Loading…",
      loadFailed: "Could not read the backend.",
      requests: "Requests",
      avgLatency: "Average latency",
      p95Latency: "p95 latency",
      tokens: "Tokens (input / output)",
      cost: "Estimated cost",
      satisfaction: "Satisfaction",
      blocked: "Blocked",
      noFeedback: "No votes",
      byVersion: "By orchestrator",
      byVersionHint: "prompt_version separates native (v1), langchain-v1, and langgraph-v1.",
      byModel: "By model",
      group: "Group",
      recentTraces: "Recent traces",
      noTraces: "No traces yet. Ask something in the chat.",
      when: "Time",
      question: "Question",
      mode: "Mode",
      model: "Model",
      feedback: "Vote",
      evaluation: "Evaluation",
      evaluationHint: "Runs the 7 questions in data/eval/questions.json through the same path as the chat: policy, agent, authorization, and guardrail. With Gemini it takes a few minutes.",
      runEvaluation: "Run evaluation",
      runningEvaluation: "Evaluating…",
      passRate: "Passed",
      history: "Previous runs",
      noHistory: "No runs yet.",
      case: "Case",
      checks: "Checks",
      passed: "Pass",
      failed: "Fail",
    },
    policyPrompts: [
      { prompt: policyPrompts[0], expect: "15 days in the first year, 20 after two years." },
      { prompt: policyPrompts[1], expect: "Yes, for email, VPN, and Databricks." },
      { prompt: policyPrompts[2], expect: "Monday to Friday, 8:00 to 18:00, Colombia time." },
    ],
    employeePrompts: [
      { ...employeePrompts[0], expect: "It should say 8 days." },
      { ...employeePrompts[1], expect: "The request is created." },
      { ...employeePrompts[2], expect: "It should deny it. Only Ana Gomez can create requests." },
    ],
  },
}

const STORAGE_KEY = "ka-locale"

export function readLocale(): Locale {
  if (typeof localStorage === "undefined") {
    return "es"
  }
  return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "es"
}

export function storeLocale(locale: Locale): void {
  localStorage.setItem(STORAGE_KEY, locale)
}
