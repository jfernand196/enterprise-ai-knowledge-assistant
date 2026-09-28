# Arquitectura del asistente

Documento técnico del Enterprise AI Knowledge Assistant: qué hace cada pieza del camino de una pregunta y por qué está ahí.

## Problema

El asistente responde dos clases de pregunta que no se pueden resolver con el mismo mecanismo.

- Política de empresa: el texto vive en documentos aprobados. La respuesta tiene que citar ese texto y no inventar una regla.
- Dato o acción de un empleado: el saldo de vacaciones y una solicitud de tiempo libre no están en el documento de política. Hay que leerlos o escribirlos en el sistema de RR. HH., y la escritura tiene permiso.

Por eso `/chat` no llama siempre al mismo modelo. Primero decide si la pregunta es de política o si necesita herramientas.

## Recorrido de una pregunta

```
React  →  POST /chat
            →  guardrail de entrada
            →  planner: ¿hace falta una tool?
                 ├── no  →  RAG (recuperar fragmentos + generar)
                 └── sí  →  agent (plan JSON, ejecutar tools, redactar)
            →  guardrail de salida
            →  traza (latencia, tokens, coste, docs, tools) en data/llmops/traces.jsonl
React  →  POST /feedback  →  voto 👍 / 👎 sobre esa traza
```

