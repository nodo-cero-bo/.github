# -*- coding: utf-8 -*-
"""Arma el catálogo del README del repo de workflows a partir de los meta.json.

Qué hace: recorre la lista fija de workflows de la especificación (los ids no cambian: la página y las guías los nombran así),
lee el meta.json de cada carpeta (título, resumen, líneas, nivel, minutos, credenciales y si fue «ejecutado» o «auditado») y
reescribe la tabla por categoría entre las marcas <!-- catalogo:inicio --> y <!-- catalogo:fin --> de workflows/README.md.
Lo demás del README no se toca.

Si una carpeta todavía no tiene meta.json, la fila sale con los datos de la especificación, sin líneas y sin insignia,
y el script lo avisa al final (sale con código 1 si falta alguno, así se nota antes de publicar).
Los workflows que la especificación marca como opcionales (54-bigquery-respuestas) entran nada más si su carpeta existe.

Uso (desde cualquier carpeta):  python -X utf8 org-perfil/tools/readme_workflows.py
"""
import json
import re
import sys
from pathlib import Path

GH = Path(__file__).resolve().parent.parent.parent      # github_nodo_cero/
WF = GH / 'workflows'
README = WF / 'README.md'
CONFIG = json.loads((GH / 'config.json').read_text(encoding='utf-8'))
ORG, RAMA = CONFIG['org'], CONFIG.get('rama', 'main')
INICIO, FIN = '<!-- catalogo:inicio -->', '<!-- catalogo:fin -->'

U = CONFIG['utm']
UTM = f'utm_source={U["utm_source"]}&utm_medium={U["utm_medium_github"]}&utm_campaign={U["utm_campaign"]}'

GUIAS = f'https://github.com/{ORG}/{CONFIG["repos"]["guias"]}/blob/{RAMA}'

INSIGNIA = {
    'ejecutado': '![ejecutado](https://img.shields.io/badge/ejecutado-FF91AC?style=flat-square)',
    'auditado': '![auditado](https://img.shields.io/badge/auditado-5A0026?style=flat-square)',
}

# Las 4 líneas de la hackathon (campo "lineas" de meta.json): id -> (nombre corto para la tabla, nombre completo).
# La guía de cada una está en guias/lineas/<id>.md.
LINEAS = {
    'ia': ('IA', 'IA para tu comunidad'),
    'web3': ('Web3', 'Web3 con Avalanche Fuji'),
    'apps': ('Apps', 'Apps con login y datos'),
    'impacto': ('Impacto', 'Impacto social y ambiental'),
}

# Categorías en el orden del repo. La bajada se muestra arriba de cada tabla.
CATEGORIAS = [
    ('00-fundamentos', 'Fundamentos',
     'Para arrancar de cero: datos, expresiones, tu primera API, HTTP Request, formularios y tu primer agente de IA. '
     'Ninguno pide credenciales, salvo el agente (una clave gratis de Google AI Studio).'),
    ('10-avalanche-fuji', 'Avalanche Fuji',
     'Leé la red de prueba de Avalanche con su RPC público: sin cuentas y sin claves privadas. '
     'Son la base de la línea Web3 con Avalanche Fuji, con Team1, y de la mención especial «Mejor uso de Avalanche Fuji».'),
    ('20-clerk', 'Clerk',
     'Login y usuarias con Clerk conectado a n8n: webhooks firmados, una API que exige sesión e invitaciones. '
     'Son la base de la línea Apps con login y datos, junto con Supabase.'),
    ('30-supabase', 'Supabase',
     'Postgres, tu propia API y búsqueda en tus documentos con pgvector. El esquema de las tablas está en [`supabase/sql/`](supabase/sql).'),
    ('40-proyectos', 'Proyectos completos',
     'Juntan varias piezas de punta a punta, para partir de algo grande y hacerlo tuyo.'),
    ('50-google-cloud', 'Google Cloud',
     'Gemini en Vertex AI, sentimiento con Cloud Natural Language, traducción con Cloud Translation, archivos en Cloud Storage '
     'y respuestas en BigQuery. Usan los créditos de Google Cloud si tu equipo los recibió, o el nivel gratuito. '
     'Desde el 16 de noviembre de 2026, el crédito de bienvenida de la prueba gratis no paga Vertex AI ni la API de Gemini: '
     f'para IA gratis, usá Gemini con la [clave de Google AI Studio]({GUIAS}/00-empezar/07-clave-gemini.md), como en el workflow 05. '
     f'Antes de empezar, seguí la [guía de Google Cloud y créditos]({GUIAS}/00-empezar/08-google-cloud.md): '
     'crear el proyecto, la cuenta de servicio y las alertas de presupuesto, y cómo apagar todo al terminar. '
     'Sirven para la mención especial «Mejor uso de Google Cloud».'),
    ('60-casos-de-uso', 'Casos de uso',
     'Automatizaciones de todos los días para problemas reales: el clima de Santa Cruz, el tipo de cambio, noticias, '
     'páginas web, listas, mensajes, un bot de Telegram y reportes ambientales.'),
]

