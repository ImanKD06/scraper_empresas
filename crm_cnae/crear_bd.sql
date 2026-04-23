-- ═══════════════════════════════════════════════════════
--  CRM CNAE - Script MySQL completo
--  Se ejecuta automaticamente desde setup.bat
--  O manualmente: mysql -u root -p < crear_bd.sql
-- ═══════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS crm_cnae
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE crm_cnae;

-- ── USUARIOS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  nombre     VARCHAR(100) NOT NULL,
  apellidos  VARCHAR(100) DEFAULT '',
  email      VARCHAR(150) NOT NULL UNIQUE,
  password   VARCHAR(255) NOT NULL,
  rol        ENUM('admin','supervisor','comercial') NOT NULL DEFAULT 'comercial',
  activo     TINYINT(1) NOT NULL DEFAULT 1,
  creado_en  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── ASIGNACIONES (tareas de scraping) ────────────────────
CREATE TABLE IF NOT EXISTS asignaciones (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  nombre         VARCHAR(200) NOT NULL,
  cnae           VARCHAR(10)  NOT NULL,
  cnae_desc      VARCHAR(200) DEFAULT '',
  provincia      VARCHAR(100) NOT NULL,
  paginas        INT NOT NULL DEFAULT 1,
  estado         ENUM('pendiente','scrapeando','completada','error') DEFAULT 'pendiente',
  progreso       INT DEFAULT 0,
  mensaje        TEXT,
  total_empresas INT DEFAULT 0,
  comercial_id   INT DEFAULT NULL,
  creado_por     INT NOT NULL,
  creado_en      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_comercial (comercial_id),
  FOREIGN KEY (comercial_id) REFERENCES usuarios(id) ON DELETE SET NULL,
  FOREIGN KEY (creado_por)   REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── EMPRESAS (datos scrapeados de El Economista) ──────────
CREATE TABLE IF NOT EXISTS empresas (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  nombre               VARCHAR(300) NOT NULL,
  cif                  VARCHAR(20)  DEFAULT '',
  ranking_posicion     INT DEFAULT NULL,
  cnae                 VARCHAR(10)  DEFAULT '',
  provincia            VARCHAR(100) DEFAULT '',
  municipio            VARCHAR(100) DEFAULT '',
  direccion            VARCHAR(300) DEFAULT '',
  web                  VARCHAR(300) DEFAULT '',
  telefono             VARCHAR(50)  DEFAULT '',
  email                VARCHAR(150) DEFAULT '',
  gerente              VARCHAR(200) DEFAULT '',
  cargo_gerente        VARCHAR(150) DEFAULT '',
  empleados            VARCHAR(50)  DEFAULT '',
  facturacion_actual   VARCHAR(50)  DEFAULT '',
  facturacion_anterior VARCHAR(50)  DEFAULT '',
  tendencia            VARCHAR(20)  DEFAULT '',
  pct_cambio           VARCHAR(20)  DEFAULT '',
  licita               TINYINT(1)   DEFAULT 0,
  url_economista       VARCHAR(500) DEFAULT '',
  asignacion_id        INT DEFAULT NULL,
  creado_en            DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cnae       (cnae),
  INDEX idx_provincia  (provincia),
  INDEX idx_asignacion (asignacion_id),
  FOREIGN KEY (asignacion_id) REFERENCES asignaciones(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── LEADS (gestión comercial) ─────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id        INT NOT NULL,
  comercial_id      INT NOT NULL,
  estado            ENUM('nuevo','contactado','interesado','negociacion','cliente','descartado') DEFAULT 'nuevo',
  interes           INT DEFAULT 0,
  nombre_contacto   VARCHAR(200) DEFAULT '',
  cargo_contacto    VARCHAR(150) DEFAULT '',
  telefono_contacto VARCHAR(50)  DEFAULT '',
  email_contacto    VARCHAR(150) DEFAULT '',
  notas             TEXT,
  proxima_accion    VARCHAR(300) DEFAULT '',
  es_cliente        TINYINT(1)   DEFAULT 0,
  creado_en         DATETIME DEFAULT CURRENT_TIMESTAMP,
  actualizado_en    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY un_lead (empresa_id, comercial_id),
  INDEX idx_estado     (estado),
  INDEX idx_comercial  (comercial_id),
  FOREIGN KEY (empresa_id)   REFERENCES empresas(id) ON DELETE CASCADE,
  FOREIGN KEY (comercial_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── ACTIVIDADES (historial de contacto) ──────────────────
CREATE TABLE IF NOT EXISTS actividades (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  lead_id     INT NOT NULL,
  tipo        ENUM('llamada','email','reunion','nota') NOT NULL DEFAULT 'nota',
  descripcion TEXT,
  resultado   VARCHAR(300) DEFAULT '',
  creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead (lead_id),
  FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── USUARIO ADMIN POR DEFECTO ─────────────────────────────
-- Contrasena: admin123
INSERT IGNORE INTO usuarios (nombre, apellidos, email, password, rol)
VALUES (
  'Administrador', 'Sistema', 'admin@crm.es',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJbekRSm5pMNhGDBR6GlkxJG',
  'admin'
);

SELECT '✓ Base de datos crm_cnae creada correctamente' AS resultado;
SELECT '✓ Login: admin@crm.es / admin123' AS credenciales;