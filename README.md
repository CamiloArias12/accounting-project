# accounting-project

Plataforma contable colombiana: plan de cuentas (PUC), comprobantes de partida
doble, libro mayor, cierre de períodos e información exógena. Monorepo
FastAPI + Next.js; todo corre en Docker.

**Demo:** <http://46.224.38.172:3001> — `demo@accounting-project.dev` /
`demo-accounting-2026`, con el PUC completo cargado (2.446 cuentas).

| Servicio | Stack                                | Puerto             |
| -------- | ------------------------------------ | ------------------ |
| `web`    | Next.js 16, React 19, Tailwind 4     | 3000               |
| `api`    | FastAPI 0.140, SQLAlchemy 2, Alembic | 8000               |
| postgres | Postgres 17                          | 5432               |
| redis    | Redis 7                              | 6379               |

## Inicio rápido

Requisito: Docker. Ni Node ni Python en la máquina.

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml exec api alembic upgrade head
docker compose -f docker-compose.local.yml exec api python -m app.seed
```

- Web: <http://localhost:3000> — **`admin@local.dev`** / **`local-admin-2026`**
- API: <http://localhost:8000/docs>

Comandos de a diario:

| Comando | Descripción |
| ------- | ----------- |
| `docker compose -f docker-compose.local.yml exec api pytest` | Pruebas de la API |
| `docker compose -f docker-compose.local.yml exec api alembic upgrade head` | Aplicar migraciones |
| `docker compose -f docker-compose.local.yml exec api alembic revision --autogenerate -m "msg"` | Nueva migración |

## Pantallas

| Ruta             | Qué hace                                                               |
| ---------------- | ---------------------------------------------------------------------- |
| `/accounts`      | El PUC como árbol: CRUD, borrado lógico, importación y gráfica de saldo |
| `/third-parties` | Personas y empresas, catálogos DANE, dígito de verificación del NIT     |
| `/vouchers`      | Editor de comprobantes: borrador, contabilización, reversión            |
| `/ledger`        | El libro: movimientos con saldo acumulado, filtros y export a .xlsx     |
| `/periods`       | Cierre y reapertura de los meses                                        |
| `/exogena`       | XML de exógena, historial re-descargable y la UVT detrás del umbral     |

Español e inglés a un clic; el idioma es una cookie, no un segmento de la URL.

## Arquitectura

**La API, por módulos de dominio** (`api/app/modules/`): `accounts`, `vouchers`,
`periods`, `ledger`, `third_parties`, `locations`, `exogena`, `uvt`, `auth`,
`health`. Cada módulo repite el mismo molde, así que se sabe dónde mirar sin
abrir nada:

| Archivo      | Responsabilidad                                             |
| ------------ | ----------------------------------------------------------- |
| `models.py`  | Las tablas. SQLAlchemy y nada más                           |
| `schemas.py` | Lo que entra y sale por HTTP. Pydantic, en el borde         |
| `service.py` | Las reglas y las transacciones. No sabe qué es una petición |
| `router.py`  | Rutas, códigos de estado y dependencias. Sin lógica         |
| `errors.py`  | Errores del módulo; un solo handler los traduce a HTTP      |

La dirección de dependencias es siempre `router → service → models`, y ningún
módulo importa el router de otro: para leer un dato se consulta la tabla ajena;
para aplicar una regla se llama al service ajeno (comprobantes le pregunta a
`PeriodService` si el mes está abierto). Las reglas puras — jerarquía del PUC,
partida doble, dígito de verificación, XML — viven en archivos sin framework
(`puc.py`, `posting.py`, `documents.py`, `report.py`) que se prueban sin base
de datos.

**La web, por rutas** (`web/src/`): las páginas son Server Components que traen
los datos con el token — una cookie httpOnly que nunca llega al navegador — y la
interacción vive en Client Components que escriben únicamente a través de
Server Actions. Por eso `API_URL` no es `NEXT_PUBLIC_*`.

## Modelo de datos

![Modelo entidad-relación](docs/modelo-entidad-relacion.png)


## Decisiones de diseño

**El plan de cuentas.** En el PUC la jerarquía ya viene escrita en el propio
código: `1` es la clase (Activo), `11` el grupo (Disponible), `1105` la cuenta
(Caja), `110505` la subcuenta (Caja general) y de 7 dígitos en adelante los
auxiliares de cada empresa. Por eso aquí solo se digita el código y de él sale
todo lo demás: el nivel por la longitud (3 y 5 dígitos se rechazan porque no
existen en el PUC) y el padre por el prefijo — el de `110505` es `1105`. No se
puede crear una cuenta sin su padre ni borrar una que tenga hijas, y como nivel
y padre se calculan en vez de digitarse, la jerarquía no puede quedar
incoherente. Leer una rama completa es un simple `LIKE '11%'`. Los movimientos
solo entran por las cuentas hoja: contabilizar en `1105` existiendo `110505`
haría contar doble a cualquier reporte que sume el árbol.

**Los comprobantes.** Un comprobante no entra a los libros si no cuadra:
débitos iguales a créditos y mínimo dos líneas, validado en el código y en la
base de datos. Una vez contabilizado no se toca: si está mal, se reversa, y el
asiento inverso queda contabilizado en la misma operación, visible y enlazado
con el original. ¿Y si dos personas contabilizan al mismo tiempo? Ambas
querrían el mismo consecutivo. El número se asigna solo al contabilizar (los
borradores no lo gastan), se calcula como el mayor existente más uno, y un
índice único hace que Postgres acepte solo a una; la que pierde recalcula y
reintenta, hasta cinco veces. Así nunca hay dos comprobantes con el mismo
número — lo garantiza la base de datos, no el código —, la numeración queda
seguida y sin huecos, y el número y la contabilización se guardan en una misma
transacción. Se descartó la secuencia de Postgres porque deja huecos cuando
una transacción se cancela, y en un consecutivo contable eso es peor.

**Los saldos y el dinero.** Los saldos no se guardan: se calculan sumando las
líneas contabilizadas, porque una copia guardada se desactualiza en cuanto una
escritura falla a medias (si se volviera lento, la salida sería una vista
materializada, no una columna). Y ningún importe pasa por un float:
`Numeric(18,2)` en Postgres, `Decimal` en Python, cadenas decimales en HTTP y
centavos enteros en el navegador.

**Los períodos.** Los meses se cierran y se pueden reabrir, y cada cambio
registra quién lo hizo y cuándo. Un cierre irreversible volvería permanente un
mes mal digitado.

**La empresa.** Hay una sola, así que sus datos (NIT, razón social) viven en el
`.env` y no en una tabla: una tabla `companies` tendría siempre una única fila,
y si algún día hubiera varias empresas, lo que haría falta es una columna de
tenant en todas las tablas, no esa tabla.

## Extras implementados

- **Exportación del libro a .xlsx** — un contador pega el libro en un papel de
  trabajo; openpyxl ya era dependencia de la importación.
- **Autenticación JWT** — cookie httpOnly, solo el servidor llama a la API.
- **Un comando levanta todo** — `docker compose -f docker-compose.local.yml up`.

## Limitaciones

- **Una empresa, una moneda, sin multi-tenencia.**
- **Sin administración de usuarios ni roles** — todo autenticado puede todo.
- **Sin adjuntos, PDF ni reportes impresos.**
- **La UVT se lee de una página de terceros** — parseo defensivo y cada intento
  registrado, pero un cambio de maquetación allá rompe la consulta; de ahí la
  sobrescritura manual.
- **Sin cola ni eventos** — todo se resuelve en la petición; a más escala, ver
  producción.

## Pendientes

- **La prueba de concurrencia.** Cómo: Postgres dentro de la suite y dos
  contabilizaciones en paralelo; la garantía a observar ya existe.

## Qué cambiaría para producción

- **Auditoría en los datos maestros** — comprobantes y períodos ya registran
  quién y cuándo; una tabla `quién/cuándo/qué` cubriría el resto.
- **Una cola para los trabajos en segundo plano** — Redis ya está en el stack;
  el refresco de la UVT y lo que se le sume pertenecen a un worker con
  reintentos que sobreviva al reinicio.
- **Rate limiting y bloqueo en el login**, que hoy acepta intentos tan rápido
  como lleguen.

## Producción


```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```