# La lista fija de la especificación (ESPEC.md). Los datos de acá se usan nada más mientras falte el meta.json.
LISTA = [
    ('00-fundamentos', '01-hola-n8n', 'Hola n8n: datos, expresiones y decisiones', 'Tu primer workflow: armá datos, usá expresiones y tomá una decisión con IF.', 'inicial', 10, []),
    ('00-fundamentos', '02-mi-primera-api', 'Tu primera API', 'Un Webhook que responde JSON: tu propia API en dos nodos.', 'inicial', 10, []),
    ('00-fundamentos', '03-http-request', 'Llamar a cualquier API con HTTP Request', 'Consultá una API pública y el RPC de Fuji, y leé la respuesta.', 'inicial', 15, []),
    ('00-fundamentos', '04-formulario', 'Un formulario de n8n', 'Un formulario que procesa la respuesta y muestra una página final.', 'inicial', 10, []),
    ('00-fundamentos', '05-agente-ia', 'Tu primer agente de IA', 'Chat Trigger, AI Agent, Google Gemini y memoria: un agente que conversa.', 'inicial', 15, ['Google Gemini']),
    ('10-avalanche-fuji', '10-fuji-estado-de-la-red', 'Estado de la red Fuji', 'chainId, último bloque y precio del gas de Fuji, en números legibles.', 'inicial', 10, []),
    ('10-avalanche-fuji', '11-fuji-saldo-wallet', 'Saldo de una wallet en Fuji', 'Pasale una dirección y te devuelve su saldo en AVAX.', 'inicial', 15, []),
    ('10-avalanche-fuji', '12-fuji-leer-transaccion', 'Leer una transacción en Fuji', 'Dado un hash: quién envió, a quién, cuánto, gas, estado y enlace al explorador.', 'inicial', 15, []),
    ('10-avalanche-fuji', '13-fuji-verificar-pago', 'Verificar un pago en Fuji', 'Valida destino, monto y confirmaciones de un pago, y responde si está verificado.', 'intermedio', 20, []),
    ('10-avalanche-fuji', '14-fuji-monitor-wallet', 'Monitor de una wallet en Fuji', 'Revisa un saldo cada cierto tiempo y avisa cuando cambia.', 'intermedio', 15, []),
    ('10-avalanche-fuji', '15-fuji-token-erc20', 'Saldo de un token ERC-20 en Fuji', 'Saldo, símbolo y decimales de un token con eth_call.', 'intermedio', 20, []),
    ('10-avalanche-fuji', '16-fuji-eventos-contrato', 'Leer eventos de un contrato en Fuji', 'Trae eventos con eth_getLogs y los decodifica.', 'avanzado', 25, []),
    ('20-clerk', '20-clerk-webhook-a-supabase', 'De Clerk a Supabase con un webhook', 'Cada alta, cambio o baja de usuaria en Clerk se sincroniza en Supabase.', 'intermedio', 20, ['Supabase API']),
    ('20-clerk', '21-clerk-api-protegida', 'Una API protegida con Clerk', 'Verifica la sesión de Clerk y devuelve el perfil; si no hay sesión, 401.', 'avanzado', 25, ['Supabase API']),
    ('20-clerk', '22-clerk-invitaciones', 'Invitaciones con Clerk', 'Invitá participantes por correo con la Backend API de Clerk.', 'intermedio', 15, ['Clerk Backend API']),
    ('30-supabase', '30-formulario-a-supabase', 'Formulario a Supabase', 'Lo que llega por un formulario queda guardado como fila en Supabase.', 'inicial', 15, ['Supabase API']),
    ('30-supabase', '31-api-crud-supabase', 'Una API sobre Supabase', 'Listá y creá filas de Supabase desde tu propia API.', 'intermedio', 20, ['Supabase API']),
    ('30-supabase', '32-cargar-documentos-rag', 'Cargar documentos para RAG', 'Subí un archivo, partilo en trozos y guardá sus embeddings en Supabase.', 'intermedio', 25, ['Supabase API', 'Google Gemini']),
    ('30-supabase', '33-agente-con-memoria-y-rag', 'Agente con memoria y tus documentos', 'Un agente que recuerda la conversación y busca en tus documentos.', 'avanzado', 30, ['Supabase API', 'Postgres', 'Google Gemini']),
    ('30-supabase', '34-supabase-webhook-ia', 'La IA clasifica cada fila nueva', 'Un Database Webhook avisa a n8n y la IA completa la fila.', 'intermedio', 20, ['Supabase API', 'Google Gemini']),
    ('40-proyectos', '40-agente-web3-fuji', 'Agente de IA para Fuji', 'Un agente que responde sobre Fuji con herramientas: saldo, transacción y último bloque.', 'avanzado', 30, ['Google Gemini']),
    ('40-proyectos', '41-pagos-fuji-con-login', 'Pagos en Fuji con login', 'Login con Clerk, la usuaria manda el hash de su pago, n8n lo verifica en Fuji y lo registra.', 'avanzado', 40, ['Supabase API']),
    ('40-proyectos', '42-reporte-kpis', 'Reporte de KPIs del evento', 'Cuenta los proyectos por tecnología, línea y mención, trae el tráfico de los repos y verifica los hashes en Fuji.', 'intermedio', 20, ['GitHub']),
    ('50-google-cloud', '50-vertex-ai-asistente', 'Asistente con Gemini en Vertex AI', 'Un agente con Gemini en Vertex AI que usa los créditos de Google Cloud.', 'intermedio', 25, ['Google Service Account API']),
    ('50-google-cloud', '51-sentimiento-natural-language', 'Sentimiento de opiniones', 'Un formulario de opiniones, Cloud Natural Language saca el sentimiento y las entidades, y arma un resumen.', 'intermedio', 20, ['Google Service Account API']),
    ('50-google-cloud', '52-traducir-y-resumir', 'Traducir y resumir', 'Traduce con Cloud Translation y resume con Gemini.', 'intermedio', 20, ['Google Service Account API']),
    ('50-google-cloud', '53-archivos-a-cloud-storage', 'Archivos a Cloud Storage', 'Un formulario con archivo lo sube a un bucket de Cloud Storage y devuelve el enlace.', 'intermedio', 20, ['Google Service Account API']),
    ('50-google-cloud', '54-bigquery-respuestas', 'Respuestas en BigQuery', 'Guarda respuestas en BigQuery y las consulta.', 'avanzado', 25, ['Google Service Account API'], 'opcional'),
    ('60-casos-de-uso', '60-alerta-del-clima', 'Alerta del clima', 'Revisa el pronóstico de Santa Cruz con Open-Meteo y avisa si llueve o hace calor extremo.', 'inicial', 15, []),
    ('60-casos-de-uso', '61-tipo-de-cambio', 'Tipo de cambio', 'La cotización del dólar en bolivianos con una API pública sin clave.', 'inicial', 10, []),
    ('60-casos-de-uso', '62-noticias-rss', 'Noticias por RSS', 'Lee un RSS público, filtra por palabras y arma un resumen.', 'inicial', 15, []),
    ('60-casos-de-uso', '63-leer-una-pagina-web', 'Leer una página web', 'HTTP Request y el nodo HTML para sacar datos de una página pública.', 'inicial', 15, []),
    ('60-casos-de-uso', '64-limpiar-una-lista', 'Limpiar una lista', 'Datos de ejemplo en CSV: limpiar, sacar repetidos y validar correos, y armar un archivo listo.', 'inicial', 15, []),
    ('60-casos-de-uso', '65-clasificar-mensajes-con-ia', 'Clasificar mensajes con IA', 'Gemini clasifica cada mensaje en consulta, reclamo o idea.', 'inicial', 15, ['Google Gemini(PaLM) Api']),
    ('60-casos-de-uso', '66-bot-de-telegram-con-ia', 'Bot de Telegram con IA', 'Un bot de Telegram que responde con un agente de IA.', 'intermedio', 25, ['Telegram API', 'Google Gemini(PaLM) Api']),
    ('60-casos-de-uso', '67-reportes-ambientales', 'Reportes ambientales', 'Un formulario ciudadano con foto: la IA clasifica el reporte, se guarda en Supabase y avisa.', 'intermedio', 30, ['Google Gemini(PaLM) Api', 'Supabase API']),
]

