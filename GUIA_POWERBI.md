# GUIA_POWERBI

## ¿Qué es esto?

Supabase almacena las sesiones, mensajes, trazas y costos generados por NaviRAG. Power BI lee esas tablas y permite visualizar métricas como latencia, tokens, costos, sesiones, mensajes y trazas.

## Requisitos

* Docker Desktop activo.
* Archivo `.env` local.
* Cuenta en Supabase.
* Power BI Desktop instalado.
* Proyecto NaviRAG clonado localmente.
* Archivo `schema.sql` disponible en la raíz del repo.

## 1. Crear proyecto en Supabase

1. Crear un nuevo proyecto en Supabase.
2. Usar un nombre claro, por ejemplo `navirag-ev3`.
3. Guardar la contraseña de base de datos en un lugar seguro.
4. Elegir la región más cercana, por ejemplo `Americas`.
5. Activar `Enable Data API`.
6. Activar `Automatically expose new tables`.
7. No activar automatic RLS. (opcional)
8. Crear el proyecto.

## 2. Crear tablas con schema.sql

1. Abrir el proyecto en Supabase.
2. Ir a `SQL Editor`.
3. Crear una nueva query.
4. Copiar el contenido completo de `schema.sql`.
5. Ejecutar con `Run`.
6. Si Supabase muestra advertencia de RLS, seleccionar `Run without RLS`.
7. Confirmar que existan estas tablas:

* `sessions`
* `messages`
* `traces`
* `model_pricing`
* `costs`
* `evaluations`

## 3. Obtener credenciales Supabase

1. Ir a `Project Settings`.
2. Entrar a `API Keys`.
3. Copiar `Project URL`.
4. Copiar la `Secret key` para uso local en backend.
5. No subir ni compartir la secret key.

## 4. Configurar .env

Agregar las variables de Supabase al archivo `.env` local:

```env
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_KEY=sb_secret_xxxxxxxxx
```

Notas:

* `.env` no se sube a Git.
* `.env.example` debe quedar sin secretos reales.
* No pegar la URL real ni la key real en documentación, chats o capturas.

## 5. Ejecutar NaviRAG con Docker

Desde PowerShell:

```powershell
cd "D:\Code\IA\EV3\NaviRAG"

docker build -t navirag-ev3 .

$APP = (Get-Location).Path

docker run --rm `
  --env-file "$APP\.env" `
  -p 8501:8501 `
  -v "$APP\data\raw:/app/data/raw:ro" `
  navirag-ev3
```

Abrir:

```text
http://localhost:8501
```

Hacer una pregunta corta para generar datos de observabilidad.

## 6. Validar datos en Supabase

En `SQL Editor`, ejecutar:

```sql
select 'sessions' as table_name, count(*) as rows from sessions
union all
select 'messages', count(*) from messages
union all
select 'traces', count(*) from traces
union all
select 'costs', count(*) from costs
union all
select 'model_pricing', count(*) from model_pricing
union all
select 'evaluations', count(*) from evaluations;
```

Resultado esperado después de una conversación (puede variar):

* `sessions` > 0
* `messages` > 0
* `traces` > 0
* `costs` > 0
* `model_pricing` = 7
* `evaluations` puede quedar 0

## 7. Instalar Power BI Desktop

1. Instalar Power BI Desktop desde Microsoft Store o Microsoft.
2. Abrir Power BI Desktop.
3. Crear un informe en blanco.

## 8. Conectar Power BI a Supabase

Método usado:

1. Ir a `Obtener datos`.
2. Elegir `Consulta en blanco`.
3. Abrir `Editor avanzado`.
4. Usar Power Query M con `Web.Contents` y headers.

Ejemplo para `sessions`:

```powerquery
let
    SupabaseUrl = "https://TU-PROYECTO.supabase.co",
    SupabaseKey = "sb_secret_xxxxxxxxx",
    Source = Json.Document(
        Web.Contents(
            SupabaseUrl & "/rest/v1/sessions?select=*",
            [
                Headers = [
                    apikey = SupabaseKey,
                    Authorization = "Bearer " & SupabaseKey
                ]
            ]
        )
    ),
    Table = Table.FromRecords(Source)
in
    Table
```

Para cargar otras tablas, duplicar la consulta y cambiar el endpoint:

* `/rest/v1/messages?select=*`
* `/rest/v1/traces?select=*`
* `/rest/v1/costs?select=*`
* `/rest/v1/model_pricing?select=*`

## 9. Guardar Power BI

Guardar el informe como:

```text
PowerBI.pbix
```

Ubicación recomendada:

```text
D:\Code\IA\EV3\NaviRAG\PowerBI.pbix
```

Notas:

* `PowerBI.pbix` está ignorado por Git.
* No subir el archivo si contiene claves o configuración sensible.
* Si se comparte el informe, revisar primero que no incluya credenciales guardadas.

## Notas de seguridad

* No compartir `.env`.
* No pegar `SUPABASE_KEY` en chats, README o capturas.
* Este proyecto usa RLS desactivado por ser una implementación académica local alineada con el enfoque simple de clase.
* Para producción real se deberían aplicar políticas RLS y credenciales de menor privilegio.
