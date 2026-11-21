# -*- coding: utf-8 -*-
"""Cabeceras de los repos de Nodo Cero, banner del perfil de la organización y logos de la portada.

Qué hace:
  1. Las imágenes de cabecera (1280 x 640, también sirven como vista previa social de cada repo):
       workflows/assets/cabecera.png, guias/assets/cabecera.png, proyectos/assets/cabecera.png, sitio/assets/cabecera.png
     y el banner del perfil (1600 x 500): org-perfil/profile/banner.png.
  2. Los logos de la portada de la organización, en una versión para el tema oscuro y otra para el claro de GitHub:
       org-perfil/profile/assets/<marca>-oscuro.png y <marca>-claro.png (y una copia en guias/assets/aliados/)

Cómo se dibuja: cada pieza es una página HTML con el lenguaje de Nodo Cero (fondo #191919 con la grilla de puntos de n8n,
nodos conectados con líneas rosas y puertos blancos, halos rosas, Inter Tight y Geist Mono de fuentes/). Se renderiza al doble
con el Chrome sin interfaz de Remotion y se baja a la medida final con Pillow (LANCZOS).

Los logos son los oficiales de marcas/ y el de Nodo Cero sale del kit (salida/kit_marketing/.../01_logos/nodo_cero/svg/).
Ninguno se redibuja ni se recolorea: los SVG se rasterizan tal cual y lo único que se recorta es su margen transparente.
El de Aspire Institute no tiene versión para fondo oscuro: sobre lo oscuro va tal cual, en una placa clara (#FAFAFA, con aire).

Al final audita cada pieza:
  - con el DOM: que todo texto y logo quede dentro de la zona segura, que nada se pise y que ningún texto se corte;
  - con un render sin textos: el contraste de cada texto contra lo que tiene detrás (4,5:1, o 3:1 desde 24 px);
  - los nodos contra el fondo (3:1), que ningún logo aliado pese más que n8n y que cada imagen pese menos de 1 MB.
Sale con código 1 si algo falla.

Uso (desde cualquier carpeta):  python -X utf8 org-perfil/tools/cabeceras.py [workflows guias proyectos sitio banner logos]
"""
import base64
import html as _html
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
GH = AQUI.parent.parent                       # github_nodo_cero/
RAIZ = GH.parent                              # Nueva carpeta/
CHROME = RAIZ / 'remotion/node_modules/.remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe'
FUENTES = RAIZ / 'fuentes'
MARCAS = RAIZ / 'marcas'
NC_SVG = RAIZ / 'salida/kit_marketing/Kit_marketing_Nodo_Cero/01_logos/nodo_cero/svg'
CONFIG = json.loads((GH / 'config.json').read_text(encoding='utf-8'))
ORG = CONFIG['org']
ESCALA = 2                                    # se renderiza al doble y se baja con LANCZOS
LIMITE_BYTES = 1_000_000

ROSA, NEGRO, BLANCO, BORDO, ROSA20 = '#FF91AC', '#191919', '#FAFAFA', '#5A0026', '#FFD0D9'
GRIS90, GRIS80, GRIS70 = '#242424', '#464646', '#676767'


def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode('ascii')


def uri_png(im):
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def uri(p):
    p = Path(p)
    tipo = {'.svg': 'image/svg+xml', '.png': 'image/png'}[p.suffix.lower()]
    return f'data:{tipo};base64,{b64(p)}'


CSS_FUENTES = f'''
@font-face {{ font-family: 'Inter Tight'; font-weight: 400; src: url(data:font/ttf;base64,{b64(FUENTES / 'InterTight-400.ttf')}); }}
@font-face {{ font-family: 'Inter Tight'; font-weight: 500; src: url(data:font/ttf;base64,{b64(FUENTES / 'InterTight-500.ttf')}); }}
@font-face {{ font-family: 'Geist Mono'; font-weight: 400; src: url(data:font/ttf;base64,{b64(FUENTES / 'GeistMono-400.ttf')}); }}
'''


