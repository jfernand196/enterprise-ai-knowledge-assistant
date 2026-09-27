# LangChain en este repo

El asistente tiene dos implementaciones del mismo flujo:

- `native`: RAG y agente escritos a mano en `backend/app/rag` y `backend/app/agent`.
- `langchain`: el mismo flujo con LangChain en `backend/app/lc`.

Las dos usan el mismo índice (TF-IDF + rerank), las mismas tools (vía MCP), la misma regla de permisos (`create_hr_request` solo para `emp-2`) y el mismo `ChatService`, que aplica guardrails y escribe las trazas. Lo único que cambia es quién orquesta las llamadas al modelo. Así se pueden comparar las dos pieza por pieza.

## Cómo cambiar

En el `.env` de la raíz:

```
ORCHESTRATOR=langchain   # o native
```

Reinicia uvicorn. En `GET /traces`, las respuestas de LangChain llevan `prompt_version: langchain-v1`.

## Equivalencias

| Concepto | Native | LangChain | Archivo |
| --- | --- | --- | --- |
| Modelo | `httpx` contra la Interactions API de Gemini | `ChatGoogleGenerativeAI`, `ChatGroq` | `lc/models.py` |
| Fallback entre modelos | bucle `for model_id in self._models` | `primary.with_fallbacks([...])` | `lc/models.py` |
| Retriever | `Retriever.retrieve()` devuelve `ScoredChunk` | `BaseRetriever` devuelve `Document` | `lc/retriever.py` |
| Prompt | f-string | `ChatPromptTemplate` | `lc/rag_chain.py` |
| Pipeline RAG | llamadas en secuencia dentro de `RagService` | cadena LCEL con `\|` | `lc/rag_chain.py` |
| Sin contexto, no llamar al modelo | `if not chunks` | `RunnableBranch` | `lc/rag_chain.py` |
| Router RAG o agente | el modelo devuelve JSON y lo parseamos | `with_structured_output(Route)` | `lc/router.py` |
| Tools | `ToolPort` + `ToolRegistry` | `StructuredTool` con esquema generado desde la firma | `lc/tools.py` |
| Elegir tools | el modelo escribe un plan JSON | `bind_tools` y el modelo devuelve `tool_calls` | `lc/agent.py` |
| Bucle del agente | un solo plan, luego ejecutar | bucle: modelo → `tool_calls` → `ToolMessage` → modelo | `lc/agent.py` |
| Tokens | leer `usage` del JSON a mano | `AIMessage.usage_metadata` | `lc/models.py` |

## Orden de lectura

1. **`lc/models.py`.** Un `BaseChatModel` es una interfaz común: `ChatGoogleGenerativeAI` y `ChatGroq` se usan igual (`invoke`, `ainvoke`, `bind_tools`). `with_fallbacks` envuelve varios modelos en uno solo. Si Gemini 3.6 devuelve 429, pasa a 3.5 y después a Groq sin que el resto del código lo sepa. Ojo: las tools se atan a cada modelo antes de encadenarlos, porque atarlas después solo llegaría al primero.

2. **`lc/retriever.py`.** Adapta el retriever que ya teníamos a `BaseRetriever`. Un retriever de LangChain es un `Runnable`: recibe un texto y devuelve una lista de `Document` (`page_content` + `metadata`). No hace falta cambiar de vector store para usar LangChain; basta con adaptar el que hay.

3. **`lc/rag_chain.py`.** LCEL (LangChain Expression Language). El operador `|` conecta `Runnable`s: la salida de uno es la entrada del siguiente.
   - `RunnableParallel(documents=retriever, question=RunnablePassthrough())` corre el retriever y conserva la pregunta.
   - `RunnablePassthrough.assign(context=...)` añade una clave al diccionario sin perder las demás.
   - `RunnableBranch` elige camino: sin documentos devuelve la respuesta fija y no gasta tokens.
   - `RAG_PROMPT | model` rellena la plantilla y llama al modelo.

   La cadena devuelve el `AIMessage` completo, no solo el texto, porque ahí vienen el nombre del modelo y los tokens.

4. **`lc/router.py`.** `with_structured_output(Route)` hace que el modelo devuelva un objeto Pydantic en lugar de texto. El native pide JSON en el prompt y lo parsea; si el JSON sale mal, falla. Aquí LangChain usa el tool calling del proveedor para forzar el esquema.

5. **`lc/tools.py`.** `StructuredTool.from_function` genera el esquema JSON que ve el modelo a partir de la firma y los tipos de la función. Las tools se crean por petición con el `user_id` ya fijado, así que el modelo no ve ese argumento y no puede pedir datos de otro empleado. Cada llamada pasa por `authorize_tool` y por el mismo `ToolRegistry` del native.

6. **`lc/agent.py`.** El bucle de un agente con tool calling, escrito a mano para ver cada paso:
   1. El modelo recibe los mensajes y devuelve un `AIMessage`.
   2. Si trae `tool_calls`, se ejecuta cada una y el resultado vuelve como `ToolMessage` con el mismo `tool_call_id`.
   3. Se repite hasta que el modelo responde sin `tool_calls` o se llega a `MAX_STEPS`.

   Es lo que hacen por dentro `create_agent` de LangChain y `create_react_agent` de LangGraph. Aquí no se usan para que el bucle quede a la vista.

7. **`lc/services.py`.** Expone las cadenas con la misma interfaz que el native (`answer(payload, request_id)` y `needs_tools`). Por eso `ChatService`, los guardrails, las trazas y el frontend no cambian.

## Qué gana y qué cuesta

Gana:

- Cambiar de proveedor es cambiar una clase. Groq, OpenAI o Anthropic implementan el mismo `BaseChatModel`.
- Tool calling y salida estructurada nativos del proveedor, en vez de pedir JSON en el prompt.
- `usage_metadata` normalizado entre proveedores.
- Integración directa con LangSmith para ver cada paso de la cadena si se configura `LANGSMITH_API_KEY`.

Cuesta:

- Más dependencias y más capas entre el código y la API.
- Los errores vienen envueltos en excepciones de LangChain, y hay que conocer la librería para depurarlos.
- Las versiones cambian rápido. Este repo fija `langchain-core==1.6.5` en `requirements.txt`.

## Pruebas

`backend/tests/test_langchain.py` corre sin red. Usa `FakeMessagesListChatModel`, un modelo falso de `langchain_core` que devuelve mensajes preparados, incluidos `tool_calls`. Así se prueban la cadena y el bucle del agente sin claves ni cuota.

## Siguientes pasos para estudiar

- Cambiar el bucle de `lc/agent.py` por `create_react_agent` de LangGraph y comparar.
- Reemplazar `IndexRetriever` por un vector store de LangChain (`InMemoryVectorStore` con `GoogleGenerativeAIEmbeddings`) y medir con `POST /evaluations`.
- Activar LangSmith y mirar la traza de una pregunta de agente.
