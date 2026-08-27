# Lichess API — Data Analysis and Automation

Proyecto que consume la API de [Lichess](https://lichess.org/api) para (A) analizar el historial de partidas de un jugador y (B) automatizar la creación semanal de torneos, con manejo de rate limits, modo simulación y logging de ejecución.

## Estructura

```
src/
  api_client.py           # cliente HTTP reutilizable (auth, reintentos, rate limit)
  utils.py                # logging, helpers de fechas/resultados
  game_analysis.py        # Parte A — análisis de partidas
  tournament_automation.py# Parte B — automatización de torneos
config/tournaments.yaml   # calendario semanal de torneos
fixtures/                 # datos sintéticos para --demo (ver más abajo)
tests/                    # pruebas unitarias (pytest)
scheduler/register_task.ps1 # registro en Windows Task Scheduler
output/data, output/plots # CSVs y gráficos generados
logs/                     # logs de ejecución
```

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env`:

```
LICHESS_USERNAME=tu_usuario_lichess
LICHESS_TOKEN=              # opcional para Parte A, obligatorio para crear torneos reales en Parte B
MAX_GAMES=100
```

El token se obtiene en `lichess.org/account/oauth/token` con scope `tournament:write`. **Nunca se commitea** (`.env` está en `.gitignore`; solo `.env.example` va al repo).

## Parte A — Análisis de partidas

```powershell
python -m src.game_analysis --username <usuario> --max-games 100
```

Hace streaming de partidas vía `GET /api/games/user/{username}`, arma un `DataFrame` de Pandas, calcula estadísticas (resultados, rating, color, modo de juego, desempeño vs favorito/underdog) y exporta:

- `output/data/games_<usuario>.csv` — partidas normalizadas
- `output/data/stats_summary_<usuario>.csv` — métricas agregadas
- `output/plots/*.png` — dashboard combinado + gráficos individuales

**Modo demo** (sin llamadas a la API, usa `fixtures/sample_games.ndjson` con datos sintéticos): `python -m src.game_analysis --demo`. Útil para verificar el pipeline sin gastar cuota de la API.

## Parte B — Automatización de torneos

```powershell
python -m src.tournament_automation            # dry-run (no crea nada, por defecto)
python -m src.tournament_automation --execute   # crea los torneos reales vía API (requiere LICHESS_TOKEN)
```

Lee `config/tournaments.yaml` (calendario semanal reutilizable), calcula la fecha/hora de cada torneo para la semana en curso, **omite** los que ya pasaron, y crea el resto vía `POST /api/tournament`. Un torneo que falla no detiene los demás. Cada corrida genera `output/data/tournament_run_<timestamp>.csv` con el detalle (creado/omitido/fallido) y queda registrada en `logs/tournament_automation.log`.

## Ejecución automática (Windows Task Scheduler)

```powershell
cd scheduler
.\register_task.ps1
```

Registra la tarea `LichessTournamentAutomation` para correr cada lunes 00:05 (`python -m src.tournament_automation --execute`). Verificar con `Get-ScheduledTask -TaskName "LichessTournamentAutomation"`.

## Tests

```powershell
pytest -v
```

## Decisiones técnicas

- **Reintentos con backoff**: 429 respeta `Retry-After`; 5xx usa backoff exponencial. Máx. 5 intentos.
- **User-Agent explícito**: la API de Lichess responde distinto (o bloquea) al User-Agent por defecto de `requests`; se fija uno propio.
- **`dry-run` por defecto** en Parte B: crear torneos reales requiere `--execute` explícito, para evitar llamadas accidentales a la API.
- **Errores no fatales por torneo**: cada entrada del calendario se procesa en su propio `try/except`, así un fallo no aborta el resto.
- **Logging centralizado**: `setup_logging` configura el root logger, así los reintentos internos de `api_client` quedan en el mismo archivo que el flujo principal.

## Nota sobre rate limiting

`GET /api/games/user/{username}` es un endpoint anónimo limitado a **1 request concurrente**; en redes compartidas (ej. IPs de sandboxes/CI) puede devolver `429` de forma persistente aunque el código esté correcto. `logs/game_analysis.log` incluye una corrida real contra la API que demuestra los reintentos/backoff funcionando, y `--demo` permite verificar el resto del pipeline de forma determinística. En una red doméstica normal (o con `LICHESS_TOKEN`) el modo en vivo funciona sin este problema.

## Puntos de innovación (extra)

- Modo `--demo` con datos sintéticos para pruebas/CI sin consumir cuota de API.
- Dashboard combinado (2x2) además de los gráficos individuales pedidos.
- Estadística adicional: win rate como favorito vs. underdog según diferencia de rating.
- Suite de tests unitarios (`pytest`) para la lógica pura (resultado de partida, cálculo de próxima fecha de torneo).
- Workflow de GitHub Actions (`.github/workflows/ci.yml`) que corre los tests en cada push.
- Script de registro automático en Windows Task Scheduler (`scheduler/register_task.ps1`).
