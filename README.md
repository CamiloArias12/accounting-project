# accounting-project

Monorepo de la plataforma contable. Todo corre en Docker.

## Estructura

```
accounting-project/
├── api/                        # Backend
├── web/                        # Frontend
├── scripts/                    # Aprovisionamiento y despliegue, idempotentes
├── docker-compose.local.yml    # Desarrollo
└── docker-compose.prod.yml     # Producción
```

| Servicio | Stack                                | Puerto             |
| -------- | ------------------------------------ | ------------------ |
| `web`    | Next.js 16, React 19, Tailwind 4     | 3000               |
| `api`    | FastAPI 0.140, SQLAlchemy 2, Alembic | 8000               |
| postgres | Postgres 17                          | 5432 (solo en dev) |
| redis    | Redis 7                              | 6379 (solo en dev) |

### El backend, por módulo de negocio

```
api/
├── app/
│   ├── main.py                 # Arranque: middlewares, handlers, routers
│   ├── api/v1/router.py        # El único sitio donde se montan los módulos
│   ├── modules/                # Un paquete por área del dominio
│   │   ├── accounts/           # Plan de cuentas: PUC, importación, caché
│   │   ├── auth/               # Usuarios, JWT, dependencia `current_user`
│   │   ├── vouchers/           # Comprobantes: cuadre, contabilización, reversión
│   │   ├── periods/            # Cierre y reapertura de períodos
│   │   ├── ledger/             # Libro mayor y libro auxiliar
│   │   ├── third_parties/      # Terceros, documentos y dígito de verificación
│   │   ├── locations/          # Catálogos DANE: país, departamento, ciudad
│   │   ├── exogena/            # Reporte XML e historial de generaciones
│   │   ├── uvt/                # Valor de la UVT y su integración externa
│   │   └── health/             # La sonda que espera el despliegue
│   └── shared/                 # Config, sesión, paginación, errores, logging
├── alembic/versions/           # Migraciones, incluidos los catálogos sembrados
└── tests/                      # 40 pruebas — ver «Las pruebas», más abajo
```


| Archivo | Responsabilidad |
| ------- | --------------- |
| `models.py` | Las tablas. SQLAlchemy y nada más |
| `schemas.py` | Lo que entra y sale por HTTP. Pydantic, en el borde |
| `service.py` | Las reglas y las transacciones. No sabe qué es una petición |
| `router.py` | Rutas, códigos de estado y dependencias. Sin lógica |
| `errors.py` | Los errores del módulo, que un handler traduce a HTTP |


### El frontend, por ruta

```
web/src/
├── app/
│   ├── (app)/                  # Bajo sesión, una carpeta por pantalla de las
│   │   │                       #   de «Pantallas»; ledger/export/ y
│   │   │                       #   exogena/[id]/file/ son descargas, no vistas
│   │   └── loading.tsx         # El esqueleto de espera, uno para todas
│   └── (auth)/login/           # La única ruta pública
├── actions/                    # Server Actions: el único camino de escritura
├── components/                 # Vistas y componentes; `ui/` es el kit base
├── lib/                        # Cliente de la API, sesión, dinero, formato
├── types/                      # El contrato con la API, escrito a mano
└── i18n/                       # Español e inglés, elegidos por cookie
```

## Modelo de datos

Doce tablas. Diagrama exportado de DBeaver sobre el esquema real, no dibujado a
mano: si difiere de la base, la base tiene la razón.

![Modelo entidad-relación](docs/modelo-entidad-relacion.png)


## Plan de cuentas

El dominio implementado es el PUC colombiano: una jerarquía de cinco niveles
donde **el nivel se deriva de la longitud del código** y el padre es su prefijo.

```
1        Clase       ACTIVOS
11       Grupo         DISPONIBLE
1105     Cuenta          CAJA
110505   Subcuenta         CAJA GENERAL
11050501 Auxiliar            (cualquier código más largo)
```

En <http://localhost:3000/accounts> se recorre el árbol, se busca, se crean y
editan cuentas, se borran de forma lógica y se restauran, y se importa la
planilla.

## Pantallas

