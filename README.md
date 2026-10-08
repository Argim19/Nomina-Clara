# Nómina Clara

MVP profesional para administrar empleados, calcular nómina y conservar un histórico inmutable de liquidaciones. La interfaz está construida con Vite + React y la API con Python + SQLite.

## Requisitos

- Node.js 20 o superior
- Python 3.10 o superior

## Ejecución local

Abra dos terminales en la carpeta del proyecto.

**Terminal 1 — API**

```bash
python3 -m backend.app
```

La API quedará disponible en `http://localhost:8000` y creará automáticamente la base de datos local.

**Terminal 2 — Interfaz**

```bash
npm install
npm run dev
```

Abra `http://localhost:5173` e ingrese con:

- Correo: `admin@nominaclara.co`
- Contraseña: `Nomina2026!`

La instalación incluye datos demostrativos para facilitar la evaluación. Para iniciar sin ellos:

```bash
NOMINA_SEED_DEMO=false python3 -m backend.app
```

## Pruebas

```bash
npm test
python3 -m unittest backend.test_app
npm run build
```

## Configuración

La API admite estas variables de entorno:

| Variable | Uso |
|---|---|
| `NOMINA_ADMIN_EMAIL` | Correo de acceso administrativo |
| `NOMINA_ADMIN_PASSWORD` | Contraseña de acceso |
| `NOMINA_TOKEN_SECRET` | Firma de sesiones; debe definirse en producción |
| `NOMINA_DB_PATH` | Ruta de la base SQLite |
| `NOMINA_ALLOWED_ORIGIN` | Origen permitido para el frontend |
| `NOMINA_SEED_DEMO` | Carga inicial de empleados (incluyendo equipo) |
| `RESEND_API_KEY` | Clave API de Resend para envíos transaccionales |
| `RESEND_FROM` | Remitente en Resend (por defecto `Nómina Clara <onboarding@resend.dev>`) |
| `NOMINA_SMTP_USER` | Correo remitente para envío SMTP (ej. cuenta de Gmail) |
| `NOMINA_SMTP_PASSWORD` | Contraseña de aplicación para SMTP |
| `NOMINA_SMTP_HOST` | Servidor SMTP (por defecto `smtp.gmail.com`) |
| `NOMINA_SMTP_PORT` | Puerto SMTP (por defecto `587`) |

Para un despliegue productivo se recomienda reemplazar el usuario único por gestión de cuentas, servir bajo HTTPS, conectar un proveedor SMTP y desplegar la API detrás de un servidor WSGI/ASGI.

## Alcance funcional

- Inicio de sesión administrativo con sesión firmada.
- Registro, consulta y edición de empleados; desactivación sin borrar histórico.
- Cálculo por empleado y periodo con horas trabajadas.
- Bonificación automática por hijos: 1 = $250.000, 2 = $400.000, 3 o más = $600.000.
- EPS, pensión, ARL y otros conceptos parametrizables por liquidación.
- Histórico inmutable con copia de los datos laborales usados en el cálculo.
- Volante de pago imprimible o exportable a PDF desde el navegador.
- Punto de integración preparado para correo electrónico.

