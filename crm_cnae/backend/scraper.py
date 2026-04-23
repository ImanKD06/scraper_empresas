"""
Scraper El Economista — Anti-429
Estrategias:
  · Rotación de 12 User-Agents reales
  · Warm-up visitando homepage primero
  · Delay aleatorio 5-10s entre páginas
  · Retry exponencial en 429/503: 30s → 60s → 120s
  · Sesión persistente con cookies
"""
import asyncio, random, re
import httpx
from bs4 import BeautifulSoup
import db

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

PROVINCIAS = {
    "Álava":"01","Albacete":"02","Alicante":"03","Almería":"04","Asturias":"33",
    "Ávila":"05","Badajoz":"06","Baleares":"07","Barcelona":"08","Burgos":"09",
    "Cáceres":"10","Cádiz":"11","Cantabria":"39","Castellón":"12","Ciudad Real":"13",
    "Córdoba":"14","Cuenca":"16","Girona":"17","Granada":"18","Guadalajara":"19",
    "Gipuzkoa":"20","Huelva":"21","Huesca":"22","Jaén":"23","La Coruña":"15",
    "La Rioja":"26","Las Palmas":"35","León":"24","Lleida":"25","Lugo":"27",
    "Madrid":"28","Málaga":"29","Murcia":"30","Navarra":"31","Ourense":"32",
    "Palencia":"34","Pontevedra":"36","Salamanca":"37","Segovia":"40","Sevilla":"41",
    "Soria":"42","Tarragona":"43","Tenerife":"38","Teruel":"44","Toledo":"45",
    "Valencia":"46","Valladolid":"47","Vizcaya":"48","Zamora":"49","Zaragoza":"50",
}

BASE = "https://ranking-empresas.eleconomista.es"
URL  = BASE + "/ranking_empresas_nacional.html"


def _hdrs():
    return {
        "User-Agent": random.choice(UAS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": random.choice(["https://www.google.es/", "https://www.bing.com/",
                                   "https://ranking-empresas.eleconomista.es/"]),
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


async def _fetch(client, params):
    """Fetch con retry anti-429."""
    for intento in range(4):
        try:
            r = await client.get(URL, params=params, headers=_hdrs(), timeout=30)
            if r.status_code == 200:
                return r.text
            elif r.status_code == 429:
                wait = 30 * (2 ** intento) + random.uniform(15, 30)
                print(f"  [429 Rate Limit] Esperando {wait:.0f}s (intento {intento+1}/4)")
                await asyncio.sleep(wait)
            elif r.status_code == 503:
                print(f"  [503] Esperando 25s...")
                await asyncio.sleep(25 + random.uniform(5, 10))
            elif r.status_code in (403, 406):
                print(f"  [{r.status_code}] Posible bloqueo. Esperando 60s...")
                await asyncio.sleep(60 + random.uniform(10, 30))
            else:
                print(f"  [HTTP {r.status_code}] Sin datos en esta página.")
                return None
        except Exception as e:
            print(f"  [Error red] {e}. Reintento {intento+1}/4")
            await asyncio.sleep(12)
    return None


def _parse(html, cnae, provincia):
    soup = BeautifulSoup(html, "lxml")
    resultados = []

    # Buscar tablas con datos empresariales
    for table in soup.find_all("table"):
        rows = table.find_all("tr")[1:]
        if len(rows) < 2:
            continue
        parsed = []
        for row in rows:
            celdas = row.find_all(["td", "th"])
            if len(celdas) < 2:
                continue
            textos = [c.get_text(separator=" ", strip=True) for c in celdas]
            full = " ".join(textos)

            # Nombre empresa
            nombre = None
            for t in textos:
                t2 = re.sub(r"^\d+\.?\s*", "", t).strip()
                if (len(t2) > 5
                        and not re.match(r"^[\d.,€%\s\-/]+$", t2)
                        and len(t2) < 200):
                    nombre = t2
                    break
            if not nombre:
                continue

            # Ranking
            ranking = None
            m = re.match(r"^(\d{1,4})\.?\s*$", textos[0].strip())
            if m:
                ranking = int(m.group(1))

            # CIF
            cif = ""
            cm = re.search(r"\b([A-Z]\d{7}[0-9A-J])\b", full)
            if cm:
                cif = cm.group(1)

            # Facturaciones
            facs = []
            for t in textos:
                if re.search(r"\d{3,}", t) and not re.match(r"^\d{1,2}\.?\s*$", t.strip()):
                    nums = re.sub(r"[^\d.,]", "", t)
                    if nums and len(nums) > 2:
                        facs.append(t.strip()[:40])
            fac_act = facs[0] if facs else ""
            fac_ant = facs[1] if len(facs) > 1 else ""

            # Tendencia
            tend, pct = _tend(fac_act, fac_ant)

            # URL detalle empresa
            url_emp = ""
            for c in celdas:
                a = c.find("a", href=True)
                if a:
                    h = a["href"]
                    url_emp = (BASE + h) if h.startswith("/") else h
                    break

            parsed.append({
                "nombre": nombre[:250],
                "cif": cif,
                "ranking_posicion": ranking,
                "cnae": cnae,
                "provincia": provincia,
                "facturacion_actual": fac_act,
                "facturacion_anterior": fac_ant,
                "tendencia": tend,
                "pct_cambio": pct,
                "url_economista": url_emp[:400],
            })

        if len(parsed) >= 3:
            resultados.extend(parsed)
            break  # Tabla principal encontrada

    return resultados


