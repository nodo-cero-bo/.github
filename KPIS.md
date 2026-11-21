# KPIs de Nodo Cero: cómo medirlos después del evento

Esta guía es para quienes organizan. No se muestra en el perfil de la organización: vive en el repo `.github`.
Sirve para armar el informe para n8n, Team1, Supabase, Clerk, Aspire Institute y Women Techmakers Santa Cruz con números que cualquiera puede volver a sacar.

> **Lo urgente primero.** GitHub guarda el tráfico de cada repo (visitas y clones) nada más de los últimos 14 días: el sábado del evento deja de aparecer alrededor del **4 de diciembre de 2026**. Guardá una foto del tráfico en la semana del evento y repetila cada semana (sección 1). Lo demás (issues, etiquetas, hashes de Fuji) queda guardado y se puede contar cuando quieras.

## Qué necesitás

- [GitHub CLI](https://cli.github.com) con una sesión de alguien con permiso de escritura en los repos: `gh auth login`. La API de tráfico responde nada más a quien puede escribir en el repo.
- Una terminal con bash (en Windows, Git Bash).
- Para el workflow `42-reporte-kpis`: n8n (n8n Cloud o local) y una credencial de GitHub con un token que tenga acceso a los repos de la organización.

Todos los comandos usan la organización `nodo-cero-bo`. Si cambió de nombre, cambiala en `ORG`.

```bash
ORG=nodo-cero-bo
REPOS="workflows guias proyectos nodo-cero-bo.github.io .github"
```

## Resumen: cada KPI, dónde se mira y con qué

| KPI | Para quién | Dónde se mira | Cómo |
|---|---|---|---|
| Proyectos presentados | todos | issues con la etiqueta `proyecto` en `proyectos` | sección 2 |
| Proyectos por tecnología (n8n, IA, Supabase, Clerk, Avalanche Fuji) | Supabase, Clerk, Team1 | etiquetas `n8n`, `ia`, `supabase`, `clerk`, `avalanche-fuji` | sección 2 |
| Equipos que presentan un proyecto con Fuji | Team1 | etiqueta `avalanche-fuji` y hashes verificados en la red | secciones 2 y 4 |
| Equipos que importaron workflows de Avalanche | Team1 | respuesta «¿Partieron de algún workflow del repo?» y rutas más vistas del repo `workflows` | secciones 1 y 3 |
| Instalaciones de Core Wallet | Team1 | etiqueta `core-wallet` (lo que declaran los equipos) y analítica de Core con UTM | secciones 2 y 5 |
| Inscripciones a Avalanche Academy | Team1 | etiqueta `avalanche-academy` y analítica de Academy con UTM | secciones 2 y 5 |
| Miembros nuevos en Team1 LATAM | Team1 | etiqueta `team1-latam` y analítica de team1.network con UTM | secciones 2 y 5 |
| Visitas y clones de los repos | todos | API de tráfico de GitHub | sección 1 |
| Estrellas y forks | todos | API de repos de GitHub | sección 1 |
| Todo junto, listo para mandar | todos | workflow `42-reporte-kpis` | sección 6 |

## 1. Tráfico de los repos (en la semana del evento)

Visitas y clones de los últimos 14 días, por día, y las 10 rutas y referencias más vistas.

```bash
ORG=nodo-cero-bo
DIA=$(date +%F)
mkdir -p "kpis/$DIA"
for r in workflows guias proyectos nodo-cero-bo.github.io .github; do
  for k in views clones popular/paths popular/referrers; do
    gh api "repos/$ORG/$r/traffic/$k" > "kpis/$DIA/${r}__${k//\//-}.json"
  done
done
ls "kpis/$DIA"
```

Totales de visitas y clones (`count` es el total y `uniques`, personas o equipos distintos):

```bash
for r in workflows guias proyectos nodo-cero-bo.github.io; do
  v=$(gh api "repos/$ORG/$r/traffic/views"  --jq '"\(.count) visitas, \(.uniques) únicas"')
  c=$(gh api "repos/$ORG/$r/traffic/clones" --jq '"\(.count) clones, \(.uniques) únicos"')
  echo "$r: $v · $c"
done
```

Qué carpetas de Avalanche se vieron más (sirve como señal de equipos que abrieron esos workflows):

```bash
gh api "repos/$ORG/workflows/traffic/popular/paths" --jq '.[] | select(.path | test("avalanche|fuji")) | "\(.count) visitas, \(.uniques) únicas  \(.path)"'
```

Estrellas, forks y personas que siguen cada repo:

```bash
for r in workflows guias proyectos; do
  gh api "repos/$ORG/$r" --jq '"\(.name): \(.stargazers_count) estrellas, \(.forks_count) forks, \(.subscribers_count) siguiendo"'
done
```

Lo que este tráfico **no** cuenta, para decirlo de frente en el informe:

- Las importaciones con «Import from URL» o con el botón «Copiar workflow» de la página: bajan el archivo crudo y GitHub no las registra como visita ni como clon.
- Las visitas a la página (`nodo-cero-bo.github.io`): GitHub Pages no tiene estadísticas. El tráfico del repo de la página cuenta a quien mira el código, no a quien visita el sitio.

## 2. Proyectos registrados y por tecnología

Cada equipo registra su proyecto con el formulario de `proyectos`. La automatización Vitrina le pone una etiqueta por cada casilla marcada.
Se cuentan los issues **abiertos**: cerrar un issue es la forma de sacar de la vitrina algo que no era un proyecto.

```bash
ORG=nodo-cero-bo
total=$(gh api -X GET search/issues -f q="repo:$ORG/proyectos is:issue is:open label:proyecto" --jq .total_count)
echo "Proyectos registrados: $total"
for t in n8n ia supabase clerk avalanche-fuji core-wallet avalanche-academy team1-latam; do
  n=$(gh api -X GET search/issues -f q="repo:$ORG/proyectos is:issue is:open label:proyecto label:$t" --jq .total_count)
  printf '%-18s %s\n' "$t" "$n"
done
```

Lo mismo se ve en la web: en `github.com/nodo-cero-bo/proyectos/issues`, filtrá por etiqueta (por ejemplo `label:proyecto label:avalanche-fuji`).

La lista completa, para una planilla (CSV con número, nombre y etiquetas, sin datos personales):

```bash
gh issue list --repo "$ORG/proyectos" --label proyecto --state open --limit 500 \
  --json number,title,labels,url \
  --jq '.[] | [.number, .title, ([.labels[].name] | join(" ")), .url] | @csv' > kpis/proyectos.csv
```

## 3. Equipos que partieron de los workflows del repo

El formulario pregunta «¿Partieron de algún workflow del repo?» con las categorías. Para contar cuántos equipos eligieron **Avalanche Fuji**:

```bash
gh issue list --repo "$ORG/proyectos" --label proyecto --state open --limit 500 --json body \
  --jq 'map(.body | split("### ¿Partieron de algún workflow del repo?")[1] // "" | split("###")[0] | select(test("Avalanche Fuji"))) | length'
```

Cambiá `Avalanche Fuji` por `Supabase`, `Clerk`, `IA`, `Fundamentos` o `Proyectos completos` para las demás categorías.

## 4. Hashes de Fuji: verificar que existen y salieron bien

Los equipos que usaron Fuji pueden informar el hash de una transacción. Esto los junta y le pregunta a la red pública de Fuji si la transacción existe y salió bien (`status` `0x1`):

```bash
RPC=https://api.avax-test.network/ext/bc/C/rpc
gh issue list --repo "$ORG/proyectos" --label proyecto --state open --limit 500 --json number,body \
  --jq '.[] | .number as $n | (.body | split("### Hash de una transacción en Fuji (opcional)")[1] // "" | split("###")[0] | [scan("0x[0-9a-fA-F]{64}")][0]) as $h | select($h) | "\($n) \($h)"' |
while read -r n h; do
  estado=$(curl -s --ssl-no-revoke -X POST -H 'content-type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$h\"]}" "$RPC" |
    node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).result;console.log(!r?"no existe":r.status==="0x1"?"ok, bloque "+parseInt(r.blockNumber,16):"falló")})')
  echo "#$n $h $estado"
done
```

(`--ssl-no-revoke` hace falta en algunas computadoras con Windows; en Linux y macOS se puede sacar.) Cada transacción también se puede abrir en el explorador: `https://build.avax.network/explorer/fuji/c-chain/tx/<hash>`.

## 5. Lo que mide Team1 con UTM

Todos los enlaces a Core Wallet, Avalanche Academy y Team1 que publicamos (README, guías, formulario y página) llevan estos parámetros:

```text
utm_source=nodo-cero
utm_campaign=hackathon-n8n-bolivia-2026
utm_medium=github   (en los README, guías y el formulario)
utm_medium=sitio    (en la página nodo-cero-bo.github.io)
```

Las visitas, descargas e inscripciones que llegaron por esos enlaces las ve **Team1 en su analítica**, no nosotros. Para el informe, pediles los números filtrando por `utm_source=nodo-cero` y `utm_campaign=hackathon-n8n-bolivia-2026`, y sumalos a lo que declararon los equipos (sección 2: `core-wallet`, `avalanche-academy` y `team1-latam`).

Para revisar que un enlace con UTM sigue respondiendo:

```bash
curl -s --ssl-no-revoke -L -o /dev/null -w '%{http_code} %{url_effective}\n' \
  "https://core.app/?utm_source=nodo-cero&utm_medium=github&utm_campaign=hackathon-n8n-bolivia-2026"
```

## 6. El informe completo con el workflow 42-reporte-kpis

El repo `workflows` trae `40-proyectos/42-reporte-kpis`, un workflow de n8n que junta todo lo de arriba y devuelve un resumen listo para mandar a Team1, Supabase, Clerk y Aspire Institute: cuenta los issues `proyecto` por tecnología, trae las visitas y clones de los repos con la API de tráfico y verifica en Fuji los hashes informados.

1. Importalo en n8n con «Import from URL»:
   `https://raw.githubusercontent.com/nodo-cero-bo/workflows/main/40-proyectos/42-reporte-kpis/workflow.json`
2. Creá la credencial de GitHub que pide (tipo de credencial de n8n `githubApi`) con un token de alguien con permiso de escritura en los repos de `nodo-cero-bo` (la API de tráfico lo exige).
3. Ejecutalo y copiá el resumen. Las instrucciones completas están en el README de esa carpeta.

Correlo en la semana del evento para que el tráfico salga completo, y guardá la salida junto a las fotos de la sección 1.

## Otras fuentes

- **Luma** (`luma.com/n8n-rfgv`): inscripciones, aprobadas y check-ins del día, en el panel del evento. En el informe van números, nunca la lista de personas.
- **Presentaciones del día**: cuántos equipos presentaron a las 15:00, de la planilla de la organización.

## Cuidado con los datos

- El informe lleva números y nombres de proyectos o equipos, nunca correos, teléfonos ni datos de contacto.
- Los archivos de `kpis/` que genera esta guía pueden tener títulos de issues: no los subas a un repo público sin revisarlos.
