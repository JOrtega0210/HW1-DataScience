# Guion de video — Web Scraping SUNAT (≈3 minutos)

Este guion cubre únicamente el bloque de Web Scraping. Si lo unes con los
otros dos retos (RPA PeopleSync y API Lichess) en un solo video, este
segmento debe quedar dentro del límite total de 9 minutos.

---

## 0:00 – 0:20 | El problema

> "Este es el segundo reto: automatizar la consulta del tipo de cambio
> oficial que publica SUNAT. SUNAT muestra esta información día por día en
> un calendario web, pero no ofrece un archivo descargable con el
> histórico completo. El objetivo es tener, en un solo CSV, el tipo de
> cambio de compra y venta de cada día desde enero de 2024 hasta hoy, sin
> tener que entrar manualmente mes por mes."

*(Pantalla: portal de SUNAT abierto, mostrando el calendario mensual.)*

## 0:20 – 1:00 | Cómo funciona la solución

> "La solución es un script en Python con Selenium. Abre el portal en
> Chrome, ubica el mes y año que muestra el calendario por defecto —que es
> el mes actual— y usa el botón de retroceso para llegar hasta enero de
> 2024. Desde ahí avanza mes a mes con el botón de avanzar, y en cada mes
> lee las celdas del calendario para sacar el día, el tipo de cambio de
> compra y el de venta. Todo esto se acumula y al final se guarda como un
> único archivo CSV ordenado por fecha."

*(Pantalla: fragmento del código — función `extraer_mes` y el loop
principal en `scraper_sunat.py`.)*

## 1:00 – 1:40 | Decisiones técnicas

> "Algunas decisiones clave: primero, todo el rango de fechas es
> configurable por línea de comandos —`--desde` y `--hasta`— no hay fechas
> quemadas en el código. Segundo, cada vez que el script cambia de mes,
> usa `WebDriverWait` para esperar a que la etiqueta de mes y año cambie y
> a que los datos del nuevo mes ya estén cargados, en lugar de usar
> `sleep` fijos que podrían fallar si la red va lenta. Tercero, entre cada
> mes se agrega una pausa configurable para no bombardear el portal con
> peticiones. Y cuarto, el driver de Chrome se descarga automáticamente
> con `webdriver-manager`, así que no hay rutas de chromedriver hardcodeadas
> y el script corre igual en cualquier máquina."

*(Pantalla: parámetros del `argparse` y la función `navegar` con el
`WebDriverWait`.)*

## 1:40 – 2:10 | Retos y cómo se resolvieron

> "Tuve tres retos concretos. Primero, este calendario no tiene un selector
> de mes y año como un formulario tradicional: solo se navega con las
> flechas de anterior y siguiente, así que tuve que inspeccionar el HTML
> para identificar que el mes y el año se muestran en botones
> deshabilitados, y usarlos como referencia confiable de en qué mes está
> parado el calendario. Segundo, al pasar de mes el calendario se
> re-renderiza completo, y a veces el script intentaba leer esos botones
> justo cuando ya habían sido reemplazados, lo que producía un error de
>'elemento obsoleto'; lo resolví agregando reintentos cortos en esa
> lectura. Y el tercero fue el más raro: cuando corría Chrome en modo
> headless, SUNAT directamente rechazaba la conexión. Investigando el
> tráfico de red encontré que el propio user-agent de headless incluye el
> texto 'HeadlessChrome', y el portal lo bloquea. La solución fue forzar un
> user-agent de navegador de escritorio normal al lanzar Chrome en modo
> headless, y con eso la página cargó exactamente igual que en una ventana
> visible."

*(Pantalla: DevTools mostrando la clase `_2026_6_1` en una celda del
calendario, y opcionalmente la comparación headless bloqueado vs.
headless con user-agent forzado.)*

## 2:10 – 2:50 | Demostración

> "Aquí lo ejecuto: primero de forma manual desde la terminal para un
> rango corto, para que se vea rápido…"

*(Pantalla: `python scraper_sunat.py --desde 2024-01 --hasta 2024-03`
corriendo, mostrando el log en consola.)*

> "…y aquí el resultado: el CSV con fecha, compra, venta y estado por
> cada día, con las 974 filas que van de enero de 2024 a hoy, y el log de
> la ejecución con el detalle de cada mes procesado. Y esto mismo también
> corre solo, sin que yo lo dispare, porque está configurado como la tarea
> 'SUNAT_TipoCambio' en Windows Task Scheduler."

*(Pantalla: `output/tipo_cambio_sunat.csv` abierto, luego el Programador
de tareas de Windows mostrando la tarea `SUNAT_TipoCambio`, clic derecho →
Ejecutar, y el "Último resultado de ejecución" en `0x0`.)*

## 2:50 – 3:00 | Cierre

> "Con esto queda automatizada la consulta del tipo de cambio oficial de
> SUNAT, con un histórico consolidado y actualizable en cualquier momento
> sin intervención manual."

---

### Checklist antes de grabar
- [ ] Correr el script una vez completo (`2024-01` → mes actual) para tener
      un CSV y un log reales que mostrar.
- [ ] Tener la tarea ya creada en Task Scheduler antes de grabar, para solo
      mostrar la ejecución y el resultado.
- [ ] Tener a la mano DevTools abierto en la celda del calendario para el
      minuto de "retos".
