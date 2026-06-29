# gdrive-migrate-toolkit (español)

**Reorganiza, deduplica, evacúa y fusiona cuentas de Google Drive / Google
Workspace a escala con [rclone](https://rclone.org/) — sin perder datos y de forma
reversible.**

> 🇬🇧 The full documentation is in English: [`README.md`](README.md) y la carpeta
> [`docs/`](docs/). Este archivo es el resumen rápido en español.

No existe una herramienta oficial para **reordenar / fusionar / evacuar /
deduplicar un Google Drive de empresa a escala**: varias cuentas, archivos
virtuales de Drive para Escritorio que cuelgan `find`, archivos Google-native que
no son bytes reales, throttling de la API y límites de ruta en Windows. Este
toolkit es el método + los scripts que lo resuelven, destilados de hacerlo de
verdad sobre un Workspace multi-cuenta de decenas de GB.

Contrato de seguridad único: **copiar → verificar → borrar a papelera**, nunca un
"mover" fuera de la nube. Todos los scripts van en **dry-run por defecto**.

## Qué hace

| Capacidad | Script | Doc (EN) |
|---|---|---|
| Inventariar sin colgar Drive | `detect_natives.py` | [docs/02](docs/02-inventory.md) |
| Espejo local (red de seguridad; exporta nativos) | `mirror_account.py` | [docs/03](docs/03-local-mirror.md) |
| Reorganizar **in situ** (move server-side, preserva nativos) | `reorg_move.py` | [docs/04](docs/04-reorg-intra-account.md) |
| **Evacuar** una cuenta a otras + disco (2 pasadas) | `evacuate.py` | [docs/05](docs/05-evacuation-cross-account.md) |
| Deduplicar y poner en cuarentena | — (recetas) | [docs/06](docs/06-dedup-and-quarantine.md) |
| Verificar (recuento/hash) y borrar reversible | `verify_counts.py` | [docs/07](docs/07-verify-and-delete.md) |
| Subir de disco a Drive (y volver) | — (recetas) | [docs/08](docs/08-disk-to-drive.md) |
| Planificar espacio y reparto | — (recetas) | [docs/10](docs/10-space-and-distribution.md) |

El método completo está en [**PLAYBOOK.md**](PLAYBOOK.md). Todas las trampas en
[**docs/GOTCHAS.md**](docs/GOTCHAS.md).

## Inicio rápido

```bash
# 0. Instala rclone y crea un remote por cuenta (¡nombres de 2+ letras!)
rclone config create cuentaA drive scope=drive
rclone about cuentaA:          # sanity: cuota cloud pequeña = OK

# 1. Espejo a disco (tu red de seguridad real) — dry-run y luego --apply
python scripts/mirror_account.py --remote cuentaA: --dest D:/MIRROR
python scripts/mirror_account.py --remote cuentaA: --dest D:/MIRROR --apply

# 2. Reorganizar in situ con una tabla CSV de moves (dry-run por defecto)
cp templates/move_table.example.csv move_table.csv   # edítala: group;source;dest
python scripts/reorg_move.py --table move_table.csv --src-remote cuentaA: --dst-remote cuentaA: --apply

# 3. O evacuar una cuenta a otras + disco (2 pasadas)
python scripts/evacuate.py --table move_table.csv --apply
python scripts/evacuate.py --table move_table.csv --pass 2 --apply

# 4. Verificar y borrar el origen a papelera (reversible 30 días)
python scripts/verify_counts.py --table move_table.csv --src-remote cuentaA: --dst-remote cuentaB:
rclone purge "cuentaA:Bloque" --drive-use-trash=true
```

Requisitos: **Python 3.8+** (solo librería estándar) y **rclone**. Sin `pip install`.

## Avisos críticos

- **Copiar, nunca mover *desde* Drive.** Un "mover" fuera de una carpeta sincronizada
  borra la copia en la nube.
- **Los Google-native solo sobreviven como nativos dentro de Drive.** Al bajar a
  disco se exportan a Office.
- **La papelera de 30 días es una red, no un backup.** El backup es tu espejo local
  verificado.
- **Un solo rclone por cuenta** — dos a la vez = HTTP 429.
- **No muevas proyectos de edición vivos** (`.prproj`/`.drp` enlazan media por ruta).

## Privacidad y licencia

Este repo solo contiene **método + scripts genéricos + plantillas vacías**. Cero
credenciales, cero datos reales, cero nombres de cuentas/marcas/clientes. Nunca
subas tu `rclone.conf`, logs ni CSV de cambios — ver [SECURITY.md](SECURITY.md) y
[.gitignore](.gitignore). Licencia [MIT](LICENSE).
