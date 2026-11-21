# .github de Nodo Cero

El repo especial de la organización [nodo-cero-bo](https://github.com/nodo-cero-bo) en GitHub. **Nodo Cero – Hackathon n8n Bolivia** es la hackathon de la comunidad n8n en Bolivia, enfocada en mujeres, de la mano de Women Techmakers Santa Cruz (sábado 21 de noviembre de 2026, CEA, Santa Cruz de la Sierra).

| Archivo | Qué es |
|---|---|
| [`profile/README.md`](profile/README.md) | La portada que GitHub muestra en [github.com/nodo-cero-bo](https://github.com/nodo-cero-bo): banner, los repos, «Empezá acá», agenda, Avalanche Fuji y los logos de quienes hacen posible el evento. |
| `profile/banner.png` y `profile/assets/` | El banner (1600 × 500) y los logos oficiales en dos versiones, para el tema oscuro y el claro de GitHub. |
| [`KPIS.md`](KPIS.md) | Para quienes organizan: cómo medir los KPIs del evento después del sábado, con comandos de `gh` y el workflow `42-reporte-kpis`. No se muestra en el perfil. |
| [`tools/cabeceras.py`](tools/cabeceras.py) | Dibuja el banner, las imágenes de cabecera de cada repo (1280 × 640, también sirven como vista previa social) y los logos del perfil (con una copia en `guias/assets/aliados/`), y audita cada pieza: zona segura, textos cortados, contraste, peso de los logos frente a n8n y tamaño de archivo. |
| [`tools/readme_workflows.py`](tools/readme_workflows.py) | Arma la tabla del catálogo del README de `workflows` a partir de los `meta.json`. |

## Regenerar las imágenes

Hace falta Python 3 con Pillow y el Chrome sin interfaz que trae Remotion; el script usa las tipografías de `fuentes/` y los logos oficiales de `marcas/` de la carpeta del proyecto, que no se publican acá.

```bash
python -X utf8 org-perfil/tools/cabeceras.py              # todas las piezas
python -X utf8 org-perfil/tools/cabeceras.py banner logos # algunas
```

Cada cabecera se sube también como vista previa social de su repo, a mano: **Settings → General → Social preview → Edit → Upload an image**.

## Licencia

El código de este repo está bajo la licencia [MIT](LICENSE). n8n, Supabase, Clerk, Avalanche, Team1, Aspire Institute, Women Techmakers y el Gobierno Autónomo Departamental de Santa Cruz son marcas de sus dueños: sus logos se usan para nombrar a quienes hacen posible el evento y no entran en ninguna licencia.