# ---------------------------------------------------------------- Chrome
def chrome(args, url, timeout=180):
    ud = Path(tempfile.mkdtemp(prefix='ud_'))
    try:
        r = subprocess.run([str(CHROME), '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars', '--no-first-run',
                            '--virtual-time-budget=8000', f'--user-data-dir={ud}', *args, url],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return r
    finally:
        shutil.rmtree(ud, ignore_errors=True)


def captura(html, w, h, destino, escala=ESCALA, transparente=False):
    """Renderiza la página a w*escala x h*escala y devuelve la imagen (RGBA)."""
    tmp = Path(tempfile.mkdtemp(prefix='cab_'))
    try:
        pag = tmp / 'p.html'
        pag.write_text(html, encoding='utf-8')
        png = tmp / 'p.png'
        extra = ['--default-background-color=00000000'] if transparente else []
        r = chrome([f'--window-size={w},{h}', f'--force-device-scale-factor={escala}', f'--screenshot={png}', *extra], pag.as_uri())
        if not png.exists():
            raise RuntimeError(f'Chrome no dejó la captura de {destino}: {r.stderr[-400:]}')
        im = Image.open(png).convert('RGBA')
        im.load()
        return im
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cajas_dom(html, w, h):
    """Corre la página y devuelve las cajas de los elementos marcados con data-k (texto, logo, gráfico)."""
    tmp = Path(tempfile.mkdtemp(prefix='dom_'))
    try:
        pag = tmp / 'p.html'
        pag.write_text(html.replace('</body>', SCRIPT_CAJAS + '</body>'), encoding='utf-8')
        r = chrome([f'--window-size={w},{h}', '--force-device-scale-factor=1', '--dump-dom'], pag.as_uri())
        m = re.search(r'<pre id="cajas">(.*?)</pre>', r.stdout, re.S)
        if not m:
            raise RuntimeError('no salieron las cajas del DOM: ' + r.stderr[-300:])
        return json.loads(_html.unescape(m.group(1)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SCRIPT_CAJAS = '''<pre id="cajas"></pre><script>
document.fonts.ready.then(function () {
  var out = [];
  document.querySelectorAll('[data-k]').forEach(function (e) {
    var r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    out.push({k: e.dataset.k, n: e.dataset.n || '', x: r.left, y: r.top, w: r.width, h: r.height,
              color: cs.color, fs: parseFloat(cs.fontSize), sw: e.scrollWidth, cw: e.clientWidth, sh: e.scrollHeight, ch: e.clientHeight,
              peso: parseFloat(e.dataset.peso || '0'), texto: (e.innerText || '').trim()});
  });
  document.getElementById('cajas').textContent = JSON.stringify(out);
});
</script>'''


# ---------------------------------------------------------------- logos
# Archivo oficial por fondo (marcas/PROCEDENCIA.md). cob: fracción de la caja que es tinta, para pesar cada logo a la vista.
LOGOS = {
    'n8n':      {'oscuro': MARCAS / 'n8n/n8n-logo-white-accent.png', 'claro': MARCAS / 'n8n/n8n-logo-black-accent.png',
                 'nombre': 'n8n', 'url': 'https://n8n.io'},
    'supabase': {'oscuro': MARCAS / 'supabase/supabase-logo-wordmark--dark.svg', 'claro': MARCAS / 'supabase/supabase-logo-wordmark--light.svg',
                 'nombre': 'Supabase', 'url': 'https://supabase.com'},
    'clerk':    {'oscuro': MARCAS / 'clerk/logotype-full-primary-light.svg', 'claro': MARCAS / 'clerk/logotype-full-primary.svg',
                 'nombre': 'Clerk', 'url': 'https://clerk.com'},
    'team1':    {'oscuro': MARCAS / 'team1/Team1_MAIN_WHITE.svg', 'claro': MARCAS / 'team1/Team1_BLACK_MAIN.svg',
                 'nombre': 'Team1', 'url': 'https://team1.network'},
    'wtm':      {'oscuro': MARCAS / 'wtm-santa-cruz/wtm-santa-cruz-para-fondo-oscuro.png', 'claro': MARCAS / 'wtm-santa-cruz/wtm-santa-cruz-para-fondo-claro.png',
                 'nombre': 'Women Techmakers Santa Cruz', 'url': 'https://www.instagram.com/wtmsantacruz/'},
    'gobierno': {'oscuro': MARCAS / 'gobierno-santa-cruz/logo-scz-white-v2.png', 'claro': MARCAS / 'gobierno-santa-cruz/logo-scz.png',
                 'nombre': 'Gobierno Autónomo Departamental de Santa Cruz', 'url': 'https://www.santacruz.gob.bo'},
    'nodo-cero': {'oscuro': NC_SVG / 'nodo-cero_horizontal_fondo-oscuro.svg', 'claro': NC_SVG / 'nodo-cero_horizontal_fondo-claro.svg',
                  'nombre': 'Nodo Cero'},
    # Aspire Institute no tiene versión para fondo oscuro: no se recolorea, sobre lo oscuro va el mismo logo rojo en una placa clara.
    'aspire':   {'oscuro': MARCAS / 'aspire-institute/aspire-institute-logo.svg', 'claro': MARCAS / 'aspire-institute/aspire-institute-logo.svg',
                 'png': MARCAS / 'aspire-institute/aspire-institute-logo.png', 'placa': True,
                 'nombre': 'Aspire Institute', 'url': 'https://www.aspireleaders.org'},
}
# La placa clara de los logos sin versión para fondo oscuro: rectángulo redondeado #FAFAFA con aire alrededor de la tinta.
# Las medidas son fracciones del alto de la tinta (arriba y abajo, a los costados, radio de la esquina).
PLACA = {'color': BLANCO, 'v': .24, 'h': .38, 'r': .28}
ALIADOS = ('supabase', 'clerk', 'team1', 'aspire', 'wtm', 'gobierno')
_CACHE = {}


def rasterizar(ruta, alto=480):
    """El logo como PNG RGBA recortado a su tinta. Los SVG se rasterizan tal cual con Chrome (sin tocar colores ni formas)."""
    ruta = Path(ruta)
    clave = (ruta, alto)
    if clave in _CACHE:
        return _CACHE[clave]
    if ruta.suffix.lower() == '.png':
        im = Image.open(ruta).convert('RGBA')
    else:
        svg = ruta.read_text(encoding='utf-8')
        m = re.search(r'viewBox="([\d.\s-]+)"', svg)
        vb = [float(v) for v in m.group(1).split()]
        prop = vb[2] / vb[3]
        w = math.ceil(alto * prop)
        html = (f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}'
                f'img{{display:block;width:{w}px;height:{alto}px}}</style></head><body><img src="{uri(ruta)}"></body></html>')
        im = captura(html, w, alto, ruta.name, escala=1, transparente=True)
    alfa = im.split()[-1].point(lambda v: 255 if v > 6 else 0)
    im = im.crop(alfa.getbbox())
    _CACHE[clave] = im
    return im


def cobertura(im):
    a = im.split()[-1]
    hist = a.histogram()
    return sum(i * c for i, c in enumerate(hist)) / (255 * im.width * im.height)


def logo_tag(marca, alto, fondo='oscuro', extra='', n=None):
    """<img> del logo con su tinta a `alto` px. data-peso = área de tinta a la vista, para comparar con n8n.
    Si la marca va en placa clara (y el fondo es oscuro), devuelve la placa con el logo adentro: la placa entera cuenta como peso."""
    im = rasterizar(LOGOS[marca][fondo])
    ancho = alto * im.width / im.height
    alt = _html.escape(LOGOS[marca]['nombre'])
    if LOGOS[marca].get('placa') and fondo == 'oscuro':
        pv, ph, r = alto * PLACA['v'], alto * PLACA['h'], alto * PLACA['r']
        pw, pa = ancho + 2 * ph, alto + 2 * pv
        return (f'<div data-k="l" data-n="{n or marca}" data-peso="{pw * pa:.0f}" class="placa" '
                f'style="display:flex;flex:none;align-items:center;justify-content:center;width:{pw:.1f}px;height:{pa:.1f}px;'
                f'background:{PLACA["color"]};border-radius:{r:.1f}px;{extra}">'
                f'<img src="{uri_png(im)}" style="display:block;flex:none;width:{ancho:.1f}px;height:{alto:.1f}px" alt="{alt}"></div>'), pw
    peso = ancho * alto * cobertura(im)
    return (f'<img data-k="l" data-n="{n or marca}" data-peso="{peso:.0f}" src="{uri_png(im)}" '
            f'style="display:block;flex:none;width:{ancho:.1f}px;height:{alto:.1f}px;{extra}" alt="{alt}">'), ancho


# ---------------------------------------------------------------- íconos (trazos propios, genéricos: no son logos de nadie)
ICONOS = {
    'cursor':    '<path d="M6 3.5l12 7.2-5.3 1.3 3.2 6.1-2.6 1.4-3.2-6.2L6 17.2z"/>',
    'webhook':   '<path d="M3.5 12h11"/><path d="M10.5 7.5L15 12l-4.5 4.5"/><path d="M17 4.5h3v15h-3"/>',
    'llaves':    '<path d="M9 4.5c-2 0-3 1-3 3v2c0 1.3-.7 2.2-2 2.5 1.3.3 2 1.2 2 2.5v2c0 2 1 3 3 3"/><path d="M15 4.5c2 0 3 1 3 3v2c0 1.3.7 2.2 2 2.5-1.3.3-2 1.2-2 2.5v2c0 2-1 3-3 3"/>',
    'globo':     '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/><path d="M12 3.5c2.6 2.6 3.8 5.4 3.8 8.5s-1.2 5.9-3.8 8.5c-2.6-2.6-3.8-5.4-3.8-8.5S9.4 6.1 12 3.5z"/>',
    'chispa':    '<path d="M12 3c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7z"/><path d="M18.5 15.5c.3 1.8 1 2.5 2.5 2.8-1.5.3-2.2 1-2.5 2.7-.3-1.7-1-2.4-2.5-2.7 1.5-.3 2.2-1 2.5-2.8z"/>',
    'base':      '<ellipse cx="12" cy="6" rx="7" ry="2.8"/><path d="M5 6v12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8V6"/><path d="M5 12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8"/>',
    'cadena':    '<rect x="3" y="8.5" width="9" height="7" rx="3.5"/><rect x="12" y="8.5" width="9" height="7" rx="3.5"/>',
    'libro':     '<path d="M4 5.5c2.8-.9 5.5-.6 8 1.2 2.5-1.8 5.2-2.1 8-1.2v13c-2.8-.9-5.5-.6-8 1.2-2.5-1.8-5.2-2.1-8-1.2z"/><path d="M12 6.7v13"/>',
    'llave':     '<circle cx="8" cy="12" r="4"/><path d="M12 12h8.5"/><path d="M17 12v3.5"/><path d="M20 12v2.5"/>',
    'persona':   '<circle cx="10" cy="8" r="3.6"/><path d="M3.5 19.5c.8-3.6 3.3-5.5 6.5-5.5s5.7 1.9 6.5 5.5"/><path d="M19 7.5v6"/><path d="M16 10.5h6"/>',
    'importar':  '<path d="M12 3.5v10"/><path d="M8 9.5l4 4 4-4"/><path d="M4.5 15v3.5c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V15"/>',
    'pantalla':  '<rect x="3.5" y="4.5" width="17" height="11" rx="1.6"/><path d="M12 15.5v4"/><path d="M8 20h8"/><path d="M8 12l2.5-3 2.2 2 3-3.5"/>',
    'formulario': '<rect x="4.5" y="3.5" width="15" height="17" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>',
    'issue':     '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    'grilla':    '<rect x="4" y="4" width="6.8" height="6.8" rx="1.4"/><rect x="13.2" y="4" width="6.8" height="6.8" rx="1.4"/><rect x="4" y="13.2" width="6.8" height="6.8" rx="1.4"/><rect x="13.2" y="13.2" width="6.8" height="6.8" rx="1.4"/>',
    'barras':    '<path d="M4 20h16"/><rect x="5.5" y="12" width="3" height="6" rx=".8"/><rect x="10.5" y="7" width="3" height="11" rx=".8"/><rect x="15.5" y="4" width="3" height="14" rx=".8"/>',
    'copiar':    '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 5.5V5a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 5v8A1.5 1.5 0 0 0 6 14.5h.5"/>',
    'lienzo':    '<rect x="3" y="9.5" width="5" height="5" rx="1.2"/><rect x="16" y="4" width="5" height="5" rx="1.2"/><rect x="16" y="15" width="5" height="5" rx="1.2"/><path d="M8 12h3.5c1.4 0 1.5-5.5 4.5-5.5"/><path d="M11.5 12c1.4 0 1.5 5.5 4.5 5.5"/>',
    'check':     '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.3l2.8 2.7L16.2 9.5"/>',
    'cohete':    '<path d="M12 3c3.5 2.2 5 5.6 4.5 10.5l-2 2.5h-5l-2-2.5C7 8.6 8.5 5.2 12 3z"/><circle cx="12" cy="9.5" r="1.8"/><path d="M9.5 16l-1.5 4 2.5-1.5"/><path d="M14.5 16l1.5 4-2.5-1.5"/>',
}


def icono(nombre, tam, color):
    return (f'<svg viewBox="0 0 24 24" width="{tam}" height="{tam}" fill="none" stroke="{color}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" style="color:{color};display:block">{ICONOS[nombre]}</svg>')


# ---------------------------------------------------------------- piezas comunes
COMUN = '''
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #191919; }
body { position: relative; overflow: hidden; font-family: 'Inter Tight', sans-serif; font-weight: 400; color: #FAFAFA;
       -webkit-font-smoothing: antialiased; font-feature-settings: "liga" 1; }
.a { position: absolute; }
.t { white-space: nowrap; line-height: 1.1; }
.m { font-family: 'Geist Mono', monospace; text-transform: uppercase; letter-spacing: .02em; }
.nodo { position: absolute; display: flex; align-items: center; justify-content: center;
        background: linear-gradient(160deg, #343434 0%, #262626 100%); border: 2px solid #8C8C8C; border-radius: 18px;
        box-shadow: 0 10px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.08); }
.nodo { z-index: 2; } .nodo.heroe { z-index: 1; }
.nodo.disparador { border-radius: 50% 18px 18px 50% / 50% 18px 18px 50%; }
.nodo.heroe { background: linear-gradient(160deg, #FFA9BE 0%, #FF91AC 55%, #F67F9D 100%); border-color: #FFD0D9;
              box-shadow: 0 0 0 6px rgba(255,145,172,.16), 0 0 56px 10px rgba(255,145,172,.50), 0 0 140px 40px rgba(255,145,172,.20); }
.puerto { position: absolute; width: 16px; height: 16px; border-radius: 50%; background: #FAFAFA; top: 50%; margin-top: -8px;
          box-shadow: 0 0 0 3px #191919, 0 0 12px rgba(255,255,255,.55); }
.puerto.in { left: -9px; } .puerto.out { right: -9px; }
.etq { position: absolute; display: inline-block; transform: translateX(-50%); text-align: center; font-size: 19px; font-weight: 500; color: #FAFAFA;
        white-space: nowrap; line-height: 1.15; text-shadow: 0 0 6px #191919, 0 0 14px #191919; }
.etq small { display: block; font-family: 'Geist Mono', monospace; font-size: 13px; font-weight: 400; color: #BFBFBF; letter-spacing: .04em; text-transform: uppercase; margin-top: 4px; }
.caps { display: flex; align-items: center; }
.caps .p { width: 12px; height: 12px; border-radius: 50%; background: #FAFAFA; flex: none; margin: 0 -6px; position: relative; z-index: 2; }
.caps .c { height: 40px; padding: 0 20px; border-radius: 400px; display: flex; align-items: center; font-family: 'Geist Mono', monospace;
           font-size: 18px; letter-spacing: .02em; text-transform: uppercase; white-space: nowrap; }
.caps.grande .p { width: 14px; height: 14px; margin: 0 -7px; }
.caps.grande .c { height: 50px; padding: 0 26px; font-size: 23px; }
.caps .c.rosa { background: #FF91AC; color: #191919; }
.caps .c.gris { background: #3A3A3A; color: #FAFAFA; }
.sin [data-k="t"], .sin [data-k="t"] * { color: transparent !important; }
.sin .caps .c { color: transparent !important; }
.sin img[data-k="l"], .sin .placa img { visibility: hidden; }
'''


def fondo(w, h, halos, encendido, grid=24):
    """Lienzo #191919 con la grilla de puntos de n8n (Gray 80), halos rosas y la grilla encendida en rosa claro cerca del flujo."""
    capas = [f'<div class="a" style="inset:0;background:{NEGRO}"></div>']
    for (x, y, rx, ry, a) in halos:
        capas.append(f'<div class="a" style="inset:0;background:radial-gradient(ellipse {rx}px {ry}px at {x}px {y}px, '
                     f'rgba(255,145,172,{a}) 0%, rgba(90,0,38,{a * .55:.3f}) 46%, rgba(90,0,38,0) 100%)"></div>')
    capas.append(f'<div class="a" style="inset:0;background-image:radial-gradient(circle, {GRIS80} 1.5px, transparent 2px);'
                 f'background-size:{grid}px {grid}px;background-position:{grid // 2}px {grid // 2}px;opacity:.75"></div>')
    ex, ey, erx, ery = encendido
    mask = f'radial-gradient(ellipse {erx}px {ery}px at {ex}px {ey}px, #000 0%, rgba(0,0,0,.55) 45%, transparent 100%)'
    capas.append(f'<div class="a" style="inset:0;background-image:radial-gradient(circle, {ROSA20} 1.6px, transparent 2.1px);'
                 f'background-size:{grid}px {grid}px;background-position:{grid // 2}px {grid // 2}px;opacity:.55;'
                 f'-webkit-mask-image:{mask};mask-image:{mask}"></div>')
    capas.append(f'<div class="a" style="inset:0;background:radial-gradient(ellipse {w * .75:.0f}px {h * .9:.0f}px at 50% 50%, '
                 f'rgba(0,0,0,0) 55%, rgba(0,0,0,.42) 100%)"></div>')
    return ''.join(capas)


def destello(x, y, tam, color=BLANCO, op=.95):
    """Un destello de cuatro puntas con su brillo."""
    return (f'<svg class="a" style="left:{x - tam}px;top:{y - tam}px;overflow:visible" width="{2 * tam}" height="{2 * tam}" viewBox="-12 -12 24 24">'
            f'<circle r="7" fill="{ROSA}" opacity=".35" filter="url(#bl6)"/>'
            f'<path d="M0-12C.9-3 3-1 12 0 3 1 .9 3 0 12-.9 3-3 1-12 0-3-1-.9-3 0-12z" fill="{color}" opacity="{op}"/></svg>')


def flujo(nodos, conexiones, w, h, chispas=()):
    """Nodos de n8n conectados. nodos: id -> dict(x, y, s, icono, etq, sub, heroe, disparador). conexiones: (de, a)."""
    svg = [f'<svg class="a" style="left:0;top:0;overflow:visible" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           '<defs><filter id="bl6" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3"/></filter>'
           '<filter id="bl10" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter></defs>']
    caminos = []
    for (a, b) in conexiones:
        na, nb = nodos[a], nodos[b]
        x1, y1 = na['x'] + na['s'] + 1, na['y'] + na['s'] / 2
        x2, y2 = nb['x'] - 1, nb['y'] + nb['s'] / 2
        dx = max(40, (x2 - x1) * .5)
        d = f'M{x1:.1f} {y1:.1f} C{x1 + dx:.1f} {y1:.1f} {x2 - dx:.1f} {y2:.1f} {x2:.1f} {y2:.1f}'
        caminos.append(d)
        svg.append(f'<path d="{d}" stroke="rgba(255,145,172,.55)" stroke-width="12" fill="none" filter="url(#bl10)"/>')
        svg.append(f'<path d="{d}" stroke="{ROSA}" stroke-width="3.5" fill="none" stroke-linecap="round"/>')
        # el pulso que viaja por la conexión: un tramo claro con brillo
        svg.append(f'<path d="{d}" pathLength="100" stroke="{ROSA20}" stroke-width="5" fill="none" stroke-linecap="round" '
                   f'stroke-dasharray="7 93" stroke-dashoffset="-46" filter="url(#bl6)"/>')
        svg.append(f'<path d="{d}" pathLength="100" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round" '
                   f'stroke-dasharray="4 96" stroke-dashoffset="-47.5"/>')
    svg.append('</svg>')
    partes = [''.join(svg)]
    for nid, n in nodos.items():
        s = n['s']
        clases = 'nodo' + (' heroe' if n.get('heroe') else '') + (' disparador' if n.get('disparador') else '')
        color = NEGRO if n.get('heroe') else BLANCO
        puertos = ('' if n.get('disparador') else '<span class="puerto in"></span>') + ('' if n.get('fin') else '<span class="puerto out"></span>')
        if n.get('heroe'):
            # halo y ondas del nodo principal
            partes.append(f'<div class="a" style="left:{n["x"] + s / 2 - 170}px;top:{n["y"] + s / 2 - 170}px;width:340px;height:340px;border-radius:50%;'
                          f'background:radial-gradient(circle, rgba(255,145,172,.30) 0%, rgba(255,145,172,.10) 40%, rgba(255,145,172,0) 70%)"></div>')
            for r, op in ((s * .5 + 26, .30), (s * .5 + 52, .16)):
                partes.append(f'<div class="a" style="left:{n["x"] + s / 2 - r}px;top:{n["y"] + s / 2 - r}px;width:{2 * r}px;height:{2 * r}px;'
                              f'border-radius:50%;border:1.5px solid rgba(255,145,172,{op})"></div>')
        partes.append(f'<div class="{clases}" data-k="g" data-n="nodo-{nid}" style="left:{n["x"]}px;top:{n["y"]}px;width:{s}px;height:{s}px">'
                      f'{icono(n["icono"], round(s * .46), color)}{puertos}</div>')
        sub = f'<small>{_html.escape(n["sub"])}</small>' if n.get('sub') else ''
        partes.append(f'<div class="etq" data-k="t" data-n="etq-{nid}" style="left:{n["x"] + s / 2}px;top:{n["y"] + s + 14}px">'
                      f'{_html.escape(n["etq"])}{sub}</div>')
    for (x, y, tam, *resto) in chispas:
        partes.append(destello(x, y, tam, *resto))
    return ''.join(partes)


def capsulas(items, extra='', grande=False):
    """Cápsulas conectadas (punto, cápsula, punto...) como en el sistema de n8n. items: (texto, 'rosa'|'gris')."""
    h = [f'<div class="caps{" grande" if grande else ""}" data-k="t" data-n="capsulas" style="{extra}"><span class="p"></span>']
    for (txt, color) in items:
        h.append(f'<span class="c {color}">{_html.escape(txt)}</span><span class="p"></span>')
    h.append('</div>')
    return ''.join(h)


def barra_superior(w, n8n_alto=48, nc_alto=92, margen=64, top=48):
    """n8n (presenta) arriba a la izquierda y el logo de Nodo Cero arriba a la derecha."""
    n8n, n8n_w = logo_tag('n8n', n8n_alto)
    nc, nc_w = logo_tag('nodo-cero', nc_alto)          # alto de la tinta = alto del nodo del «0»
    pres = (f'<div class="a t m" data-k="t" data-n="presenta" style="left:{margen + n8n_w + 18}px;top:{top + n8n_alto - 19}px;'
            f'font-size:15px;color:#BFBFBF;letter-spacing:.08em">Presenta</div>')
    return (f'<div class="a" style="left:{margen}px;top:{top}px">{n8n}</div>{pres}'
            f'<div class="a" style="left:{w - margen - nc_w:.1f}px;top:{top + n8n_alto / 2 - nc_alto / 2:.1f}px">{nc}</div>')


def pagina(w, h, cuerpo, clase=''):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS_FUENTES}{COMUN}'
            f'body{{width:{w}px;height:{h}px}}</style></head><body class="{clase}">{cuerpo}</body></html>')


