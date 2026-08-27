# Web Scraping — Tipo de Cambio Oficial SUNAT

Bot en Python + Selenium que extrae del portal oficial de SUNAT
([e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias](https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias))
el tipo de cambio (compra y venta) publicado día por día, desde enero 2024 hasta
el mes actual, y lo consolida en un único CSV.

## Qué hace el script

1. Abre el portal con Chrome controlado por Selenium.
2. Lee el mes/año que el calendario muestra por defecto (el actual) y retrocede
   con el botón `<` hasta llegar al mes de inicio pedido.
3. Desde ahí avanza mes a mes con el botón `>`, y en cada mes lee las celdas
   del calendario (`td.calendar-day.current`) para extraer día, tipo de
   cambio de compra y de venta.
4. Cada navegación espera explícitamente (`WebDriverWait`) a que la etiqueta
   de mes/año cambie y a que los datos del nuevo mes estén renderizados, y
   además respeta una pausa configurable entre peticiones para no saturar el
   portal.
5. Si un día no tiene compra/venta publicados (fin de semana, feriado, error
   puntual del portal) lo marca como `SIN_DATO_PUBLICADO` en vez de fallar.
6. Guarda todo en `output/tipo_cambio_sunat.csv` y escribe un log detallado
   de la ejecución en `logs/`.

El rango de fechas, el archivo de salida y la pausa entre peticiones son
parámetros de línea de comandos, no están hardcodeados.

## Estructura

```
WebScraping/
├── scraper_sunat.py     # script principal
├── requirements.txt
├── run_scraper.bat       # wrapper para Task Scheduler
├── output/               # CSV generado (tipo_cambio_sunat.csv)
├── logs/                 # logs con timestamp por ejecución
└── README.md
```

## Requisitos

- Python 3.10+ instalado desde [python.org](https://www.python.org/downloads/)
  (no la versión de Microsoft Store) y agregado al PATH.
- Google Chrome instalado (el driver se descarga solo con `webdriver-manager`,
  no hace falta bajar chromedriver a mano).

## Instalación

```powershell
cd WebScraping
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución manual

```powershell
.venv\Scripts\activate
python scraper_sunat.py
```

Parámetros opcionales:

| Parámetro       | Default                      | Descripción                                   |
|-----------------|-------------------------------|------------------------------------------------|
| `--desde`       | `2024-01`                     | Mes/año de inicio, formato `YYYY-MM`           |
| `--hasta`       | mes actual                    | Mes/año final, formato `YYYY-MM`               |
| `--salida`      | `output/tipo_cambio_sunat.csv`| Ruta del CSV de salida                         |
| `--espera`      | `1.5`                          | Segundos de espera entre cada mes consultado   |
| `--con-ventana` | (desactivado)                  | Muestra el navegador (por defecto es headless) |

Ejemplo para traer solo un rango puntual:

```powershell
python scraper_sunat.py --desde 2024-01 --hasta 2024-06 --salida output/2024_s1.csv
```

## Ejecución automática con Windows Task Scheduler

1. Instala el proyecto tal como se indica arriba (el entorno `.venv` debe
   quedar dentro de la carpeta `WebScraping`, junto a `run_scraper.bat`).
2. Abre **Programador de tareas** (`taskschd.msc`) → **Crear tarea básica**.
3. **General**: ponle un nombre (ej. `SUNAT_TipoCambio`) y marca
   "Ejecutar tanto si el usuario inició sesión como si no" si quieres que
   corra sin que tengas sesión abierta.
4. **Desencadenador**: elige la frecuencia deseada (ej. diario a una hora
   fija).
5. **Acción** → **Iniciar un programa**:
   - **Programa o script**: ruta completa a `run_scraper.bat`
     (ej. `C:\...\WebScraping\run_scraper.bat`).
   - **Iniciar en (opcional)**: ruta a la carpeta `WebScraping`
     (el `.bat` ya se autoubica con `%~dp0`, pero conviene dejarlo explícito).
6. Guarda la tarea y pruébala con clic derecho → **Ejecutar**.
7. Verifica que funcionó revisando:
   - Un log nuevo en `logs/scraper_<fecha>.log`.
   - El archivo `output/tipo_cambio_sunat.csv` actualizado.
   - En el Programador de tareas, columna **Último resultado de ejecución**
     debe mostrar `0x0` (éxito).

Equivalente por línea de comandos (mismo resultado que los pasos de arriba):

```powershell
schtasks /create /tn "SUNAT_TipoCambio" /tr "C:\...\WebScraping\run_scraper.bat" /sc DAILY /st 07:00
schtasks /run /tn "SUNAT_TipoCambio"          # dispara una corrida de prueba
schtasks /query /tn "SUNAT_TipoCambio" /v /fo LIST   # revisa "Ultimo resultado"
```

Esta tarea ya se creó y se probó en este equipo: quedó registrada como
`SUNAT_TipoCambio` (diaria, 07:00 a. m.), se disparó manualmente con
`schtasks /run`, y terminó con **Último resultado: 0** (éxito), generando
un log nuevo y actualizando el CSV sin intervención manual. La salida
completa de `schtasks /query` queda como evidencia en
[`task_scheduler_evidencia.txt`](task_scheduler_evidencia.txt).

### Nota sobre el modo headless

SUNAT bloquea las peticiones cuyo User-Agent contiene el string
`HeadlessChrome` (responde `ERR_EMPTY_RESPONSE`, como un WAF). Por eso
`crear_driver()` fuerza un User-Agent de escritorio normal cuando corre en
headless (el default). Si algún día vuelve a bloquear, se puede correr con
`--con-ventana` para depurar visualmente qué está pasando.

`run_scraper.bat` llama directamente al Python del entorno virtual
(`.venv\Scripts\python.exe`), así que Task Scheduler usa el intérprete
correcto sin depender del PATH del sistema, y todas las rutas del script son
relativas a su propia ubicación (`os.path.dirname(__file__)`), por lo que
funciona igual desde la terminal, doble clic o Task Scheduler.

## Notas sobre datos faltantes

Según la propia nota del portal SUNAT: *"En los días que no se cuente con
tipo de cambio publicado, se deberá tomar el del día inmediato anterior"*.
En la práctica el calendario ya replica el valor del último día hábil en
fines de semana y feriados, por lo que casi todos los días tendrán dato; los
pocos casos sin compra/venta visibles quedan marcados como
`SIN_DATO_PUBLICADO` en el CSV y registrados como warning en el log, en vez
de detener la ejecución.