`ChatService` es el orquestador. El planner corre en un hilo (`asyncio.to_thread`) porque la llamada al modelo es síncrona. Si el planner dice que no hay tools, entra `RagService`. Si dice que sí, entra `AgentService`. Con `ORCHESTRATOR=langgraph` el paso de ruta lo hace el grafo (ver [Orquestadores intercambiables](#orquestadores-intercambiables)); los guardrails, las métricas y la traza siguen en `ChatService`.

Los tests fuerzan `LAKEHOUSE_BACKEND=local` y `LLM_PROVIDER=extractive` antes de importar la app. La suite no depende de Databricks ni de una API de pago.

## RAG

El corpus de demostración son cuatro markdown: vacaciones, seguridad, soporte y visión de producto. En runtime con Databricks, el índice no lee esos archivos: lee `knowledge_assistant.gold.documents`. El oro es la tabla que ya pasó por bronce y plata.

### Por qué TF-IDF y no un embedding de API

`TfidfEmbeddingClient` implementa `EmbeddingPort`. Ajusta el vocabulario sobre los chunks y representa cada texto como un vector disperso de TF-IDF. El retriever compara por coseno, se queda con `candidate_k` (10) y `LexicalReranker` reordena por solapamiento de términos de la pregunta. Al generador le llegan `top_k` (3) chunks de hasta 1000 caracteres con 100 de solape.

El chunker corta en el último fin de frase (`. `) pasada la mitad del chunk. Con cortes fijos, una frase como “se pueden trasladar hasta 5 días” quedaba partida y el modelo contestaba “una cantidad especificada”. El número tiene que llegar en la misma frase que la regla.

Está así por tres razones:

- El corpus cabe en memoria. Un modelo de embeddings no cambia el resultado de forma que justifique una red en el camino de cada pregunta.
- Los tests y el modo extractivo tienen que funcionar sin clave.
- `EmbeddingPort` deja cambiar el cliente por sentence-transformers o una API sin tocar el retriever.

El rerank existe porque el coseno de TF-IDF abre la red y a veces mete un documento vecino (por ejemplo Product Overview) por encima del documento que contiene la frase. El solapamiento léxico empuja hacia arriba el chunk que realmente menciona los términos de la pregunta.

### Generador

`build_chat_generator` elige el generador:

| Condición | Generador | Por qué |
| --- | --- | --- |
| `LLM_PROVIDER` distinto de `gemini`, o sin clave | `GroundedGenerator` | Extrae frases de los chunks. Es el camino de los tests y el último recurso. |
| Gemini con clave | `GeminiGroundedGenerator` | Redacta la respuesta solo con los extractos. |

La cadena de Gemini es `gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`. Si un modelo responde 429 u otro fallo, se prueba el siguiente. Los modelos Gemini 3 que no son lite llevan `thinking_level=minimal`: la pregunta es de extracción, no de razonamiento largo, y el pensamiento extra solo añade latencia. Si toda la cadena falla y hay `GROQ_API_KEY`, entra Groq con `openai/gpt-oss-120b` (Groq retiró `llama-3.3-70b-versatile`). Si Groq también falla, vuelve el generador extractivo.

El prompt del sistema obliga a contestar solo con los extractos, a nombrar el documento en la primera frase, a copiar cada número, plazo y excepción (traslado y pago incluidos) y a decir que no hay información cuando el fragmento no alcanza. Así se reduce la invención de política. La interfaz quita la línea suelta `Document Title:` porque la cita ya muestra el título.

## Tools del agente

Hay cuatro tools. El modelo no las ejecuta directo: propone un JSON y el servicio las corre después de autorizar.

| Tool | Qué devuelve | Por qué existe |
| --- | --- | --- |
| `get_employee_profile` | Nombre y departamento | La política no dice quién es el usuario. El nombre sale de `data/hr/employees.json`. |
| `get_vacation_balance` | Días restantes | El documento dice la regla (15 y luego 20). El saldo de Juan Perez (8) o Ana Gomez (12) es un dato de persona. Si se respondiera con RAG, el modelo inventaría el número. |
| `search_documents` | Fragmentos del índice | Una pregunta personal a veces también necesita el texto de la política. Es la misma recuperación del RAG, expuesta como tool. |
| `create_hr_request` | `request_id` y estado | Es la única escritura. Crear una solicitud no es una búsqueda. |

`GeminiPlanner` pide al modelo un JSON: `{"needs_tools": false}` o una lista de llamadas. Una pregunta de saldo debe pedir perfil y saldo a la vez, para que la respuesta diga el nombre y el número. Si el JSON no parsea, cae a `KeywordPlanner`, que mira marcadores (`my`, `balance`, `submit`, `time off request`). Ese planner de palabras es el que usan los tests: es determinista y no gasta cuota.

Las tools con `user_id` no aceptan el empleado que elija el modelo. `_with_user` pisa el argumento con el `user_id` de la petición. Si el modelo intenta crear la solicitud como `emp-2` estando logueado `emp-1`, la llamada sale igual como `emp-1`.

### Autorización

`authorize_tool` corre antes de `execute`. `create_hr_request` solo está permitida si el usuario está en `hr_writers` (por defecto `emp-2`, Ana Gomez). Juan Perez recibe un error y `GeminiAnswerWriter` tiene que incluir ese error. Si el modelo lo omite, el writer lo antepone. No se puede responder “solicitud creada” cuando la tool falló.

El resto de tools son lectura. No pasan por esa lista.

## Orquestadores intercambiables

`ORCHESTRATOR` en `.env` elige quién ejecuta el flujo. Los tres usan el mismo índice, las mismas tools MCP, la misma `authorize_tool` y la misma traza. Cambiar de uno a otro no cambia qué empleado puede escribir.

| Valor | Código | Cómo decide y ejecuta |
| --- | --- | --- |
| `native` (defecto) | `app/rag`, `app/agent` | Planner JSON propio, cliente de la Interactions API de Gemini, loop escrito a mano |
| `langchain` | `app/lc` | Cadena LCEL para RAG, router con `with_structured_output`, `bind_tools` y loop manual con `ToolMessage` |
| `langgraph` | `app/lg` | Un `StateGraph`: nodos route, retrieve, generate, agent, tools, finish; `ToolNode` y `tools_condition` para el ciclo del agente |

Por qué existen los tres: el nativo muestra qué hace cada pieza sin abstracciones; los otros dos muestran lo mismo con las librerías que se usan en producción, para comparar qué ahorran y qué esconden.

Detalles que importan:

- Los modelos de LangChain y LangGraph son `ChatGoogleGenerativeAI` por cada modelo de la cadena y `ChatGroq` al final, unidos con `with_fallbacks`. Con tools, cada modelo recibe `bind_tools` antes de encadenarse.
- En LangGraph el `user_id` llega a las tools por `InjectedState`. No aparece en el schema que ve el modelo, así que no lo puede elegir. En LangChain se cierra sobre el `user_id` al construir las tools en cada petición.
- El grafo se compila una vez al arrancar. `recursion_limit=12` cumple el papel de `MAX_STEPS`.
- `prompt_version` en la traza queda como `langchain-v1` o `langgraph-v1` para comparar ejecuciones.
- Las guías de estudio están en [langchain.md](langchain.md) y [langgraph.md](langgraph.md).

## MCP

Las tres tools de RR. HH. se registran en un `McpServer` in-process (`tools/list` y `tools/call`). El agente no las importa sueltas: las recibe como `McpToolAdapter` a través de `McpClient`. `GET /mcp/tools` usa el mismo cliente, así el catálogo y el agente no se desalinean.

`search_documents` no va por MCP. Necesita el índice que vive en el proceso. Meterla en el servidor MCP obligaría a serializar el retriever o a duplicar la búsqueda.

El transporte es una llamada en memoria. En producción ese servidor iría por stdio o SSE y esta app solo conocería el cliente. El protocolo ya es el de listar y llamar, para no atar el agente al import de Python.

## Lakehouse

Hay dos backends detrás de `LakehousePort`.

- `local`: JSON en `data/lakehouse`. Es el de los tests.
- `databricks`: Delta en el workspace personal, catálogo `knowledge_assistant`, esquemas `bronze`, `silver` y `gold`.

El medallón separa ingestión, limpieza y servicio:

- Bronce: `INSERT OVERWRITE` de los cuatro documentos, tal cual.
- Plata: `MERGE` que recorta categoría y calcula `content_length`.
- Oro de documentos: join con el equipo dueño (hr → People, security → Security, product → Product, customer → Support).
- Oro de conteos: `GROUP BY category`.

El chat arranca leyendo el oro. Si esa tabla está vacía, el índice no se construye con basura: `load_gold_documents` falla. El historial Delta (`DESCRIBE HISTORY`, `VERSION AS OF`) permite mirar una versión anterior sin un almacén aparte.

### Por qué la CLI y no un token en el código

`DatabricksCliSqlClient` no lee el PAT. Ejecuta `databricks api post /api/2.0/sql/statements` con el perfil `dbc-a6df516d-a455`. El token OAuth está en el llavero del sistema y el host en `~/.databrickscfg`. El proceso de la app no ve el secreto. SQL no tiene comando propio en la CLI, por eso se usa el statement API del warehouse y se hace poll si el estado es `PENDING` o `RUNNING`. El warehouse del free tier no se puede borrar ni duplicar; se reutiliza el Serverless Starter Warehouse.

Los identificadores SQL pasan por `quote_identifier` con una allowlist `[A-Za-z_][A-Za-z0-9_]*`. El catálogo y el esquema no se interpolan desde el usuario.

## LLMOps

El ciclo es: cada respuesta deja una traza, el usuario la califica, las métricas se agrupan por orquestador y modelo, y una evaluación fija decide si un cambio se puede subir. Todo vive en `app/llmops` y en los servicios de observabilidad y evaluación.

### Guardrails

`check_input` rechaza frases de inyección (`ignore previous instructions`, `reveal the system prompt`, `you are now`) con HTTP 400. `check_output` sustituye la respuesta si el modelo intenta volcar el system prompt. Una petición bloqueada también deja traza, con modo `blocked` y el motivo.

### Trazas

Cada `/chat` escribe una traza: `request_id`, fecha, pregunta, usuario, modelo, versión de prompt, modo (`rag`, `agent` o `blocked`), latencia, tokens, coste, documentos recuperados, tools y feedback.

- Los tokens salen del proveedor: `total_input_tokens` y `total_output_tokens` en la Interactions API, `usage_metadata` en LangChain. En el agente se suman planner y writer (o cada vuelta del grafo). Solo si ambos contadores siguen en cero se estiman con caracteres / 4.
- El coste usa tarifas de referencia (`input_token_rate`, `output_token_rate`), así `/metrics` tiene forma aunque el proveedor no devuelva el usage.
- `TraceStore` guarda en memoria y agrega cada evento a `data/llmops/traces.jsonl`. Al arrancar relee el archivo, así un reload de uvicorn no borra el historial. El archivo es de solo agregar: el feedback es un evento aparte (`type: feedback`) y no reescribe la línea de la traza. Si el proceso muere a mitad de escritura, se pierde como mucho la última línea.
- Por qué JSONL y no una base de datos: es un proceso, un escritor y pocas peticiones. Un archivo se lee con `jq` y se puede cargar a una tabla Delta sin traducir. Con varias réplicas iría a una tabla o a un colector OpenTelemetry.
- La traza guarda la pregunta del usuario. Por eso el archivo está en `.gitignore` y `TRACES_PATH=` vacío lo deja solo en memoria.

### Feedback

`POST /feedback` recibe `request_id`, `up` o `down` y un comentario opcional. Devuelve 404 si la traza no existe, así un voto no queda huérfano. La interfaz muestra 👍 y 👎 debajo de cada respuesta.

La satisfacción (`up / (up + down)`) es la única señal que viene del usuario y no del sistema. Una respuesta rápida y barata que la gente vota 👎 es un problema que la latencia no muestra.

### Métricas

`GET /metrics` devuelve el total y dos agrupaciones: `by_prompt_version` y `by_model`. `prompt_version` es `v1`, `langchain-v1` o `langgraph-v1`, así que la primera tabla compara los tres orquestadores con las mismas preguntas: latencia media y p95, tokens, coste, satisfacción y bloqueos. `by_model` muestra cuánto tráfico cae a los fallbacks (por ejemplo `gemini-3.5-flash-lite` cuando 3.6 da 429).

### Evaluación

`data/eval/questions.json` tiene siete casos. Cada caso declara solo lo que se revisa:

| Chequeo | Cuándo aplica | Qué mide |
| --- | --- | --- |
| `route` | Siempre | El modo fue `rag`, `agent` o `blocked` según lo esperado |
| `retrieval` | `expected_document` | El documento correcto está entre las fuentes |
| `tools` | `expected_tools` | Se llamaron esas tools |
| `generation` | `expected_phrases` | La respuesta contiene las frases (por ejemplo “8” o “not allowed”) |
| `forbidden` | `forbidden_phrases` | La respuesta no contiene la frase (Ana no debe recibir “not allowed”) |

Los casos cubren tres políticas, el saldo de Juan, la solicitud de Ana, la solicitud negada a Juan y una inyección de prompt. La evaluación pasa por `ChatService.run`: guardrails, ruteo y el orquestador activo, igual que `/chat`, pero sin escribir traza, para que no cambie `/metrics`.

`POST /evaluations` devuelve el informe y agrega un resumen a `data/llmops/evaluations.jsonl`. `GET /evaluations` lista las corridas anteriores con su `prompt_version`, así se ve si un cambio de chunk, prompt u orquestador bajó la tasa.

El filtro de calidad para CI:

```
cd backend && .venv/bin/python -m app.llmops.gate --min-pass-rate 0.85
```

Imprime cada caso con sus chequeos fallidos y sale con código 1 si la tasa queda por debajo del mínimo. En modo extractivo corre sin red; con Gemini mide el modelo real.

Las comparaciones por frase son deliberadamente simples. Un juez LLM (groundedness, relevancia) daría una señal más fina, pero cuesta cuota en cada corrida y también se equivoca. Para siete casos con respuestas cortas, una frase exacta es más barata y reproducible.

### Panel

`/ops` en el frontend muestra las métricas, las dos agrupaciones, las últimas 20 trazas con su voto y un botón para correr la evaluación con su historial. Se refresca cada 15 segundos.

## Frontend

Vite, React, TypeScript y Tailwind. TanStack Query guarda el estado de la petición (`isPending`, error, respuesta). TanStack Router deja la pantalla en `/` con un sitio claro para más rutas. react-hook-form y Zod validan el compositor (pregunta de 1 a 4000 caracteres y empleado opcional). El proxy de Vite manda `/api` a `http://127.0.0.1:8000` y le quita el prefijo.

La cromática de la interfaz está en español o en inglés (`localStorage`, clave `ka-locale`). Las preguntas de ejemplo siguen en inglés en los dos idiomas: el índice está en inglés y una pregunta en español recupera peor. El botón del encabezado cambia solo la interfaz.

La guía de la pantalla vacía separa políticas (se envían al pulsar) de preguntas de empleado (rellenan el selector y el texto, y la persona pulsa Preguntar). Eso evita mandar “crea una solicitud” sin haber elegido a Ana Gomez o a Juan Perez. Con la conversación ya empezada, el botón **ⓘ Guía** del encabezado abre la misma guía en un `<dialog>` nativo.

Cada respuesta muestra tokens de entrada, tokens de salida, latencia y los botones de feedback. El enlace **Ops** del encabezado abre el panel de LLMOps. Las fuentes se deduplican por documento: las que la respuesta nombra van primero y el resto queda plegado en “También consultados”.

`fetch` corta a los 90 segundos. Sin ese límite, un reload de uvicorn a mitad de la llamada deja el botón en “Buscando…” para siempre. Con `gemini-3.5-flash` una respuesta tarda entre 20 y 40 segundos, así que el límite deja margen.

## Guía de estudio

Resumen para la entrevista: el recorrido completo y qué papel cumple cada pieza.

### Vista general

```
                         USER
                           │
                           ▼
                    React Frontend
                           │
                       POST /chat
                           │
                           ▼
                    ┌─────────────┐
                    │   FastAPI   │
                    └──────┬──────┘
                           │
                      ChatService
                           │
                    Input Guardrail
                           │
                           ▼
                 ┌───────────────────┐
                 │    ORCHESTRATOR   │
                 │  native           │
                 │  langchain        │
                 │  langgraph        │
                 └─────────┬─────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
               RAG                  AGENT
                │                     │
                │                     ▼
                │                   Tools (MCP)
                │               ┌─────┼─────┐
                │            Profile Balance HR Request
                ▼
        Databricks Gold
        gold.documents
                │
                ▼
          TF-IDF Index
                │
                ▼
            Retriever
                │
                ▼
             Reranker
                │
                ▼
               LLM
                │
                ▼
         Output Guardrail
                │
                ▼
     Trace → data/llmops/traces.jsonl
```

### Databricks: qué papel juega

Databricks es la plataforma de datos. Prepara y sirve los documentos que alimentan el RAG, pero **no es el RAG**.

```
Documents → Bronze → Silver → Gold
```

- **Bronze:** los documentos llegan tal cual (`vacations.md`, `security.md`, `support.md`, `product_vision.md`).
- **Silver:** se limpian y transforman (`category = trim(category)`, `content_length`).
- **Gold:** la capa que consume la aplicación, `knowledge_assistant.gold.documents`.

### Qué ocurre después de Gold

Aquí entra el RAG. El corpus es pequeño, por eso el índice vive en memoria.

```
gold.documents → load_gold_documents() → chunks → TF-IDF → índice en RAM
```

Cuando llega una pregunta como “How many vacation days can I carry over?”:

```
Question → TF-IDF vector → cosine similarity → top 10 candidatos → lexical reranker → top 3 chunks → LLM
```

### Por qué existe el reranker

El primer resultado de TF-IDF no siempre es el mejor. El coseno puede poner Product Overview por encima de Vacation Policy. El reranker mira el solapamiento de términos de la pregunta y sube el chunk que realmente los menciona.

No es perfecto: para “What is the vacation policy?” Product Overview sigue quedando primero. Vacation Policy entra igual en el top 3 y el LLM la usa. Por eso la evaluación comprueba que el documento esté entre las fuentes, no que sea el primero.

### Dónde entra el LLM

```
Question + chunks relevantes → LLM → Answer
```

El prompt le exige responder solo con los extractos, nombrar el documento y copiar cada número y excepción. Así se evita que invente políticas. El RAG es **retrieval + grounded generation**.

### El agente

“How many vacation days do I have?” no se responde con RAG: la política dice cuántos días da la empresa, no cuántos le quedan a Juan.

```
Question → Agent → get_employee_profile + get_vacation_balance → LLM → "Juan Perez, you have 8 vacation days left."
```

### Leer y escribir

```
READ
 ├── get_employee_profile
 ├── get_vacation_balance
 └── search_documents

WRITE
 └── create_hr_request
```

Crear una solicitud es una acción, no una consulta. Por eso pasa por autorización:

```
User → Agent → create_hr_request → authorize_tool() → ¿tiene permiso?
                                                       ├── NO  → error (emp-1, Juan)
                                                       └── SÍ  → execute (emp-2, Ana)
```

Segunda protección: si el modelo dice `user_id = emp-2`, la aplicación no le cree. Cada orquestador lo resuelve a su manera:

- **Native:** `_with_user` pisa el argumento con el `user_id` de la petición.
- **LangChain:** `ScopedTools` construye las tools por petición, ya atadas al `user_id`.
- **LangGraph:** `InjectedState("user_id")` saca el argumento del schema que ve el modelo y lo llena desde el estado.

### MCP

MCP es la forma de exponer las tools de RR. HH. En lugar de que el agente importe `get_vacation_balance`, pasa por el protocolo:

```
Agent → MCP Client → MCP Server → tools/list, tools/call → HR tools
```

El agente descubre las tools por protocolo. Hoy el servidor corre in-process; en producción iría separado (stdio o SSE).

### Native, LangChain y LangGraph

No son tres arquitecturas: es el mismo sistema con tres formas de orquestar el LLM y el agente.

```
                  MISMO SISTEMA
                       │
                  ChatService
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Native       LangChain    LangGraph
```

Los tres comparten documentos, índice, tools, MCP, autorización, guardrails, trazas y evaluación.

**Native.** La implementación manual: llama al modelo, interpreta el JSON del planner, ejecuta tools, vuelve a llamar al modelo, maneja el fallback y controla el loop. Sirve para ver qué hay debajo de los frameworks.

```
Planner → ¿tools?
            ├── NO → RAG
            └── SÍ → Agent
```

**LangChain.** Lo mismo con las abstracciones del framework: LCEL (`prompt | model`), `ChatGoogleGenerativeAI`, `ChatGroq`, `BaseRetriever`, `StructuredTool`, `bind_tools`, `with_structured_output`, `with_fallbacks`.

```
model → tool_calls → ToolMessage → model
```

El repo demuestra: “I understand both the underlying implementation and the framework abstraction.”

**LangGraph.** Cambia la forma de representar el flujo. En lugar de `for step in range(MAX_STEPS)`, hay un grafo:

```
              State
                │
              route
             /  │  \
      retrieve  │   agent ⇄ tools
         │   missing_user   │
      generate  │         finish
         │      │           │
         └──────┴─── END ───┘
```

- **State:** lo que viaja por el flujo (question, user_id, documents, messages, answer, tokens).
- **Node:** una función que hace algo (route, retrieve, generate, agent, tools, finish).
- **Edge:** qué nodo viene después (agent → tools, tools → agent, agent → finish).

LangGraph es útil cuando el flujo tiene ciclos, estado y decisiones.

### Qué cubre el repo

```
                 ENTERPRISE GENAI APP
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
      Data              AI              Operations
        │                │                 │
   Databricks          RAG              LLMOps
   Delta               Agents           Tracing + feedback
   Bronze/Silver       Tools            Evaluation + gate
   Gold                MCP              Cost, guardrails
        │                │                 │
        └────────────────┼─────────────────┘
                         │
                  FastAPI / React
```

### LLMOps

Cada respuesta deja una traza persistente con request_id, usuario, pregunta, modelo, prompt_version, modo, latencia, tokens, coste, documentos, tools y feedback. Con eso se responde:

- ¿Cuánto tarda y cuánto cuesta?
- ¿Qué modelo respondió? ¿Cuánto cae a los fallbacks?
- ¿Qué documentos y tools usó?
- ¿Qué orquestador estaba activo y cuál rinde mejor?
- ¿Al usuario le sirvió (👍 / 👎)?
- ¿Un cambio de prompt, chunk u orquestador empeoró la calidad? (evaluación de 7 casos con historial y filtro de CI)

Endpoints: `/traces`, `/metrics`, `/feedback`, `/evaluations`. Panel: `/ops`.

### El recorrido para la entrevista

No hace falta memorizar los archivos, sino este recorrido:

```
USER → React → FastAPI → Guardrail → ORCHESTRATOR
                                        ├── RAG   → Databricks Gold → Retriever → LLM
                                        └── AGENT → MCP Tools → datos o acción de RR. HH.
                                     → Guardrail → Trace / LLMOps
```

| Pieza | Papel |
| --- | --- |
| Databricks | Datos |
| RAG | Buscar conocimiento |
| LLM | Generar lenguaje |
| Agent | Decidir y usar herramientas |
| Tools | Acceder a sistemas o ejecutar acciones |
| MCP | Protocolo para exponer y descubrir tools |
| LangChain | Framework para construir componentes y apps LLM |
| LangGraph | Framework para orquestar flujos y agentes con estado |
| LLMOps | Operar, evaluar, monitorear y gobernar la app LLM |
| FastAPI / React | API e interfaz |

La frase para decir de memoria:

> “This project is an enterprise GenAI assistant that combines RAG for company knowledge with an agent for employee-specific data and actions. Databricks provides the curated data layer, MCP exposes the HR tools, and I implemented the orchestration three ways: a native implementation, LangChain, and LangGraph. This allows me to compare the abstractions while keeping the same data, tools, authorization, and evaluation pipeline.”

Si puedes explicar ese recorrido sin mirar el README, entiendes el proyecto y no solo sigues el código.
