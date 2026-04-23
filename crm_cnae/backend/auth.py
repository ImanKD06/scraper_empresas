from datetime import datetime, timedelta
from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import config, db

bearer = HTTPBearer()

def hash_pw(plain):
    return bcrypt.hashpw(plain[:72].encode(), bcrypt.gensalt()).decode()

def check_pw(plain, hashed):
    try:
        return bcrypt.checkpw(plain[:72].encode(), hashed.encode())
    except Exception:
        return False

def make_token(uid, rol):
    exp = datetime.utcnow() + timedelta(hours=config.TOKEN_HORAS)
    return jwt.encode({"sub": str(uid), "rol": rol, "exp": exp},
                      config.SECRET_KEY, algorithm=config.ALGORITHM)

def get_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        pl = jwt.decode(creds.credentials, config.SECRET_KEY,
                        algorithms=[config.ALGORITHM])
        uid = int(pl["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Token inválido o expirado")
    u = db.one("SELECT id,nombre,apellidos,email,rol FROM usuarios WHERE id=%s AND activo=1", (uid,))
    if not u:
        raise HTTPException(401, "Usuario no encontrado")
    return u

def need(*roles):
    def check(u=Depends(get_user)):
        if u["rol"] not in roles:
            raise HTTPException(403, "Sin permisos")
        return u
    return check