# Bot RPA · Registro de Ingresos PeopleSync

Bot de automatización (RPA) en **Python + Selenium** que lee un dataset de
50 empleados desde un archivo Excel y registra cada alta en el formulario
web **PeopleSync HRIS**
(`https://the-paul2002.github.io/Proyecto-IA-/Homework1/`), verificando
cada registro antes de continuar con el siguiente, todo dentro de la misma
sesión de navegador y sin recargar la página.

## Qué hace el bot

1. Lee `Ingreso_Personal_Agosto.xlsx` (ruta configurable) con pandas y
   normaliza los datos (fechas a `AAAA-MM-DD`, DNI/teléfono a texto, etc.).
2. Abre Chrome una sola vez y navega al formulario.
3. Por cada empleado: completa todos los campos, hace clic en
   **"Registrar Ingreso"** y verifica con `WebDriverWait` (nunca
   `time.sleep`) que el contador **"Ingresos registrados hoy"** incrementó
   y que apareció la fila correspondiente en la tabla, antes de pasar al
   siguiente.
4. Si un registro tiene datos inválidos o falla al registrarse, se loguea
   el motivo, se toma una captura de pantalla (solo en caso de error), se
   limpia el formulario y se continúa con el siguiente **sin detener el
   lote**.
5. Al final se loguea (consola + archivo) un resumen con: total de
   registros procesados, cuántos se cargaron exitosamente, cuántos no se
   pudieron cargar, y el detalle (DNI + motivo) de cada uno de estos
   últimos.
