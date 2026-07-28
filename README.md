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
| postgres | Postgres 17                          | 5432 (solo en dev) |
| redis    | Redis 7                              | 6379 (solo en dev) |

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

- **El código es la jerarquía.** Ver la sección siguiente: el nivel es la
  longitud del código y el padre es su prefijo.
- **Solo las hojas reciben movimientos.** Contabilizar en `1105` existiendo
  `110505` contaría doble en todo reporte que recorra el árbol.
- **Los saldos se calculan, nunca se guardan.** Una segunda copia se separa de
  la primera en cuanto una escritura falla a medias; si se volviera lento, vista
  materializada y no columna.
- **El cuadre es precondición de contabilizar.** Débitos = créditos y mínimo dos
  líneas antes de entrar a los libros, en el dominio y en la base.
- **Un contabilizado no se altera: se reversa.** El asiento inverso se
  contabiliza en la misma operación y el par queda visible y enlazado.
- **Cierre por período, reapertura permitida.** Con quién y cuándo en cada
  cambio; un cierre irreversible volvería permanente un mes mal digitado.
- **La empresa es configuración.** Una sola empresa haría de `companies` una
  tabla de una fila; con varias, sería una columna de tenant.
- **Concurrencia sin bloqueos.** Ver la sección siguiente; lo demás es una
  transacción por comprobante.
- **Ningún float toca un importe.** `Numeric(18,2)` en Postgres, `Decimal` en
  Python, cadenas decimales en HTTP y centavos enteros en el navegador.

## Clase, grupo, cuenta y subcuenta: cómo vive la jerarquía

El PUC ya trae la jerarquía escrita en el propio código: `1` es la clase
(Activo), `11` el grupo (Disponible), `1105` la cuenta (Caja), `110505` la
subcuenta (Caja general), y de 7 dígitos en adelante van los auxiliares que
crea cada empresa. Cada código empieza con el código de su padre.

Por eso no hay una tabla por nivel ni un padre que se elija a mano. Se digita
solo el código, y de él sale todo lo demás:

- **El nivel es la longitud del código:** 1 dígito → clase, 2 → grupo,
  4 → cuenta, 6 → subcuenta, 7 o más → auxiliar. Un código de 3 o 5 dígitos se
  rechaza porque no corresponde a ningún nivel del PUC.
- **El padre es el prefijo:** el padre de `110505` es `1105`, y el de `1105` es
  `11`. Nadie escoge el padre en un formulario; sale del código.
- **El padre debe existir primero:** no se puede crear `110505` si no existe
  `1105`, ni borrar una cuenta que todavía tenga hijas vivas.

El nivel y el padre sí se guardan como columnas — para filtrar y armar el árbol
rápido — pero nunca los escribe el usuario: se calculan del código al crear la
cuenta, así que no pueden contradecirlo.

Qué garantiza:

- **La jerarquía no puede quedar incoherente.** Como nivel y padre se derivan
  del código, no existe forma de que `110505` termine colgada de `2105` o
  marcada como grupo. El error simplemente no se puede digitar.
- **Leer una rama es trivial:** todo lo que cuelga de `11` es todo código que
  empieza por `11` — un `LIKE '11%'`, sin consultas recursivas.
- **Los reportes no cuentan doble:** los movimientos solo entran por las hojas
  (ver "Solo las hojas reciben movimientos"), y los niveles superiores se
  obtienen sumando la rama.

Se descartó lo complejo: tablas separadas por nivel, un `parent_id` digitado a
mano o extensiones de árbol de Postgres. Habrían agregado piezas que pueden
contradecirse entre sí para representar algo que el código de la cuenta ya
dice solo.

## ¿Y si dos personas contabilizan al mismo tiempo?

Las dos querrían el mismo número de comprobante. Se resolvió sin bloqueos,
con tres ideas simples:

1. **Un borrador no tiene número.** El número se asigna solo al contabilizar,
   así que los borradores abandonados no gastan consecutivo.
2. **El número se calcula sin bloquear nada:** se mira el mayor que exista y se
   le suma uno.
3. **La base de datos es el árbitro.** Un índice único sobre el número hace que,
   si dos peticiones llegan con el mismo, Postgres acepte una sola. La que
   pierde recibe el error, recalcula con el número ya actualizado y vuelve a
   intentar (hasta cinco veces).

Qué garantiza:

- **Nunca dos comprobantes con el mismo número**, aunque corran varias copias
  de la API a la vez. Lo garantiza Postgres, no el código.
- **Sin huecos:** como un contabilizado nunca se borra (se reversa), la
  numeración queda 1, 2, 3… seguida.
- **Todo o nada:** el número y la contabilización se guardan en la misma
  transacción; no existe un comprobante "numerado pero sin contabilizar".

El costo asumido: si una petición pierde cinco veces seguidas — algo que exige
muchísima concurrencia para una empresa sola —, falla y el usuario reintenta.
Se descartó usar una secuencia de Postgres porque deja huecos cuando una
transacción se cancela, y en un consecutivo contable eso es peor.

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