# ---------------------------------------------------------------- las cabeceras de 1280 x 640
W, H = 1280, 640
M = 64

FLUJOS = {
    'workflows': dict(
        nodos={
            'a': dict(x=716, y=286, s=96, icono='webhook', etq='Webhook', disparador=True),
            'b': dict(x=872, y=276, s=116, icono='llaves', etq='Tu workflow', sub='importado', heroe=True),
            'c': dict(x=1084, y=172, s=96, icono='chispa', etq='Agente de IA'),
            'd': dict(x=1084, y=392, s=96, icono='base', etq='Supabase', fin=True),
        },
        conexiones=[('a', 'b'), ('b', 'c'), ('b', 'd')],
        chispas=[(1042, 150, 9), (842, 236, 6, ROSA20), (1196, 360, 7)],
    ),
    'guias': dict(
        nodos={
            'a': dict(x=704, y=212, s=92, icono='persona', etq='Creá tu cuenta', disparador=True),
            'b': dict(x=858, y=302, s=112, icono='importar', etq='Importá', sub='el workflow', heroe=True),
            'c': dict(x=1040, y=196, s=92, icono='llave', etq='Credenciales'),
            'd': dict(x=1040, y=394, s=92, icono='pantalla', etq='Presentá', fin=True),
        },
        conexiones=[('a', 'b'), ('b', 'c'), ('b', 'd')],
        chispas=[(1166, 170, 8), (820, 270, 6, ROSA20), (1180, 470, 7)],
    ),
    'proyectos': dict(
        nodos={
            'a': dict(x=716, y=286, s=96, icono='formulario', etq='Formulario', disparador=True),
            'b': dict(x=872, y=276, s=116, icono='issue', etq='Tu proyecto', sub='registrado', heroe=True),
            'c': dict(x=1084, y=172, s=96, icono='grilla', etq='Vitrina', fin=True),
            'd': dict(x=1084, y=392, s=96, icono='barras', etq='KPIs', fin=True),
        },
        conexiones=[('a', 'b'), ('b', 'c'), ('b', 'd')],
        chispas=[(1042, 150, 9), (842, 236, 6, ROSA20), (1196, 360, 7)],
    ),
    'sitio': dict(
        nodos={
            'a': dict(x=716, y=286, s=96, icono='globo', etq='Catálogo', disparador=True),
            'b': dict(x=872, y=276, s=116, icono='copiar', etq='Copiar workflow', heroe=True),
            'c': dict(x=1084, y=172, s=96, icono='lienzo', etq='Pegar en n8n', fin=True),
            'd': dict(x=1084, y=392, s=96, icono='importar', etq='Descargar', fin=True),
        },
        conexiones=[('a', 'b'), ('b', 'c'), ('b', 'd')],
        chispas=[(1042, 150, 9), (842, 236, 6, ROSA20), (1196, 360, 7)],
    ),
}

