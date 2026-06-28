# Cómo ejecutar NaviRAG Trading en Windows

Guía diseñada para Windows usando PowerShell.

Esta guía asume el caso de un usuario que parte desde cero:

1. Clona el proyecto en la rama `version-3`.
2. Crea y configura `.env`.
3. Configura MongoDB Atlas y permite su IP.
4. Configura Supabase para observabilidad EV3.
5. Agrega PDFs a `data/raw/`.
6. Prepara el entorno de ejecución con `.venv` o Docker.
7. Crea el índice vectorial.
8. Ejecuta la ingesta.
9. Ejecuta Streamlit.
10. Ejecuta los casos EV3 si necesita regenerar evidencia.

> Clonar el repositorio no basta. El proyecto depende de GitHub Models, MongoDB Atlas, Supabase, variables locales, índice vectorial y documentos cargados.

---

## 1. Clonar proyecto

Abrir PowerShell y ejecutar:

```powershell
git clone https://github.com/Fergchis/NaviRag_Trading.git
cd NaviRag_Trading
git checkout version-3
```

## 2. Crear/configurar `.env`

Crear un archivo `.env` en la raíz del proyecto.

Usar `.env.example` como referencia. No subir `.env` a GitHub.

Variables principales:

```env
APP_ENV=local
GITHUB_TOKEN=
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_CHAT_MODEL=openai/gpt-4o-mini
GITHUB_MODELS_EMBEDDINGS_ENDPOINT=https://models.github.ai/inference/embeddings
GITHUB_MODELS_CHAT_ENDPOINT=https://models.github.ai/inference/chat/completions

MONGODB_CONNECTION_STRING=
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index

SUPABASE_URL=
SUPABASE_KEY=
```

`SUPABASE_URL` y `SUPABASE_KEY` se usan para registrar observabilidad EV3 en Supabase. No pegues secretos reales en documentación, commits o capturas.

## 3. Configurar MongoDB Atlas y permitir IP

Antes de ejecutar el proyecto, MongoDB Atlas debe estar preparado.

En MongoDB Atlas:

1. Crear o usar un cluster activo.
2. Crear usuario y contraseña de base de datos.
3. Copiar el connection string en `MONGODB_CONNECTION_STRING`.
4. Ir a **Network Access**.
5. Agregar la IP pública del PC.
6. Confirmar que los nombres del `.env` sean los usados por el proyecto:
   - `MONGODB_DATABASE`
   - `MONGODB_COLLECTION`
   - `MONGODB_VECTOR_INDEX`

Si la IP pública del PC no está permitida en MongoDB Atlas, la aplicación puede fallar al recuperar contexto.

## 4. Configurar Supabase y Power BI

La observabilidad EV3 usa Supabase como backend y Power BI como dashboard visual.

Consulta [GUIA_POWERBI.md](GUIA_POWERBI.md) para:

- crear el proyecto Supabase;
- ejecutar `schema.sql`;
- obtener `SUPABASE_URL` y `SUPABASE_KEY`;
- conectar Power BI a las tablas de Supabase;
- guardar `PowerBI.pbix` localmente.

`PowerBI.pbix` está ignorado por Git y no se versiona.

## 5. Agregar PDFs a `data/raw/`

Si el usuario está usando una base nueva o vacía, debe agregar PDFs en:

```text
data/raw/
```

Ejemplo:

```text
data/raw/algo_fundamentals.pdf
data/raw/otro_libro_de_trading.pdf
```

Si MongoDB Atlas ya tiene documentos ingeridos y el índice vectorial existe, este paso puede omitirse.

## 6. Preparar el entorno de ejecución

En este punto se debe elegir una de las dos formas de ejecución:

- **Camino A:** usar `.venv`.
- **Camino B:** usar Docker.

No es necesario usar ambos caminos.

### 6A. Preparar entorno con `.venv`

Usar este camino si se quiere ejecutar el proyecto con Python local y entorno virtual.

Desde la raíz del proyecto:

```powershell
python -m venv .venv
```

Instalar dependencias usando el Python del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.venv` no debe subirse a GitHub. Se genera localmente en cada PC.

### 6B. Preparar entorno con Docker

Usar este camino si se quiere evitar crear `.venv` manualmente.

Requisitos:

1. Docker Desktop instalado.
2. Docker Desktop abierto.
3. `.env` configurado.
4. MongoDB Atlas accesible.
5. Supabase configurado con `schema.sql`.
6. IP pública permitida en Atlas.

Desde la raíz del proyecto:

```powershell
docker build -t navirag-trading .
```

## 7. Crear índice vectorial

Este paso crea o configura el índice vectorial en MongoDB Atlas.

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe create_vector_index.py
```

### Si usas Docker

```powershell
docker run --rm --env-file .env navirag-trading python create_vector_index.py
```

## 8. Ejecutar ingesta

Ejecutar este paso si se agregaron PDFs en `data/raw/` y se necesita cargar la base documental en MongoDB Atlas.

La ingesta lee los PDFs, genera embeddings y guarda chunks en MongoDB Atlas.

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"
```

### Si usas Docker

```powershell
docker run --rm --env-file .env -v "${PWD}\data\raw:/app/data/raw" navirag-trading python -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"
```

## 9. Ejecutar Streamlit

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Si usas Docker

```powershell
docker run --rm -p 8501:8501 --env-file .env navirag-trading
```

Luego abrir en el navegador:

```text
http://localhost:8501
```

Después de hacer una pregunta, la app registra sesiones, mensajes, trazas y costos en Supabase si las credenciales están configuradas correctamente.

## 10. Ejecutar casos EV3

Los casos EV3 validan el comportamiento del agente y generan evidencia local en `eval/resultados_ev3.json`.

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe eval\run_casos_ev3.py
```

### Si usas Docker

```powershell
docker run --rm --env-file .env navirag-trading python eval/run_casos_ev3.py
```

### Evidencia generada

`eval/resultados_ev3.json` es el snapshot de evidencia de las pruebas EV3. El runner `eval/run_casos_ev3.py` sobrescribe este archivo cada vez que se ejecutan los casos.

Antes de commitear resultados nuevos, revisa el diff y confirma que corresponde a una ejecución válida y no contiene información sensible.
