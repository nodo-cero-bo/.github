# -*- coding: utf-8 -*-
"""Arma el catálogo del README del repo de workflows a partir de los meta.json.

Qué hace: recorre la lista fija de workflows de la especificación (los ids no cambian: la página y las guías los nombran así),
lee el meta.json de cada carpeta (título, resumen, nivel, minutos, credenciales y si fue «ejecutado» o «auditado») y
reescribe la tabla por categoría entre las marcas <!-- catalogo:inicio --> y <!-- catalogo:fin --> de workflows/README.md.
Lo demás del README no se toca.

Si una carpeta todavía no tiene meta.json, la fila sale con los datos de la especificación y sin insignia,
y el script lo avisa al final (sale con código 1 si falta alguno, así se nota antes de publicar).

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

INSIGNIA = {
    'ejecutado': '![ejecutado](https://img.shields.io/badge/ejecutado-FF91AC?style=flat-square)',
    'auditado': '![auditado](https://img.shields.io/badge/auditado-5A0026?style=flat-square)',
}

# Categorías en el orden del repo. La bajada se muestra arriba de cada tabla.
CATEGORIAS = [
    ('00-fundamentos', 'Fundamentos',
     'Para arrancar de cero: datos, expresiones, tu primera API, HTTP Request, formularios y tu primer agente de IA. '
     'Ninguno pide credenciales, salvo el agente (una clave gratis de Google AI Studio).'),
    ('10-avalanche-fuji', 'Avalanche Fuji',
     'Leé la red de prueba de Avalanche con su RPC público: sin cuentas y sin claves privadas. '
     'Es el track de Avalanche Fuji, con mención especial para los equipos que lo integren.'),
    ('20-clerk', 'Clerk',
     'Login y usuarias con Clerk conectado a n8n: webhooks firmados, una API que exige sesión e invitaciones. '
     'Hay mención al mejor uso de Clerk.'),
    ('30-supabase', 'Supabase',
     'Postgres, tu propia API y búsqueda en tus documentos con pgvector. El esquema de las tablas está en [`supabase/sql/`](supabase/sql).'),
    ('40-proyectos', 'Proyectos completos',
     'Juntan varias piezas de punta a punta, para partir de algo grande y hacerlo tuyo.'),
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
    ('40-proyectos', '42-reporte-kpis', 'Reporte de KPIs del evento', 'Cuenta los proyectos por tecnología, trae el tráfico de los repos y verifica los hashes en Fuji.', 'intermedio', 20, ['GitHub']),
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
    for cat, wid, titulo, resumen, nivel, minutos, creds in LISTA:
        carpeta = f'{cat}/{wid}'
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
        filas_por_cat[cat].append(
            f'| [`{wid}`]({carpeta}) | **{celda(titulo)}**<br>{celda(resumen)} | {celda(nivel)}<br>{minutos} min | {cred} | {estado} |')

    total = len(LISTA)
    out = [INICIO, '']
    resumen_estado = []
    if conteo['ejecutado']:
        resumen_estado.append(f'{conteo["ejecutado"]} ejecutados de verdad')
    if conteo['auditado']:
        resumen_estado.append(f'{conteo["auditado"]} auditados')
    out.append(f'**{total} workflows en {len(CATEGORIAS)} categorías**' + (f' · {" y ".join(resumen_estado)}' if resumen_estado else '') + '.')
    out.append('')
    for cat, nombre, bajada in CATEGORIAS:
        n = len(filas_por_cat[cat])
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
        out += ['| Workflow | Qué hace | Nivel | Credenciales | Estado |', '|---|---|---|---|---|', *filas_por_cat[cat], '']
    out += ['### Material de apoyo', '', '| Carpeta | Qué tiene |', '|---|---|']
    for carpeta, que in APOYO:
        out.append(f'| [`{carpeta}/`]({carpeta}) | {que} |')
        if not (WF / carpeta).exists():
            faltan.append(f'{carpeta}/')
    out += ['', FIN]
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
        print(f'Faltan {len(faltan)} archivos o carpetas (la fila sale con los datos de la especificación y sin insignia):')
        for f in faltan:
            print('  -', f)
        return 1
    print('Todos los workflows tienen su meta.json y su workflow.json.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