def _tend(a, b):
    if not a or not b:
        return "sin datos", "N/A"
    try:
        def p(s):
            s = re.sub(r"[^\d,.]", "", s).replace(",", ".")
            pts = s.split(".")
            if len(pts) > 2:
                s = "".join(pts[:-1]) + "." + pts[-1]
            return float(s) if s else 0
        va, vb = p(a), p(b)
        if va == 0 or vb == 0:
            return "sin datos", "N/A"
        pct = (va - vb) / vb * 100
        if pct > 3:   return "crecimiento",  f"+{pct:.1f}%"
        if pct < -3:  return "decrecimiento", f"{pct:.1f}%"
        return "estable", f"{pct:.1f}%"
    except:
        return "sin datos", "N/A"


def _set_prog(aid, pct, msg, estado="scrapeando"):
    db.run("UPDATE asignaciones SET progreso=%s, mensaje=%s, estado=%s WHERE id=%s",
           (pct, msg, estado, aid))


async def scrape_y_guardar(asignacion_id: int):
    row = db.one("SELECT * FROM asignaciones WHERE id=%s", (asignacion_id,))
    if not row:
        return

    cnae     = row["cnae"]
    prov     = row["provincia"]
    paginas  = row["paginas"]
    prov_cod = PROVINCIAS.get(prov, "")

    _set_prog(asignacion_id, 3, "Iniciando scraper...")
    print(f"\n[Scraper] Asignacion {asignacion_id}: CNAE={cnae} Prov={prov} Pags={paginas}")

    todas = []

    async with httpx.AsyncClient(follow_redirects=True,
                                 limits=httpx.Limits(max_connections=1)) as client:
        # Warm-up: visitar home para obtener cookies reales
        try:
            print("  [Warm-up] Visitando homepage...")
            await client.get(BASE + "/", headers=_hdrs(), timeout=15)
            await asyncio.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"  [Warm-up] {e}")

        for pag in range(1, paginas + 1):
            pct = int((pag - 1) / paginas * 85) + 5
            _set_prog(asignacion_id, pct, f"Scrapeando página {pag}/{paginas}...")
            print(f"  [Pág {pag}/{paginas}] Fetching...")

            params = {"qSectorNorm": cnae, "pagina": pag}
            if prov_cod:
                params["qProvincia"] = prov_cod

            html = await _fetch(client, params)
            if html:
                batch = _parse(html, cnae, prov)
                todas.extend(batch)
                print(f"  [Pág {pag}] {len(batch)} empresas encontradas")
            else:
                print(f"  [Pág {pag}] Sin resultado, continuando...")

            # Pausa CRÍTICA anti-429 entre páginas
            if pag < paginas:
                espera = random.uniform(6, 11)
                print(f"  [Pausa] {espera:.1f}s antes de la siguiente página...")
                await asyncio.sleep(espera)

    _set_prog(asignacion_id, 90, f"Guardando {len(todas)} empresas en MySQL...")

    # Deduplicar por nombre normalizado
    vistas = set()
    nuevas = 0
    for e in todas:
        key = e["nombre"].lower().strip()[:35]
        if key in vistas:
            continue
        vistas.add(key)

        ya = db.one(
            "SELECT id FROM empresas WHERE nombre=%s AND cnae=%s AND provincia=%s",
            (e["nombre"], cnae, prov)
        )
        if not ya:
            db.run("""
                INSERT INTO empresas
                  (nombre, cif, ranking_posicion, cnae, provincia,
                   facturacion_actual, facturacion_anterior,
                   tendencia, pct_cambio, url_economista, asignacion_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (e["nombre"], e["cif"], e["ranking_posicion"], cnae, prov,
                  e["facturacion_actual"], e["facturacion_anterior"],
                  e["tendencia"], e["pct_cambio"], e["url_economista"], asignacion_id))
            nuevas += 1

    total = db.one(
        "SELECT COUNT(*) AS n FROM empresas WHERE asignacion_id=%s", (asignacion_id,)
    )["n"]

    db.run("""UPDATE asignaciones
              SET estado='completada', progreso=100, total_empresas=%s,
                  mensaje=%s WHERE id=%s""",
           (total, f"Completado: {total} empresas guardadas", asignacion_id))
    print(f"[Scraper] Terminado: {total} empresas en BD\n")