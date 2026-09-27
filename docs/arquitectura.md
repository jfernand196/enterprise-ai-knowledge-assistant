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
            →  traza (latencia, tokens, coste, docs, tools)
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

## Guardrails y trazas

`check_input` rechaza frases de inyección (`ignore previous instructions`, `reveal the system prompt`, `you are now`) con HTTP 400. `check_output` sustituye la respuesta si el modelo intenta volcar el system prompt.

Cada `/chat` escribe una traza: `request_id`, usuario, modelo, versión de prompt, modo (`rag`, `agent` o `blocked`), latencia, tokens, coste, documentos recuperados y tools. Los tokens salen del proveedor: `total_input_tokens` y `total_output_tokens` en la Interactions API, `usage_metadata` en LangChain. En el agente se suman planner y writer (o cada vuelta del grafo). Solo si ambos contadores siguen en cero se estiman con caracteres / 4. El coste usa tarifas de referencia (`input_token_rate`, `output_token_rate`) para que `/metrics` tenga forma aunque el proveedor no devuelva el usage. `GET /traces` y `GET /traces/{request_id}` exponen eso.

`POST /evaluations` corre el conjunto de `data/eval/questions.json` contra el mismo RAG. Sirve para ver si un cambio de chunk o de prompt empeora las respuestas de política, no para atender al usuario.

## Frontend

Vite, React, TypeScript y Tailwind. TanStack Query guarda el estado de la petición (`isPending`, error, respuesta). TanStack Router deja la pantalla en `/` con un sitio claro para más rutas. react-hook-form y Zod validan el compositor (pregunta de 1 a 4000 caracteres y empleado opcional). El proxy de Vite manda `/api` a `http://127.0.0.1:8000` y le quita el prefijo.

La cromática de la interfaz está en español o en inglés (`localStorage`, clave `ka-locale`). Las preguntas de ejemplo siguen en inglés en los dos idiomas: el índice está en inglés y una pregunta en español recupera peor. El botón del encabezado cambia solo la interfaz.

La guía de la pantalla vacía separa políticas (se envían al pulsar) de preguntas de empleado (rellenan el selector y el texto, y la persona pulsa Preguntar). Eso evita mandar “crea una solicitud” sin haber elegido a Ana Gomez o a Juan Perez. Con la conversación ya empezada, el botón **ⓘ Guía** del encabezado abre la misma guía en un `<dialog>` nativo.

Cada respuesta muestra tokens de entrada, tokens de salida y latencia. Las fuentes se deduplican por documento: las que la respuesta nombra van primero y el resto queda plegado en “También consultados”.

`fetch` corta a los 90 segundos. Sin ese límite, un reload de uvicorn a mitad de la llamada deja el botón en “Buscando…” para siempre. Con `gemini-3.5-flash` una respuesta tarda entre 20 y 40 segundos, así que el límite deja margen.
