# Integrative Project: Automation, APIs, and Data Analysis

Tres retos independientes de automatización, web scraping y consumo de APIs, entregados en un solo repositorio como pide el enunciado. Cada carpeta tiene su propio `README.md` con instrucciones detalladas de instalación y ejecución.

| Carpeta | Reto | Estado |
|---|---|---|
| [`01-peoplesync-rpa/`](01-peoplesync-rpa/README.md) | RPA — registro automático de empleados en PeopleSync | ✅ Completo |
| [`02-sunat-webscraping/`](02-sunat-webscraping/README.md) | Web Scraping — SUNAT | 🚧 En desarrollo |
| [`03-lichess-api/`](03-lichess-api/README.md) | API — análisis de partidas y automatización de torneos en Lichess | ✅ Completo |

## Cómo ejecutar cada proyecto

```powershell
cd 01-peoplesync-rpa
# seguir el README de esa carpeta

cd ..\03-lichess-api
# seguir el README de esa carpeta
```

Cada subproyecto tiene su propio `requirements.txt`, `.env.example` y entorno virtual — son independientes entre sí, solo comparten repositorio.

## Video de presentación

Un solo video de hasta 9 minutos cubriendo los tres proyectos (problema, solución, decisiones técnicas, retos y demo). Ver guion de apoyo para la parte de Lichess en `03-lichess-api/guion_video.md`.