| Ruta             | Qué hace                                                                    |
| ---------------- | --------------------------------------------------------------------------- |
| `/accounts`      | El plan como árbol: buscar, crear, editar, borrar lógicamente, restaurar, importar |
| `/third-parties` | Personas naturales y jurídicas, con los lugares DANE y el dígito de verificación del NIT |
| `/vouchers`      | Listado y editor; guardar un borrador, contabilizarlo, reversar uno contabilizado |
| `/ledger`        | Saldos por cuenta, movimientos de una cuenta y el libro auxiliar en .xlsx    |
| `/periods`       | Los doce meses de un año, cerrados y reabiertos                              |
| `/exogena`       | Generar el XML, descargar uno anterior y administrar la UVT detrás de él     |

Todo está en español o en inglés a un clic, y el idioma es una cookie, no un
segmento de la URL.

## Decisiones de diseño

### El código es la jerarquía

El nivel es la longitud del código y el padre es su prefijo, así que ambos se
derivan a la entrada y no pueden contradecirse. Leer una rama es un
`LIKE '1105%'`; el costo es que un código no se renombra sin mover sus hijos.

### Solo las hojas reciben movimientos

Contabilizar en `1105` existiendo `110505` lo contaría dos veces en todo reporte
que recorra el árbol. La regla vive en el dominio, no en el endpoint.

### Los saldos se calculan, nunca se guardan

El libro es lo que suman las líneas contabilizadas: una segunda copia se separa
de la primera en cuanto una escritura falla a medias. Saldo inicial y movimiento
salen en una consulta; si se volviera lento, vista materializada y no columna.

### El cuadre es precondición de contabilizar, no pie de reporte

Débitos iguales a créditos y mínimo dos líneas antes de entrar a los libros.

### Borrador, contabilizado y reversión

Un borrador se edita y no toca los saldos; un contabilizado no se altera, se
cancela con el asiento inverso contabilizado en la misma operación. El par queda
visible: el original marcado y la reversión apuntando a él.

### Cierre de periodo, y reapertura

Solo los periodos cerrados tienen fila, así que un mes sin fila está abierto.
Reabrir se permite —un cierre irreversible vuelve permanente un mes mal
digitado— y cada cambio registra quién y cuándo.

### La empresa es configuración

Con una sola empresa, `companies` sería una tabla de una fila y cada consulta
llevaría una llave foránea con un único valor posible. Se imprime en pantalla y
se estampa en la exógena; con varias, sería una columna de tenant.

### Concurrencia

El consecutivo lo resuelve un índice único y no un bloqueo: el perdedor
reintenta con el siguiente número. Lo demás se apoya en la base — una
transacción por comprobante, una instantánea por reporte.

### El dinero

`Numeric(18,2)` en Postgres, `Decimal` en Python, cadenas decimales sobre HTTP y
centavos enteros en el navegador: ningún float toca un importe en ningún punto.

### La exógena y la UVT

Cada generación guarda sus bytes, así que re-descargarla entrega lo que se
presentó y no lo que dirían los libros hoy. El POST devuelve el registro y
`?download=true` el archivo. La UVT se guarda por año con cada intento anotado,
y un valor puesto a mano manda sobre la fuente.

## Las pruebas: qué se probó y por qué

Cuarenta pruebas en `api/tests`, que se corren con
`docker compose -f docker-compose.local.yml exec api pytest`. No son cobertura:
son una por regla que, si se rompe, deja los libros mal sin que nadie se entere.
Una cuenta que deja de aparecer en un listado se nota en la primera pantalla;
un comprobante descuadrado que entra a los libros
no se nota hasta que el balance de prueba deja de cuadrar meses después, y para
entonces ya nadie sabe cuál de los mil asientos fue.

Lo que protegen, en orden de riesgo:

- **El cuadre.** Débitos iguales a créditos, mínimo dos líneas, una sola columna
  por línea, sin negativos y con dos decimales — en `Decimal`, con el caso que
  justifica el tipo: `0.10 + 0.20` debe dar exactamente `0.30`.
- **La jerarquía del PUC.** El nivel y el padre salen del código, el código no se
  renombra, y solo las hojas reciben movimientos.