TEXTOS = {
    'workflows': dict(cap=[('Workflows', 'rosa'), ('Listos para importar', 'gris')], titulo='Workflows',
                      bajada='Fundamentos, IA, Google Cloud, Avalanche Fuji, Clerk, Supabase y casos de uso: copialos, importalos y seguí construyendo.',
                      url=f'github.com/{ORG}/workflows'),
    'guias': dict(cap=[('Guías', 'rosa'), ('Paso a paso', 'gris')], titulo='Guías',
                  bajada='Creá tus cuentas, importá workflows, conectá credenciales y presentá tu proyecto.',
                  url=f'github.com/{ORG}/guias'),
    'proyectos': dict(cap=[('Vitrina', 'rosa'), ('Proyectos del día', 'gris')], titulo='Proyectos',
                      bajada='Registrá lo que construyó tu equipo con un formulario y sumalo a la vitrina.',
                      url=f'github.com/{ORG}/proyectos'),
    'sitio': dict(cap=[('Página', 'rosa'), ('Catálogo y guías', 'gris')], titulo='La página',
                  bajada='Catálogo de workflows con filtros, guías, agenda, mentoría y aliados, todo junto.',
                  url=CONFIG['sitio_url'].replace('https://', '')),
}


def cabecera(repo, clase=''):
    t, f = TEXTOS[repo], FLUJOS[repo]
    heroe = next(n for n in f['nodos'].values() if n.get('heroe'))
    hx, hy = heroe['x'] + heroe['s'] / 2, heroe['y'] + heroe['s'] / 2
    cuerpo = [fondo(W, H, halos=[(hx + 60, hy, 520, 360, .26), (150, 40, 520, 260, .10)], encendido=(hx + 80, hy, 430, 300))]
    cuerpo.append(barra_superior(W))
    cuerpo.append(capsulas(t['cap'], extra=f'position:absolute;left:{M - 6}px;top:164px'))
    cuerpo.append(f'<div class="a t" data-k="t" data-n="titulo" style="left:{M - 6}px;top:206px;font-size:136px;font-weight:500;'
                  f'letter-spacing:-0.015em;line-height:1.12">{_html.escape(t["titulo"])}</div>')
    cuerpo.append(f'<div class="a" data-k="t" data-n="bajada" style="left:{M}px;top:372px;width:560px;font-size:29px;line-height:38px;'
                  f'color:#E0E0E0">{_html.escape(t["bajada"])}</div>')
    if repo == 'workflows':
        sup, w_sup = logo_tag('supabase', 27)
        cle, w_cle = logo_tag('clerk', 30)
        tea, w_tea = logo_tag('team1', 27)
        asp, w_asp = logo_tag('aspire', 21)            # en su placa clara: la placa entera pesa menos que n8n
        cuerpo.append(f'<div class="a t m" data-k="t" data-n="apoyo" style="left:{M}px;top:526px;font-size:14px;color:#BFBFBF;letter-spacing:.08em">'
                      f'Con el apoyo de</div>')
        cuerpo.append(f'<div class="a" style="left:{M}px;top:556px;height:34px;display:flex;align-items:center;gap:40px">{sup}{cle}{tea}{asp}</div>')
    else:
        cuerpo.append(f'<div class="a t" data-k="t" data-n="enfoque" style="left:{M}px;top:548px;font-size:22px;color:#D6D6D6">'
                      f'<span style="color:{ROSA}">Enfocada en mujeres</span>, de la mano de Women Techmakers Santa Cruz</div>')
    cuerpo.append(flujo(f['nodos'], f['conexiones'], W, H, f['chispas']))
    cuerpo.append(f'<div class="a t" data-k="t" data-n="url" style="right:{M}px;top:{586 if repo == "workflows" else 552}px;'
                  f'font-family:\'Geist Mono\',monospace;font-size:16px;color:#BFBFBF;letter-spacing:.01em">{_html.escape(t["url"])}</div>')
    return pagina(W, H, ''.join(cuerpo), clase)