6. Además exporta un reporte `.xlsx` por corrida (ver
   [Contenido extra](#contenido-extra-reporte-exportado-a-excel)).

**Dato del dataset no compatible con el formulario:** el `<select
id="genero">` del formulario solo ofrece **"Masculino"** y **"Femenino"**,
pero el dataset incluye también **"No binario"** y **"Prefiero no
indicar"** (26 de 50 registros). Como el formulario no tiene una opción
válida para representarlos, el bot **omite esos registros por defecto** y
los reporta explícitamente como "no cargados" con el motivo exacto, en
lugar de forzar un valor incorrecto. Es configurable con
`GENERO_UNSUPPORTED_ACTION` (ver [Configuración](#configuración)). Con la
configuración por defecto, el resultado esperado de una corrida completa
es **24/50 cargados, 26 no cargados por género no soportado, 0 fallidos**.

## Requisitos previos

- **Python 3.10+**
- **Google Chrome** instalado (el driver se resuelve automáticamente con
  el Selenium Manager incorporado en Selenium >= 4.6, sin configuración
  adicional)
- Windows 10/11 (`run.bat` y las instrucciones de Task Scheduler están
  pensadas para Windows; el código Python es multiplataforma)
- Acceso a internet la primera vez que se ejecuta (para que Selenium
  descargue el chromedriver correspondiente; luego queda cacheado)

## Instalación

```powershell
cd ruta\al\proyecto

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

> **Dataset:** `Ingreso_Personal_Agosto.xlsx` no se incluye en el
> repositorio porque contiene datos personales (DNI, teléfono, correo,
> fecha de nacimiento). Colócalo en la raíz del proyecto (o cualquier ruta
> local) y apunta `EXCEL_PATH` en tu `.env` hacia esa ubicación.

## Configuración

Toda la configuración vive en `.env` (plantilla documentada en
[`.env.example`](.env.example)) y puede sobreescribirse por línea de
comandos. Nada está hardcodeado: URL, ruta del Excel, timeouts, modo
headless, carpetas de salida, etc. se leen de config.

| Variable | Descripción | Default |
|---|---|---|
| `FORM_URL` | URL del formulario | (obligatoria) |
| `EXCEL_PATH` | Ruta al Excel con el dataset | (obligatoria) |
| `EXCEL_SHEET_NAME` | Hoja a leer (vacío = primera) | vacío |
| `HEADLESS` | Chrome sin ventana visible | `false` |
| `EXPLICIT_WAIT_SECONDS` | Timeout de `WebDriverWait` | `15` |
| `IMPLICIT_WAIT_SECONDS` | Espera implícita del driver | `2` |
| `CHROMEDRIVER_PATH` | Ruta manual a chromedriver (solo sin internet) | vacío (auto) |
| `LOG_DIR` / `SCREENSHOT_DIR` / `REPORT_DIR` | Carpetas de salida | `./logs`, `./screenshots`, `./reports` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `STATE_FILE` | Archivo JSON para el modo resume | `./state/registrados.json` |
| `RESUME` | Saltar DNIs ya registrados en una corrida previa | `false` |
| `MAX_RECORDS` | Límite de registros a procesar (pruebas) | vacío (todos) |
| `GENERO_UNSUPPORTED_ACTION` | `skip` / `default` / `alternate` | `skip` |
| `GENERO_DEFAULT_VALUE` | Valor forzado si `GENERO_UNSUPPORTED_ACTION=default` | `Masculino` |

Todas estas variables también aceptan override por CLI (`--url`,
`--excel`, `--headless`/`--no-headless`, `--limit`, `--resume`, etc.).
Ejecuta `python run_bot.py --help` para ver la lista completa.

> **Sobre `RESUME`:** el formulario es 100% client-side (no hay backend),
> así que cada vez que se abre una ventana de Chrome nueva la tabla y el
> contador empiezan en cero. Por eso el default es `false`: cada corrida
> completa intenta los 50 registros de nuevo. Actívalo (`--resume`) solo
> si necesitas reanudar una corrida interrumpida a mitad de camino.

## Cómo ejecutar

```powershell
venv\Scripts\activate

# Prueba rápida con 1 registro, navegador visible
python run_bot.py --limit 1 --no-headless

# Lote completo (50 registros), headless (recomendado para Task Scheduler)
python run_bot.py --headless
```

También puede usarse `run.bat` (reenvía los argumentos):

```powershell
run.bat --headless
```

Al finalizar, el bot imprime (en consola y en `logs/registro_*.log`) un
resumen como:

```
RESUMEN FINAL
Total de registros procesados: 50
Registros cargados exitosamente: 24
Registros que NO se pudieron cargar: 26
  - DNI 48376941: Valor de género 'No binario' no está entre las opciones...
  ...
```

Cada registro fallido/omitido queda además con su propia línea en el log
durante la corrida, y ante cualquier excepción se guarda una captura en
`screenshots/error_<DNI>_<timestamp>.png`.

## Contenido extra: reporte exportado a Excel

Además del log de texto (que pide el enunciado), cada corrida genera
automáticamente un archivo `reports/reporte_<timestamp>.xlsx` con dos
hojas:

- **Resumen**: las mismas 4 métricas del log (total procesado, cargados,
  no cargados, omitidos por resume) en formato tabla.
- **Detalle**: una fila por cada empleado procesado, con `dni`, `nombres`,
  `estado` (`Cargado` / `No cargado` / `Omitido (resume)`) y `motivo`.

Esto da una evidencia estructurada y fácil de revisar/filtrar en Excel
(en vez de tener que leer el `.log` línea por línea), útil tanto para la
sustentación como para adjuntarla como evidencia en el repositorio. Se
implementa en [`src/report_writer.py`](src/report_writer.py) usando
`pandas`/`openpyxl` (dependencias ya usadas para leer el dataset de
entrada).

## Programar en Windows Task Scheduler

1. Abre **Programador de tareas** (`taskschd.msc`).
2. **Crear tarea básica** → nombre: `PeopleSync RPA - Registro de Ingresos`.
3. **Desencadenador**: la frecuencia que necesites (ej. diaria a una hora fija).
4. **Acción** → "Iniciar un programa":
   - **Programa/script**: ruta completa a `run.bat`, ej.
     `D:\Joaquin\UP\2026-2\DataScience\HW1\1RPA\run.bat`
   - **Agregar argumentos**: `--headless`
   - **Iniciar en**: la carpeta del proyecto, ej.
     `D:\Joaquin\UP\2026-2\DataScience\HW1\1RPA`
5. En **Propiedades → General**, marca "Ejecutar tanto si el usuario inició
   sesión como si no" si debe correr sin sesión activa, y "Ejecutar con
   los privilegios más altos" si Chrome headless lo requiere.
6. En **Condiciones**, desmarca "Iniciar la tarea solo si el equipo está
   conectado a la corriente alterna" si se ejecuta en un laptop.
7. Guarda y prueba con **Ejecutar** desde el propio Programador; revisa
   `logs/` para confirmar que corrió correctamente y generó el resumen.

`run.bat` se encarga de: ubicarse en la carpeta correcta (`cd /d %~dp0`
— por eso "Iniciar en" no es estrictamente necesario pero se recomienda
igual), activar `venv` si existe, ejecutar `run_bot.py` reenviando los
argumentos, y devolver el código de salida (0 = todo exitoso o solo
omisiones esperadas por dato inválido, 1 = hubo registros fallidos por
error técnico) para que Task Scheduler pueda detectar fallas.

**Importante:** no basta con crear la tarea — verifica que Windows la
ejecute correctamente (botón "Ejecutar" del Programador, columna "Último
resultado de ejecución" = `0x0`) y que se generen logs nuevos en `logs/`
tras cada corrida, ya que esto es parte de lo evaluado.

## Estructura del proyecto

```
1RPA/
├── src/
│   ├── config.py          # Config (.env + argparse), sin valores hardcodeados
│   ├── logger_setup.py    # Logging a consola + archivo con timestamp
│   ├── data_loader.py     # Lectura/normalización del Excel, mapeo de género
│   ├── driver_factory.py  # Construcción del WebDriver (Selenium Manager)
│   ├── form_page.py       # Page Object del formulario PeopleSync
│   ├── state_store.py     # Persistencia del modo resume (opcional)
│   ├── report_writer.py   # Extra: exporta reporte .xlsx por corrida
│   └── main.py            # Orquestador del flujo completo
├── logs/                  # Logs de ejecución (ignorado por git)
├── screenshots/           # Capturas de error (ignorado por git)
├── state/                 # Estado de resume (ignorado por git)
├── reports/               # Reportes .xlsx por corrida (ignorado por git)
├── run_bot.py             # Punto de entrada: python run_bot.py [opciones]
├── run.bat                # Wrapper para ejecución manual / Task Scheduler
├── requirements.txt
├── .env.example
└── .gitignore
```

## Troubleshooting

**`SessionNotCreatedException` / versión de ChromeDriver incompatible**
Actualiza Chrome, o borra la caché de Selenium Manager en
`%USERPROFILE%\.cache\selenium` para forzar una nueva resolución de
versión. Alternativamente define `CHROMEDRIVER_PATH` en `.env` apuntando
a un `chromedriver.exe` que coincida con tu versión de Chrome
(`chrome://version`).

**El bot no encuentra el Excel**
Verifica que `EXCEL_PATH` en `.env` sea correcto (relativo a la carpeta
desde donde se ejecuta, o usa ruta absoluta), o pásalo con
`--excel "C:\ruta\completa\archivo.xlsx"`.

**Quiero ver qué hace el bot paso a paso**
Corre con `--no-headless --limit 1`.
