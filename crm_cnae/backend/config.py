# ══════════════════════════════════════════════
#  CONFIGURACIÓN - edita solo DB_PASSWORD
# ══════════════════════════════════════════════

DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "1307065"      # ← PON TU CONTRASEÑA MYSQL AQUÍ
DB_NAME     = "crm_cnae"

SECRET_KEY  = "crm_cnae_2025_clave_secreta"
ALGORITHM   = "HS256"
TOKEN_HORAS = 8

# Ruta donde se guardan los Excel exportados (Windows)
EXCEL_DIR   = "C:\\crm_exports"