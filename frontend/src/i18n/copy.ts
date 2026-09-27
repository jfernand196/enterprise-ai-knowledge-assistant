import type { EmployeeId } from "@/domain/chat"

export type Locale = "es" | "en"

export interface GuidePrompt {
  prompt: string
  expect: string
  userId?: EmployeeId
  employee?: string
}

export interface Copy {
  documentTitle: string
  brand: string
  title: string
  languageToggle: string
  languageToggleLabel: string
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
  toolsUsed: string
  categories: Record<string, string>
  tools: Record<string, string>
  timeout: string
  requestFailed: string
  policyPrompts: GuidePrompt[]
  employeePrompts: GuidePrompt[]
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
