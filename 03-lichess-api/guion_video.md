# Guion — Lichess API: Data Analysis and Automation (≈3 min)

## 0:00–0:25 — Problema y contexto
"Este proyecto usa la API de Lichess para resolver dos problemas: primero, analizar automáticamente el historial de partidas de un jugador para sacar estadísticas de resultados, rating, color y modo de juego; y segundo, automatizar la creación semanal de torneos, para no tener que crearlos manualmente cada semana desde la web."

## 0:25–1:10 — Parte A: Análisis de partidas (cómo funciona)
"La primera parte se conecta al endpoint `/api/games/user` de Lichess, que hace streaming de partidas en formato ndjson. Cada partida se transforma en una fila de un DataFrame de Pandas: color con el que jugué, resultado desde mi perspectiva, rating, modo de juego y apertura. Con eso calculo estadísticas — porcentaje de victorias, evolución de rating, rendimiento por color y por modo — y las exporto a CSV, además de generar un dashboard con Matplotlib."
*(mostrar en pantalla: `python -m src.game_analysis --username <usuario>`, luego el CSV y el dashboard PNG)*

## 1:10–1:35 — Decisión técnica destacada
"Una decisión técnica importante: la API de Lichess responde distinto — o directamente bloquea — el User-Agent por defecto de la librería requests, así que configuré uno propio. También implementé reintentos con backoff exponencial respetando el header Retry-After para los códigos 429, porque el endpoint de exportación de partidas tiene un límite de una request concurrente."

## 1:35–2:00 — Reto encontrado y cómo se resolvió
"Durante las pruebas me topé con rate limiting real de la API por estar en una red compartida. En vez de simularlo, dejé esa corrida real en los logs como evidencia de que el manejo de errores funciona — reintenta, respeta el backoff, y si se agotan los intentos falla de forma controlada sin romper el programa. Además agregué un modo `--demo` con datos sintéticos para poder verificar todo el pipeline de análisis sin depender de la disponibilidad de la API."
*(mostrar en pantalla: fragmento de `logs/game_analysis.log` con los reintentos 429)*

## 2:00–2:40 — Parte B: Automatización de torneos
"La segunda parte lee un calendario semanal de torneos desde un YAML — nombre, día, hora, modalidad y duración — calcula la fecha exacta para la semana actual, y omite automáticamente los torneos cuyo horario ya pasó. Por defecto corre en modo `dry-run`: simula la creación y muestra qué se enviaría a la API sin ejecutar nada. Con la flag `--execute` y un token de autenticación, crea los torneos reales vía POST a `/api/tournament`. Si un torneo falla — por ejemplo por un token inválido — el error se registra pero el resto del calendario se sigue procesando."
*(mostrar en pantalla: ejecución `--dry-run` y luego `--execute`, mostrando el log con el error controlado y el CSV de resultados)*

## 2:40–3:00 — Cierre
"Todo el proyecto queda organizado en un repositorio con funciones reutilizables entre ambas partes, tests unitarios, logging centralizado, y un workflow de GitHub Actions que corre los tests en cada push. Con esto, el análisis y la automatización de torneos en Lichess quedan completamente gobernados por código, sin intervención manual."

---

### Notas para grabar
- Ten el terminal y el archivo `dashboard_DemoPlayer.png` (o el tuyo real) listos para mostrar antes de grabar.
- Si tu red no está compartida/limitada, puedes reemplazar la demo de rate-limit por una corrida en vivo exitosa — el guion funciona igual, solo ajusta esa frase a "aquí se ve la corrida en vivo trayendo mis partidas reales".
- Tiempo total apuntado: ~3:00. Recorta la sección 1:10–1:35 si vas corto de tiempo.