# ---------------------------------------------------------------- el banner del perfil (1600 x 500)
BW, BH = 1600, 500


def banner(clase=''):
    # centros cada 174 px: el flujo respira parejo (disparador, nodo principal, rama doble y cierre)
    nodos = {
        'a': dict(x=842, y=168, s=88, icono='cursor', etq='Empezá acá', disparador=True),
        'b': dict(x=1008, y=160, s=104, icono='llaves', etq='Workflows', heroe=True),
        'c': dict(x=1190, y=64, s=88, icono='libro', etq='Guías'),
        'd': dict(x=1190, y=268, s=88, icono='grilla', etq='Proyectos'),
        'e': dict(x=1364, y=168, s=88, icono='globo', etq='Página', fin=True),
    }
    conex = [('a', 'b'), ('b', 'c'), ('b', 'd'), ('c', 'e'), ('d', 'e')]
    hx, hy = 1060, 212
    cuerpo = [fondo(BW, BH, halos=[(hx + 130, hy, 660, 330, .26), (240, 60, 640, 260, .10)], encendido=(hx + 150, hy, 540, 260))]
    n8n, n8n_w = logo_tag('n8n', 48)
    cuerpo.append(f'<div class="a" style="left:72px;top:52px">{n8n}</div>')
    cuerpo.append(f'<div class="a t m" data-k="t" data-n="presenta" style="left:{72 + n8n_w + 18:.1f}px;top:{52 + 48 - 19}px;font-size:15px;'
                  f'color:#BFBFBF;letter-spacing:.08em">Presenta</div>')
    nc, nc_w = logo_tag('nodo-cero', 148)
    cuerpo.append(f'<div class="a" style="left:72px;top:134px">{nc}</div>')
    cuerpo.append(f'<div class="a" data-k="t" data-n="lema" style="left:72px;top:306px;width:720px;font-size:31px;line-height:39px;color:#E6E6E6">'
                  f'La hackathon de la comunidad n8n en Bolivia,<br><span style="color:{ROSA};white-space:nowrap">enfocada en mujeres</span>.</div>')
    cuerpo.append(capsulas([('Sáb 21 nov 2026', 'rosa'), ('08:00–16:00', 'gris'), ('CEA · Santa Cruz', 'gris')],
                           extra='position:absolute;left:65px;top:408px', grande=True))
    wtm, wtm_w = logo_tag('wtm', 40)
    cuerpo.append(f'<div class="a" style="right:72px;top:424px;display:flex;align-items:center;gap:18px">'
                  f'<span class="t m" data-k="t" data-n="de-la-mano" style="font-size:15px;color:#BFBFBF;letter-spacing:.08em">De la mano de</span>{wtm}</div>')
    cuerpo.append(flujo(nodos, conex, BW, BH, chispas=[(1150, 46, 8), (968, 132, 6, ROSA20), (1500, 300, 7), (1330, 380, 6, ROSA20)]))
    return pagina(BW, BH, ''.join(cuerpo), clase)


