"""CRM CNAE - Backend completo en un archivo."""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import auth, db, scraper, excel

app = FastAPI(title="CRM CNAE", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Servir frontend si existe
FE = Path(__file__).parent.parent / "frontend"
if FE.exists():
    app.mount("/ui", StaticFiles(directory=str(FE), html=True), name="ui")


# ── Schemas ────────────────────────────────────────────────
class Login(BaseModel):
    email: str; password: str

class NuevoUsuario(BaseModel):
    nombre: str; apellidos: Optional[str] = ""
    email: str; password: str; rol: str = "comercial"

class EditUsuario(BaseModel):
    nombre: Optional[str] = None; apellidos: Optional[str] = None
    email: Optional[str] = None; password: Optional[str] = None
    rol: Optional[str] = None; activo: Optional[int] = None

class NuevaAsig(BaseModel):
    nombre: str; cnae: str; cnae_desc: Optional[str] = ""
    provincia: str; paginas: int = 1; comercial_id: Optional[int] = None

class EditLead(BaseModel):
    estado: Optional[str] = None; interes: Optional[int] = None
    nombre_contacto: Optional[str] = None; cargo_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None; email_contacto: Optional[str] = None
    notas: Optional[str] = None; proxima_accion: Optional[str] = None

class NuevaActividad(BaseModel):
    tipo: str; descripcion: Optional[str] = ""; resultado: Optional[str] = ""

class EditEmpresa(BaseModel):
    telefono: Optional[str] = None; email: Optional[str] = None
    gerente: Optional[str] = None; cargo_gerente: Optional[str] = None
    municipio: Optional[str] = None; direccion: Optional[str] = None
    empleados: Optional[str] = None; licita: Optional[int] = None


# ── AUTH ───────────────────────────────────────────────────
@app.post("/api/login")
def login(d: Login):
    u = db.one("SELECT * FROM usuarios WHERE email=%s AND activo=1", (d.email,))
    if not u or not auth.check_pw(d.password, u["password"]):
        raise HTTPException(400, "Email o contraseña incorrectos")
    return {
        "token": auth.make_token(u["id"], u["rol"]),
        "user": {"id":u["id"],"nombre":u["nombre"],"apellidos":u["apellidos"],
                 "email":u["email"],"rol":u["rol"]}
    }

@app.get("/api/yo")
def yo(u=Depends(auth.get_user)):
    return u


# ── USUARIOS ───────────────────────────────────────────────
@app.get("/api/usuarios")
def listar_usuarios(u=Depends(auth.need("admin","supervisor"))):
    return db.query("SELECT id,nombre,apellidos,email,rol,activo,creado_en FROM usuarios ORDER BY id")

@app.post("/api/usuarios")
def crear_usuario(d: NuevoUsuario, u=Depends(auth.need("admin"))):
    if d.rol not in ("admin","supervisor","comercial"):
        raise HTTPException(400, "Rol inválido")
    if db.one("SELECT id FROM usuarios WHERE email=%s", (d.email,)):
        raise HTTPException(400, "Email ya existe")
    uid = db.run(
        "INSERT INTO usuarios (nombre,apellidos,email,password,rol) VALUES (%s,%s,%s,%s,%s)",
        (d.nombre, d.apellidos or "", d.email, auth.hash_pw(d.password), d.rol)
    )
    return {"id": uid, "ok": True}

@app.put("/api/usuarios/{uid}")
def editar_usuario(uid: int, d: EditUsuario, u=Depends(auth.need("admin"))):
    sets, vals = [], []
    if d.nombre    is not None: sets.append("nombre=%s");    vals.append(d.nombre)
    if d.apellidos is not None: sets.append("apellidos=%s"); vals.append(d.apellidos)
    if d.email     is not None: sets.append("email=%s");     vals.append(d.email)
    if d.password  is not None: sets.append("password=%s");  vals.append(auth.hash_pw(d.password))
    if d.rol       is not None: sets.append("rol=%s");       vals.append(d.rol)
    if d.activo    is not None: sets.append("activo=%s");    vals.append(d.activo)
    if not sets: return {"ok": True}
    vals.append(uid)
    db.run(f"UPDATE usuarios SET {','.join(sets)} WHERE id=%s", vals)
    return {"ok": True}

@app.delete("/api/usuarios/{uid}")
def borrar_usuario(uid: int, u=Depends(auth.need("admin"))):
    db.run("UPDATE usuarios SET activo=0 WHERE id=%s", (uid,))
    return {"ok": True}


# ── ASIGNACIONES ───────────────────────────────────────────
@app.get("/api/asignaciones")
def listar_asig(u=Depends(auth.get_user)):
    if u["rol"] == "comercial":
        return db.query("""
            SELECT a.*, us.nombre AS com_nombre
            FROM asignaciones a LEFT JOIN usuarios us ON a.comercial_id=us.id
            WHERE a.comercial_id=%s ORDER BY a.id DESC
        """, (u["id"],))
    return db.query("""
        SELECT a.*, us.nombre AS com_nombre
        FROM asignaciones a LEFT JOIN usuarios us ON a.comercial_id=us.id
        ORDER BY a.id DESC
    """)

@app.get("/api/asignaciones/{aid}")
def get_asig(aid: int, u=Depends(auth.get_user)):
    r = db.one("SELECT * FROM asignaciones WHERE id=%s", (aid,))
    if not r: raise HTTPException(404, "No encontrada")
    return r

@app.post("/api/asignaciones")
def crear_asig(d: NuevaAsig, bt: BackgroundTasks, u=Depends(auth.need("admin","supervisor"))):
    if not 1 <= d.paginas <= 20:
        raise HTTPException(400, "Páginas entre 1 y 20")
    aid = db.run("""
        INSERT INTO asignaciones (nombre,cnae,cnae_desc,provincia,paginas,comercial_id,creado_por)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (d.nombre, d.cnae, d.cnae_desc or "", d.provincia,
          d.paginas, d.comercial_id, u["id"]))
    bt.add_task(scraper.scrape_y_guardar, aid)
    return {"id": aid, "ok": True}

@app.get("/api/asignaciones/{aid}/excel")
def descargar_excel(aid: int, u=Depends(auth.get_user)):
    asig = db.one("SELECT estado FROM asignaciones WHERE id=%s", (aid,))
    if not asig: raise HTTPException(404, "No encontrada")
    fpath = excel.exportar(aid)
    import os
    return FileResponse(fpath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(fpath))


# ── EMPRESAS ───────────────────────────────────────────────
@app.get("/api/empresas")
def listar_empresas(
    asignacion_id: Optional[int] = None,
    provincia: Optional[str] = None,
    tendencia: Optional[str] = None,
    page: int = 1, per_page: int = 50,
    u=Depends(auth.get_user)
):
    w, v = ["1=1"], []
    if u["rol"] == "comercial":
        w.append("e.asignacion_id IN (SELECT id FROM asignaciones WHERE comercial_id=%s)")
        v.append(u["id"])
    if asignacion_id: w.append("e.asignacion_id=%s"); v.append(asignacion_id)
    if provincia:     w.append("e.provincia=%s");      v.append(provincia)
    if tendencia:     w.append("e.tendencia=%s");      v.append(tendencia)
    wh = " AND ".join(w)
    total = db.one(f"SELECT COUNT(*) AS n FROM empresas e WHERE {wh}", v)["n"]
    ofs   = (page-1)*per_page
    items = db.query(f"""
        SELECT e.*,
          (SELECT COUNT(*) FROM leads l WHERE l.empresa_id=e.id) AS tiene_lead
        FROM empresas e WHERE {wh}
        ORDER BY e.ranking_posicion, e.id LIMIT %s OFFSET %s
    """, v+[per_page, ofs])
    return {"total": total, "page": page, "items": items}

@app.put("/api/empresas/{eid}")
def editar_empresa(eid: int, d: EditEmpresa, u=Depends(auth.get_user)):
    sets, vals = [], []
    for col in ("telefono","email","gerente","cargo_gerente","municipio","direccion","empleados","licita"):
        val = getattr(d, col)
        if val is not None: sets.append(f"{col}=%s"); vals.append(val)
    if not sets: return {"ok": True}
    vals.append(eid)
    db.run(f"UPDATE empresas SET {','.join(sets)} WHERE id=%s", vals)
    return {"ok": True}


# ── LEADS ──────────────────────────────────────────────────
@app.get("/api/leads")
def listar_leads(estado: Optional[str]=None, comercial_id: Optional[int]=None,
                 asignacion_id: Optional[int]=None, u=Depends(auth.get_user)):
    w, v = ["1=1"], []
    if u["rol"] == "comercial":
        w.append("l.comercial_id=%s"); v.append(u["id"])
    elif comercial_id:
        w.append("l.comercial_id=%s"); v.append(comercial_id)
    if estado:        w.append("l.estado=%s");          v.append(estado)
    if asignacion_id: w.append("e.asignacion_id=%s");   v.append(asignacion_id)
    wh = " AND ".join(w)
    return db.query(f"""
        SELECT l.*, e.nombre AS emp_nom, e.cif, e.provincia, e.municipio,
               e.telefono AS emp_tel, e.email AS emp_email, e.ranking_posicion,
               e.cnae, e.facturacion_actual, e.tendencia, e.pct_cambio,
               e.licita, e.gerente, e.cargo_gerente, e.asignacion_id,
               u.nombre AS com_nom, u.apellidos AS com_ap
        FROM leads l
        JOIN empresas e ON l.empresa_id=e.id
        JOIN usuarios u ON l.comercial_id=u.id
        WHERE {wh} ORDER BY l.actualizado_en DESC LIMIT 500
    """, v)

@app.post("/api/leads")
def crear_lead(empresa_id: int, u=Depends(auth.get_user)):
    ya = db.one("SELECT id FROM leads WHERE empresa_id=%s AND comercial_id=%s",
                (empresa_id, u["id"]))
    if ya:
        return db.one("""
            SELECT l.*, e.nombre AS emp_nom, e.cif, e.provincia, e.municipio,
                   e.telefono AS emp_tel, e.email AS emp_email, e.ranking_posicion,
                   e.cnae, e.facturacion_actual, e.tendencia, e.pct_cambio,
                   e.licita, e.gerente, e.cargo_gerente,
                   u.nombre AS com_nom, u.apellidos AS com_ap
            FROM leads l
            JOIN empresas e ON l.empresa_id=e.id
            JOIN usuarios u ON l.comercial_id=u.id
            WHERE l.id=%s
        """, (ya["id"],))
    lid = db.run("INSERT INTO leads (empresa_id,comercial_id) VALUES (%s,%s)",
                 (empresa_id, u["id"]))
    return db.one("""
        SELECT l.*, e.nombre AS emp_nom, e.cif, e.provincia, e.municipio,
               e.telefono AS emp_tel, e.email AS emp_email, e.ranking_posicion,
               e.cnae, e.facturacion_actual, e.tendencia, e.pct_cambio,
               e.licita, e.gerente, e.cargo_gerente,
               u.nombre AS com_nom, u.apellidos AS com_ap
        FROM leads l
        JOIN empresas e ON l.empresa_id=e.id
        JOIN usuarios u ON l.comercial_id=u.id
        WHERE l.id=%s
    """, (lid,))

@app.put("/api/leads/{lid}")
def editar_lead(lid: int, d: EditLead, u=Depends(auth.get_user)):
    lead = db.one("SELECT * FROM leads WHERE id=%s", (lid,))
    if not lead: raise HTTPException(404, "Lead no encontrado")
    if u["rol"] == "comercial" and lead["comercial_id"] != u["id"]:
        raise HTTPException(403, "Sin permisos")
    sets, vals = [], []
    for col in ("estado","interes","nombre_contacto","cargo_contacto",
                "telefono_contacto","email_contacto","notas","proxima_accion"):
        val = getattr(d, col)
        if val is not None: sets.append(f"{col}=%s"); vals.append(val)
    if d.estado == "cliente": sets.append("es_cliente=1")
    if not sets: return {"ok": True}
    vals.append(lid)
    db.run(f"UPDATE leads SET {','.join(sets)} WHERE id=%s", vals)
    return {"ok": True}


# ── ACTIVIDADES ────────────────────────────────────────────
@app.get("/api/leads/{lid}/actividades")
def listar_acts(lid: int, u=Depends(auth.get_user)):
    return db.query("SELECT * FROM actividades WHERE lead_id=%s ORDER BY creado_en DESC", (lid,))

@app.post("/api/leads/{lid}/actividades")
def crear_act(lid: int, d: NuevaActividad, u=Depends(auth.get_user)):
    aid = db.run(
        "INSERT INTO actividades (lead_id,tipo,descripcion,resultado) VALUES (%s,%s,%s,%s)",
        (lid, d.tipo, d.descripcion or "", d.resultado or "")
    )
    return {"id": aid, "ok": True}


# ── STATS ──────────────────────────────────────────────────
@app.get("/api/stats")
def stats(u=Depends(auth.need("admin","supervisor"))):
    total_e  = db.one("SELECT COUNT(*) AS n FROM empresas")["n"]
    total_l  = db.one("SELECT COUNT(*) AS n FROM leads")["n"]
    total_cl = db.one("SELECT COUNT(*) AS n FROM leads WHERE estado='cliente'")["n"]
    total_ng = db.one("SELECT COUNT(*) AS n FROM leads WHERE estado='negociacion'")["n"]
    coms = db.query("SELECT id,nombre,apellidos FROM usuarios WHERE rol='comercial' AND activo=1")
    resultado = []
    for c in coms:
        tot = db.one("SELECT COUNT(*) AS n FROM leads WHERE comercial_id=%s", (c["id"],))["n"]
        ests = {}
        for e in ("nuevo","contactado","interesado","negociacion","cliente","descartado"):
            ests[e] = db.one(
                "SELECT COUNT(*) AS n FROM leads WHERE comercial_id=%s AND estado=%s",
                (c["id"], e)
            )["n"]
        resultado.append({"comercial": c, "total": tot, "estados": ests})
    return {
        "total_empresas": total_e, "total_leads": total_l,
        "total_clientes": total_cl, "total_negociacion": total_ng,
        "comerciales": resultado,
    }


# ── ARRANQUE ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "═"*48)
    print("  CRM CNAE · Servidor arrancado")
    print("  URL:     http://localhost:8000")
    print("  Docs:    http://localhost:8000/docs")
    print("  Login:   admin@crm.es / admin123")
    print("═"*48 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)