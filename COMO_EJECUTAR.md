# Cómo ejecutar NaviRag Trading en Windows

Guía diseñada para **Windows usando PowerShell**.

Esta guía asume el caso de un usuario que parte desde cero:

1. Clona el proyecto.
2. Crea/configura `.env`.
3. Configura MongoDB Atlas y permite su IP.
4. Agrega PDFs a `data/raw/`.
5. Prepara el entorno de ejecución:
   - Camino A: `.venv`
   - Camino B: Docker
6. Crea el índice vectorial.
7. Ejecuta la ingesta.
8. Ejecuta Streamlit.

> Clonar el repositorio no basta. El proyecto depende de GitHub Models, MongoDB Atlas, variables locales, índice vectorial y documentos cargados.

---

## 1. Clonar proyecto

Abrir PowerShell y ejecutar:

```powershell
git clone https://github.com/Fergchis/NaviRag_Trading.git
cd NaviRag_Trading
git checkout version-2
```

## 2. Crear/configurar `.env`

Crear un archivo `.env` en la raíz del proyecto.

Usar `.env.example` como referencia.

No subir `.env` a GitHub.

## 3. Configurar MongoDB Atlas y permitir IP

Antes de ejecutar el proyecto, MongoDB Atlas debe estar preparado.

En MongoDB Atlas:

1. Crear o usar un cluster activo.
2. Crear usuario y contraseña de base de datos.
3. Copiar el connection string en `MONGODB_CONNECTION_STRING`.
4. Ir a **Network Access**.
5. Agregar la IP pública del PC.
6. Confirmar que los nombres del `.env` serán los usados por el proyecto:
   - `MONGODB_DATABASE`
   - `MONGODB_COLLECTION`
   - `MONGODB_VECTOR_INDEX`

Si la IP pública del PC no está permitida en MongoDB Atlas, la aplicación puede fallar al recuperar contexto.

## 4. Agregar PDFs a `data/raw/`

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

## 5. Preparar el entorno de ejecución

En este punto se debe elegir una de las dos formas de ejecución:

- **Camino A:** usar `.venv`.
- **Camino B:** usar Docker.

No es necesario usar ambos caminos.

### 5A. Preparar entorno con `.venv`

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

### 5B. Preparar entorno con Docker

Usar este camino si se quiere evitar crear `.venv` manualmente.

Requisitos:

1. Docker Desktop instalado.
2. Docker Desktop abierto.
3. `.env` configurado.
4. MongoDB Atlas accesible.
5. IP pública permitida en Atlas.

Desde la raíz del proyecto:

```powershell
docker build -t navirag-trading .
```

## 6. Crear índice vectorial

Este paso crea o configura el índice vectorial en MongoDB Atlas.

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe create_vector_index.py
```

### Si usas Docker

```powershell
docker run --rm --env-file .env navirag-trading python create_vector_index.py
```

## 7. Ejecutar ingesta

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

## 8. Ejecutar Streamlit

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

## 9. Ejecutar casos EV2

Los casos validan las rutas actuales `FINISH`, `answer_agent`, `memory_agent`, `rag_agent` y `rag_then_answer` sin usar Streamlit ni RAGAS.

### Si usas `.venv`

```powershell
.\.venv\Scripts\python.exe eval\run_casos_ev2.py
```

### Si usas Docker

```powershell
docker run --rm --env-file .env navirag-trading python eval/run_casos_ev2.py
```