- **Los estados del comprobante.** Un borrador se edita y se borra; uno
  contabilizado tiene consecutivo y no se toca, solo se reversa. Y las tres cosas
  que la reversión no permite: reversar dos veces, reversar una reversión,
  reversar un borrador.
- **El período.** Un mes sin fila está abierto; cerrado rechaza la
  contabilización pero sigue aceptando borradores; el cierre sigue al período y
  no a la fecha del papel.
- **El libro mayor.** El borrador no llega, el reporte suma cero, las fechas
  separan el saldo inicial del movimiento, y la reversión devuelve el saldo
  medido sobre los libros y no afirmado.
- **La exógena.** El DV del informante se verifica antes de firmar el archivo,
  una fila por tercero y concepto, el umbral en UVT convertido a pesos, y el
  archivo que se vuelve a descargar es byte por byte el que se presentó.
- **La UVT.** Reintento ante fallo transitorio, rendición tras tres intentos, el
  año único para que una tarea nocturna no acumule filas, y el valor manual que
  una consulta nunca sobrescribe.
- **La autenticación.** Un solo test recorre los once endpoints de lectura y las
  escrituras: un router montado sin la dependencia es como se publican datos de
  negocio, y eso no se ve en las pruebas de ese router.

Lo que deliberadamente no se prueba: el catálogo DANE, que son datos de una
migración ya ejecutada; el formato del `.xlsx` más allá de que abra, traiga
números y sume cero; los listados y sus filtros, que fallan a la vista; y el
frontend, donde el tiempo rindió más en las reglas del servidor.

Queda un hueco conocido: **la concurrencia no tiene prueba**. Las pruebas corren
sobre SQLite en memoria con una sola conexión, así que la carrera por el
consecutivo no se puede reproducir ahí. La garantía es el índice único más el
reintento descrito arriba; probarla de verdad pide levantar Postgres en la suite
y lanzar dos contabilizaciones en paralelo.

## Más allá del núcleo contable

Cinco cosas que los libros no necesitaban para cuadrar, y la razón de cada una:

- **Exportación del libro a hoja de cálculo.** El libro auxiliar, en
  `/ledger/export`. Un contador filtra, totaliza y pega un libro en un papel de
  trabajo, así que tiene que salir de la aplicación como archivo — y openpyxl ya
  era dependencia para la importación del plan, así que no costó código nuevo en
  la cadena de suministro.
- **Una gráfica del saldo de una cuenta en el tiempo.** En el detalle de cuenta
  del libro. Dibujada a partir de los mismos asientos que muestra la tabla de
  abajo y no de un segundo endpoint: una gráfica que contradice las cifras
  impresas debajo es peor que ninguna gráfica.
- **Autenticación JWT.** La aplicación está detrás de un login; el token vive en
  una cookie httpOnly que el JavaScript del navegador no puede leer, y solo el
  servidor lo adjunta a las llamadas a la API.
- **Un solo comando levanta el sistema completo.**
  `docker compose -f docker-compose.local.yml up -d --build`.
- **CI en GitHub Actions**, y un despliegue que la sigue — ver más abajo.

La gráfica es SVG dibujado a mano en vez de una librería de gráficas. Una sola
gráfica de línea no justifica recharts y sus dependencias de d3 en el bundle, y
todo lo que una librería aportaría aquí — un path, un eje, una etiqueta al pasar
el mouse — es el componente mismo. Si aparece una segunda o una tercera gráfica,
ese trato se invierte.

Está escalada a los datos en vez de anclada a cero. Forzar el cero en el eje es
la regla de un gráfico de barras, donde la longitud de la barra *es* el valor;
una cuenta de caja parada en 3.500.000 se pasaría toda la gráfica como una línea
plana abajo, con su movimiento real invisible. Las etiquetas del eje llevan la
magnitud, y la línea del cero se dibuja siempre que caiga a la vista.

La línea escalona en vez de inclinarse, porque eso es lo que hace un saldo:
mantiene su valor hasta que el siguiente movimiento lo cambia. Interpolar entre
dos asientos dibujaría una diagonal a través de días en los que no pasó nada.

## Limitaciones

Conocidas y deliberadas, cada una con su porqué:

- **Una empresa, una moneda, sin multi-tenencia.** Ver arriba.
- **Sin administración de usuarios.** Los usuarios existen y se autentican; no
  hay pantalla para crearlos ni roles — todo usuario autenticado puede hacer
  todo.
- **Sin adjuntos en los comprobantes**, sin salida en PDF, sin reportes
  impresos.
- **La fuente de la UVT es una página de terceros.** Se parsea de forma
  defensiva y cada intento queda registrado, pero un cambio de maquetación allá
  rompe la consulta — de ahí la sobrescritura manual.
- **Sin cola ni eventos.** Todo se resuelve dentro de la petición que lo pide.
  Con esta carga alcanza; a más escala, el trabajo se reparte con eventos o una
  cola.

## Qué cambiaría para producción

- **Traza de auditoría en cada escritura.** Los comprobantes registran quién los
  creó y contabilizó, y los periodos quién los cerró, pero los datos maestros
  no — una tabla de `quién/cuándo/qué` cubriría el resto.
- **Una cola para los trabajos en segundo plano.** Redis ya está en el stack, así
  que el refresco de la UVT —y cualquier cosa que se le sume después: la exógena
  de un año entero, un envío por correo— pertenece a un worker aparte, con
  reintentos y con la corrida sobreviviendo al reinicio del proceso que la pidió.
- **Rate limiting y bloqueo en el endpoint de login**, que hoy acepta intentos
  tan rápido como lleguen.

## Requisitos

Docker. Nada más — ni Node, ni Python en la máquina.

## Desarrollo

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml exec api alembic upgrade head
docker compose -f docker-compose.local.yml exec api python -m app.seed
```

La última línea deja la base utilizable: el usuario **`admin@local.dev`** /
**`local-admin-2026`** y 142 cuentas del PUC en los cuatro niveles. Se puede
repetir sin romper nada, el usuario se cambia con `SEED_EMAIL` y
`SEED_PASSWORD`, y fuera de `ENVIRONMENT=local` se niega a correr.

El plan viene de [`api/fixtures/puc.csv`](./api/fixtures/puc.csv), que además de
código, nombre y naturaleza lleva el concepto DIAN y la marca de retención que
la exógena necesita. El mismo plan está en
[`api/fixtures/puc.xlsx`](./api/fixtures/puc.xlsx) con el formato de la planilla
—código, nombre, tipo, naturaleza— para probar la importación desde
`/accounts`.

El `.env` copiado arranca tal cual; esto es lo que trae:

```bash
ENVIRONMENT=local

WEB_PORT=3000                  # puertos publicados en el host
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

POSTGRES_USER=postgres         # obligatorios: Compose falla sin ellos
POSTGRES_PASSWORD=postgres
POSTGRES_DB=accounting
# JWT_SECRET=                  # fuera de local la API no arranca sin él

DB_POOL_SIZE=10                # conexiones por réplica de la API
DB_MAX_OVERFLOW=5
CACHE_TTL_SECONDS=300
COMPANY_NIT=900000000-5        # la empresa es configuración, no una tabla
COMPANY_LEGAL_NAME=Mi Empresa S.A.S.

UVT_SOURCE=http                # `simulated` responde sin red — lo que usan las pruebas
UVT_SOURCE_URL=https://www.gerencie.com/uvt.html
UVT_SOURCE_TIMEOUT_SECONDS=10

CORS_ORIGINS=["http://localhost:3000"
```

- Web: <http://localhost:3000>
- API: <http://localhost:8000> · documentación en <http://localhost:8000/docs>



## Producción

Producción es el otro archivo:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```


## Instancia en vivo

<http://46.224.38.172:3001> — ingresar con `demo@accounting-project.dev` /
`demo-accounting-2026`.

## Comandos

Todos con `-f docker-compose.local.yml`, que aquí se abrevia como `$C`:

```bash
C="docker compose -f docker-compose.local.yml"
```

| Comando                                          | Descripción         |
| ------------------------------------------------ | ------------------- |
| `$C exec api pytest`                             | Pruebas de la API   |
| `$C exec api alembic upgrade head`               | Aplicar migraciones |
| `$C exec api alembic revision --autogenerate -m "msg"` | Nueva migración |