# ---------------------------------------------------------------- auditoría
def lum(rgb):
    def c(v):
        v = v / 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return .2126 * c(r) + .7152 * c(g) + .0722 * c(b)


def contraste(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def color_css(s):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', s)
    return tuple(int(v) for v in m.groups()) if m else (250, 250, 250)


def solapan(a, b, tol=1):
    return not (a['x'] + a['w'] <= b['x'] + tol or b['x'] + b['w'] <= a['x'] + tol or a['y'] + a['h'] <= b['y'] + tol or b['y'] + b['h'] <= a['y'] + tol)


def auditar(nombre, html, w, h, destino, im_final):
    probs = []
    cajas = cajas_dom(html, w, h)
    seg = 24
    for c in cajas:
        if c['k'] in ('t', 'l') and (c['x'] < seg or c['y'] < seg or c['x'] + c['w'] > w - seg or c['y'] + c['h'] > h - seg):
            probs.append(f'{c["n"]} se sale de la zona segura ({c["x"]:.0f},{c["y"]:.0f},{c["w"]:.0f}x{c["h"]:.0f})')
        # horizontal: el texto no entra en su caja; vertical: más de 10 px (los ascendentes de una línea sola no cuentan)
        if c['k'] == 't' and (c['sw'] > c['cw'] + 1 or c['sh'] > c['ch'] + 10) and c['n'] not in ('capsulas',):
            probs.append(f'el texto {c["n"]} se corta ({c["sw"]}>{c["cw"]} o {c["sh"]}>{c["ch"]})')
    visibles = [c for c in cajas if c['k'] in ('t', 'l', 'g')]
    for i, a in enumerate(visibles):
        for b in visibles[i + 1:]:
            if solapan(a, b):
                probs.append(f'{a["n"]} pisa a {b["n"]}')
    # pesos: ningún aliado pesa más que n8n
    pn = next((c['peso'] for c in cajas if c['n'] == 'n8n'), None)
    altos = {c['n']: c['h'] for c in cajas if c['k'] == 'l'}
    for c in cajas:
        if c['k'] == 'l' and c['n'] in ALIADOS:
            if pn is None or c['peso'] >= pn:
                probs.append(f'el logo de {c["n"]} pesa más que n8n ({c["peso"]:.0f} >= {pn})')
            if c['h'] > altos.get('n8n', 0):
                probs.append(f'el logo de {c["n"]} es más alto que n8n')
    # contraste de cada texto contra lo que tiene detrás (render sin textos)
    sin = captura(html.replace('<body class="', '<body class="sin '), w, h, destino).convert('RGB').resize((w, h), Image.LANCZOS)
    for c in cajas:
        if c['k'] != 't' or c['n'] == 'capsulas':
            continue
        x0, y0 = max(0, int(c['x'])), max(0, int(c['y']))
        x1, y1 = min(w, int(c['x'] + c['w'])), min(h, int(c['y'] + c['h']))
        if x1 <= x0 or y1 <= y0:
            continue
        zona = sin.crop((x0, y0, x1, y1))
        datos = zona.get_flattened_data() if hasattr(zona, 'get_flattened_data') else zona.getdata()
        pix = sorted(datos, key=lum)
        fondo_claro = pix[int(len(pix) * .95) - 1]
        ct = contraste(color_css(c['color']), fondo_claro)
        minimo = 3.0 if c['fs'] >= 24 else 4.5
        if ct < minimo:
            probs.append(f'contraste bajo en {c["n"]}: {ct:.2f}:1 (mínimo {minimo})')
    # nodos: el borde llega a 3:1 contra el fondo (WCAG 1.4.11)
    for c in cajas:
        if c['k'] == 'g':
            x, y = int(c['x'] + c['w'] / 2), int(c['y'] + 1)
            borde = im_final.convert('RGB').getpixel((min(w - 1, x), min(h - 1, y)))
            afuera = sin.getpixel((min(w - 1, x), max(0, int(c['y']) - 6)))
            ct = contraste(borde, afuera)
            if ct < 3:
                probs.append(f'{c["n"]}: el borde contra el fondo da {ct:.2f}:1')
    peso = destino.stat().st_size
    if peso >= LIMITE_BYTES:
        probs.append(f'pesa {peso / 1e6:.2f} MB (límite 1 MB)')
    if im_final.size != (w, h):
        probs.append(f'mide {im_final.size}, no {w}x{h}')
    return probs


# ---------------------------------------------------------------- salida
def guardar(im, destino):
    """PNG optimizado; si pasa de 1 MB, paleta de 256 colores con difuminado (el degradado no se nota a esta escala)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    im = im.convert('RGB')
    im.save(destino, optimize=True)
    if destino.stat().st_size >= LIMITE_BYTES:
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(destino, optimize=True)
    return destino


def hacer(nombre, html_fn, w, h, destino):
    html = html_fn()
    grande = captura(html, w, h, destino)
    final = grande.resize((w, h), Image.LANCZOS)
    guardar(final, destino)
    probs = auditar(nombre, html_fn(), w, h, destino, Image.open(destino).convert('RGB'))
    estado = 'OK' if not probs else 'REVISAR'
    print(f'[{estado}] {nombre}: {destino.relative_to(GH)}  {final.size[0]}x{final.size[1]}  {destino.stat().st_size / 1024:.0f} KB')
    for p in probs:
        print('    -', p)
    return probs


def logos_en_placa(marca, alto=160):
    """Para una marca sin versión para fondo oscuro (Aspire Institute): compone su PNG oficial con Pillow, sin tocar sus colores.
    oscuro: el logo sobre la placa clara (#FAFAFA, esquinas redondeadas, con aire). claro: el mismo logo tal cual, con el mismo
    aire pero transparente, para que en los dos temas de GitHub el logo salga del mismo tamaño con el mismo `height`.
    `alto` es el alto total de la placa."""
    im = Image.open(LOGOS[marca]['png']).convert('RGBA')
    im = im.crop(im.split()[-1].point(lambda v: 255 if v > 6 else 0).getbbox())     # nada más el margen transparente
    tinta = round(alto / (1 + 2 * PLACA['v']))
    pv = (alto - tinta) // 2
    ancho_tinta = round(im.width * tinta / im.height)
    ph = round(tinta * PLACA['h'])
    logo = im.resize((ancho_tinta, tinta), Image.BOX)        # promedio de área con alfa premultiplicado: sin halos ni rojos nuevos
    w = ancho_tinta + 2 * ph
    # la placa, dibujada al cuádruple y bajada, para que las esquinas salgan suaves
    k = 4
    mascara = Image.new('L', (w * k, alto * k), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w * k - 1, alto * k - 1), radius=round(tinta * PLACA['r'] * k), fill=255)
    mascara = mascara.resize((w, alto), Image.LANCZOS)
    oscuro = Image.new('RGBA', (w, alto), PLACA['color'])
    oscuro.putalpha(mascara)
    oscuro.alpha_composite(logo, (ph, pv))
    claro = Image.new('RGBA', (w, alto), (0, 0, 0, 0))
    claro.alpha_composite(logo, (ph, pv))
    return {'oscuro': oscuro, 'claro': claro}


def logos_perfil():
    """Logos para la portada de la organización: una versión para el tema oscuro y otra para el claro, recortados a su tinta,
    a 4 veces el alto con el que se muestran (para pantallas de alta densidad). n8n va con su PNG oficial tal cual.
    Aspire Institute, que no tiene versión para fondo oscuro, va en su placa clara (ver logos_en_placa).
    Los mismos archivos se copian a guias/assets/aliados/, que los usa en su README."""
    dest = GH / 'org-perfil/profile/assets'
    dest.mkdir(parents=True, exist_ok=True)
    guias = GH / 'guias/assets/aliados'
    hechos = []
    for marca in ('n8n', 'supabase', 'clerk', 'team1', 'aspire', 'wtm', 'gobierno', 'nodo-cero'):
        placas = logos_en_placa(marca) if LOGOS[marca].get('placa') else None
        for fondo_ in ('oscuro', 'claro'):
            src = LOGOS[marca][fondo_]
            out = dest / f'{marca}-{fondo_}.png'
            if marca == 'n8n':
                shutil.copyfile(src, out)            # el PNG oficial (480 x 96), sin tocar
            elif placas:
                placas[fondo_].save(out, optimize=True)
            else:
                im = rasterizar(src, alto=480)
                alto = 240 if marca == 'nodo-cero' else 160
                if im.height > alto:
                    im = im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)
                im.save(out, optimize=True)
            hechos.append(out)
            if marca != 'nodo-cero' and guias.is_dir():
                shutil.copyfile(out, guias / out.name)
    for p in hechos:
        im = Image.open(p)
        print(f'[OK] logo {p.relative_to(GH)}  {im.width}x{im.height}  {p.stat().st_size / 1024:.0f} KB')
    if guias.is_dir():
        print(f'     (copiados también a {guias.relative_to(GH)}/, salvo Nodo Cero)')
    return []


PIEZAS = {
    'workflows': (lambda: cabecera('workflows'), W, H, GH / 'workflows/assets/cabecera.png'),
    'guias': (lambda: cabecera('guias'), W, H, GH / 'guias/assets/cabecera.png'),
    'proyectos': (lambda: cabecera('proyectos'), W, H, GH / 'proyectos/assets/cabecera.png'),
    'sitio': (lambda: cabecera('sitio'), W, H, GH / 'sitio/assets/cabecera.png'),
    'banner': (banner, BW, BH, GH / 'org-perfil/profile/banner.png'),
}


def main(ids):
    if not CHROME.exists():
        sys.exit(f'No encuentro el Chrome sin interfaz en {CHROME}')
    ids = ids or [*PIEZAS, 'logos']
    probs = []
    for i in ids:
        if i == 'logos':
            probs += logos_perfil()
        elif i in PIEZAS:
            fn, w, h, destino = PIEZAS[i]
            probs += hacer(i, fn, w, h, destino)
        else:
            sys.exit(f'Pieza desconocida: {i}. Opciones: {", ".join([*PIEZAS, "logos"])}')
    print('\nTodo en orden.' if not probs else f'\n{len(probs)} cosas para revisar.')
    return 1 if probs else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