# Material de apoyo que acompaña a los workflows.
APOYO = [
    ('supabase/sql', 'El esquema de Supabase: tablas `perfiles`, `ideas`, `pagos_fuji` y `documentos` (pgvector), la función de búsqueda y la seguridad por filas (RLS) explicada.'),
    ('clerk/app-ejemplo', 'Una página mínima con Clerk que inicia sesión y llama a un webhook protegido de n8n con el token de sesión: el circuito login → n8n → Supabase.'),
    ('avalanche/contratos', 'Un contrato simple en Solidity, la guía para desplegarlo en Fuji con Remix y Core Wallet, y cómo leer sus eventos con el workflow 16.'),
]


def celda(s):
    """Texto seguro para una celda de tabla de Markdown."""
    return re.sub(r'\s+', ' ', str(s or '')).replace('|', '\\|').strip()


def lineas_de(meta, carpeta):
    """Las líneas del meta.json como texto corto para la celda («las 4» si sirve para todas)."""
    ids = meta.get('lineas') if meta else None
    if not ids:
        return '—'
    malas = [x for x in ids if x not in LINEAS]
    if malas:
        print(f'  ojo: {carpeta}/meta.json tiene líneas desconocidas: {", ".join(map(str, malas))}')
    buenas = [x for x in LINEAS if x in ids]  # en el orden de las líneas, sin repetir
    if len(buenas) == len(LINEAS):
        return 'las 4'
    return '<br>'.join(LINEAS[x][0] for x in buenas) or '—'


def leer_meta(carpeta):
    p = WF / carpeta / 'meta.json'
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'  meta.json ilegible en {carpeta}: {e}')
        return None


def armar():
    faltan, filas_por_cat, conteo = [], {c[0]: [] for c in CATEGORIAS}, {'ejecutado': 0, 'auditado': 0}
    sin_credenciales = {c[0]: 0 for c in CATEGORIAS}
    omitidos = []
    for cat, wid, titulo, resumen, nivel, minutos, creds, *extra in LISTA:
        carpeta = f'{cat}/{wid}'
        if 'opcional' in extra and not (WF / carpeta).exists():
            omitidos.append(carpeta)
            continue
        meta = leer_meta(carpeta)
        if meta:
            if meta.get('id') != wid:
                print(f'  ojo: {carpeta}/meta.json dice id «{meta.get("id")}»')
            titulo = meta.get('titulo') or titulo
            resumen = meta.get('resumen') or resumen
            nivel = meta.get('nivel') or nivel
            minutos = meta.get('minutos') or minutos
            creds = [c.get('nombre', '') if isinstance(c, dict) else str(c) for c in meta.get('credenciales', [])]
            probado = meta.get('probado')
        else:
            faltan.append(f'{carpeta}/meta.json')
            probado = None
        if probado in conteo:
            conteo[probado] += 1
        if not (WF / carpeta / 'workflow.json').exists():
            faltan.append(f'{carpeta}/workflow.json')
        estado = INSIGNIA.get(probado, '')
        cred = ', '.join(celda(c) for c in creds if c) or 'ninguna'
        if not [c for c in creds if c and '(opcional)' not in c]:  # sin credenciales o con todas opcionales
            sin_credenciales[cat] += 1
        filas_por_cat[cat].append(
            f'| [`{wid}`]({carpeta}) | **{celda(titulo)}**<br>{celda(resumen)} | {lineas_de(meta, carpeta)} | {celda(nivel)}<br>{minutos} min | {cred} | {estado} |')

    total = sum(len(f) for f in filas_por_cat.values())
    out = [INICIO, '']
    resumen_estado = []
    if conteo['ejecutado']:
        resumen_estado.append(f'{conteo["ejecutado"]} ejecutados de verdad')
    if conteo['auditado']:
        resumen_estado.append(f'{conteo["auditado"]} auditados')
    out.append(f'**{total} workflows en {len(CATEGORIAS)} categorías**' + (f' · {" y ".join(resumen_estado)}' if resumen_estado else '') + '.')
    out.append('')
    guias_lineas = ' · '.join(f'**{corto}**: [{largo}]({GUIAS}/lineas/{lid}.md)' for lid, (corto, largo) in LINEAS.items())
    out += [
        'La columna **Líneas** dice para qué línea de la hackathon sirve cada workflow («las 4» si sirve para cualquiera). '
        'Cada equipo elige una línea; tocá cada una para ver su guía:',
        '',
        guias_lineas,
        '',
    ]
    for cat, nombre, bajada in CATEGORIAS:
        n = len(filas_por_cat[cat])
        if cat == '60-casos-de-uso' and n:
            libres = sin_credenciales[cat]
            bajada += f' {libres} de {n} corren sin credenciales.' if libres else ''
        out += [f'### [{nombre}]({cat}) · {n} workflows', '', bajada, '']
        if cat == '10-avalanche-fuji':
            out += [
                '> **Antes de empezar con Fuji:**'
                f' [Descargá Core Wallet](https://core.app/?{UTM}) y activá el modo testnet ·'
                ' [Pedí AVAX de prueba en el faucet](https://build.avax.network/console/primary-network/faucet) ·'
                f' [Aprendé en Avalanche Academy](https://build.avax.network/academy?{UTM}) ·'
                f' [Sumate a Team1](https://www.team1.network/?{UTM}) ·'
                ' [Explorá tus transacciones](https://build.avax.network/explorer/fuji/c-chain)',
                '>',
                f'> Red: Avalanche Fuji C-Chain · chainId `{CONFIG["fuji"]["chain_id"]}` (`{CONFIG["fuji"]["chain_id_hex"]}`) · RPC público `{CONFIG["fuji"]["rpc"]}`',
                '',
            ]
        out += ['| Workflow | Qué hace | Líneas | Nivel | Credenciales | Estado |', '|---|---|---|---|---|---|', *filas_por_cat[cat], '']
    out += ['### Material de apoyo', '', '| Carpeta | Qué tiene |', '|---|---|']
    for carpeta, que in APOYO:
        out.append(f'| [`{carpeta}/`]({carpeta}) | {que} |')
        if not (WF / carpeta).exists():
            faltan.append(f'{carpeta}/')
    out += ['', FIN]
    for o in omitidos:
        print(f'  {o}: es opcional y todavía no existe, no entra en el catálogo.')
    return '\n'.join(out), faltan


def main():
    if not README.exists():
        sys.exit(f'No encuentro {README}')
    actual = README.read_text(encoding='utf-8')
    a, b = actual.find(INICIO), actual.find(FIN)
    if a < 0 or b < a:
        sys.exit(f'El README no tiene las marcas {INICIO} y {FIN}.')
    bloque, faltan = armar()
    nuevo = actual[:a] + bloque + actual[b + len(FIN):]
    if nuevo != actual:
        README.write_text(nuevo, encoding='utf-8', newline='\n')
        print('Catálogo del README actualizado.')
    else:
        print('El catálogo ya estaba al día.')
    if faltan:
        print(f'Faltan {len(faltan)} archivos o carpetas (la fila sale con los datos de la especificación, sin líneas y sin insignia):')
        for f in faltan:
            print('  -', f)
        return 1
    print('Todos los workflows tienen su meta.json y su workflow.json.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
