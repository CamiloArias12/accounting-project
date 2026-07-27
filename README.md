# accounting-project

Monorepo de la plataforma contable. Todo corre en Docker.

## Estructura

```
accounting-project/
├── web/                        # Frontend — Next.js 16 + React 19 + Tailwind 4
├── api/                        # Backend  — FastAPI + SQLAlchemy async
├── docker-compose.yml          # Base = producción
└── docker-compose.override.yml # Desarrollo (Compose lo aplica solo)
```

| Servicio | Stack                                | Puerto             |
| -------- | ------------------------------------ | ------------------ |
| `web`    | Next.js 16, React 19, Tailwind 4     | 3000               |
| `api`    | FastAPI 0.140, SQLAlchemy 2, Alembic | 8000               |
| postgres | Postgres 17                          | 5432 (solo en dev) |
| redis    | Redis 7                              | 6379 (solo en dev) |

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
planilla. El modelo y la importación están documentados en
[`api/README.md`](./api/README.md).

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

El nivel es la longitud del código y el padre es su prefijo. Eso no es un atajo
sino lo que el PUC es en realidad: `110505` *está* dentro de `1105` por cómo
está escrito. Ambos se derivan a la entrada y nunca se le piden al llamante, así
que los dos no pueden contradecirse.

`parent_code` sigue siendo una columna real con llave foránea — derivada, pero
almacenada, para que la base de datos pueda negarse a borrar un padre que aún
tiene hijos incluso si se saltara la validación del servicio. Lo que no es, es
la *fuente* de la relación: se cambia un código y el padre se recalcula a partir
de él, nunca al revés.

Leer una rama completa es entonces un solo `LIKE '1105%'` en lugar de una
consulta recursiva. El costo es que un código no se puede renombrar sin mover
sus hijos, que es el trato correcto: en el PUC el código es la identidad.

### Solo las hojas reciben movimientos

Una línea de comprobante solo puede nombrar una cuenta que no tenga nada debajo.
Contabilizar en `1105` existiendo `110505` lo contaría dos veces en todo reporte
que recorra el árbol. La validación está en la capa de dominio, así que vale
para la API, para la importación y para cualquier cosa que se agregue después.

### Los saldos se calculan, nunca se guardan

No hay columna de saldo acumulado ni tabla de totales por cuenta. El libro es lo
que suman las líneas de los comprobantes contabilizados, y mantener una segunda
copia significa que las dos se separan la primera vez que una escritura falla a
medias — el error contable clásico donde el saldo y los movimientos ya no
coinciden y nadie sabe cuál tiene la razón.

El reporte obtiene el saldo inicial y el movimiento en **una sola** consulta:
agregación condicional sobre dos rangos de fechas en lugar de dos viajes. El
saldo corrido del detalle de cuenta se acumula en orden de fecha y consecutivo,
que es el orden en que se escribieron los libros y el único orden en el que un
saldo corrido significa algo.

Si esto se volviera lento sería una vista materializada refrescada al
contabilizar, no una columna — la derivación queda en un solo lugar de
cualquier forma.

### El cuadre es precondición de contabilizar, no pie de reporte

Los débitos deben igualar a los créditos antes de que un comprobante entre a los
libros, y un comprobante necesita al menos dos líneas. El proyecto de referencia
calcula esos totales solo para imprimirlos, así que un asiento descuadrado se
guarda tan feliz y el balance de prueba deja de cuadrar en silencio. Aquí
`totals.is_balanced` en el libro es una consecuencia, no una validación: si cada
comprobante cuadró, los libros en conjunto suman cero.

### Borrador y contabilizado

Un borrador es un documento de trabajo — editable, borrable, fuera de los
saldos. Un comprobante contabilizado tiene consecutivo y no se puede alterar en
absoluto, solo reversar. Esa es la línea entre un documento que alguien todavía
está escribiendo y un registro contable.

### Reversión en lugar de borrado

Un error contabilizado se corrige escribiendo el asiento que lo cancela: mismas
cuentas, débitos y créditos invertidos, contabilizado en la misma operación.
Dejar la corrección como borrador sería peor que cualquiera de los dos estados,
porque los libros muestran solo el error hasta que alguien se acuerde de
terminar. El par queda visible — el original queda marcado como reversado y la
reversión apunta de vuelta a él.

### Cierre de periodo, y reapertura

Solo los periodos *cerrados* tienen fila. Un mes sin fila está abierto, así que
los libros se pueden usar antes de que nadie haya creado un solo periodo, y
cerrar 2025-06 no exige que existan los otros once meses.

Reabrir está permitido, y a propósito: un periodo se cierra para frenar asientos
accidentales, no para volver el pasado inalcanzable, y un cierre que no se puede
deshacer convierte un mes mal digitado en uno permanente. Cada cambio registra
quién lo hizo y cuándo, que es la parte que de verdad importa para una
auditoría.

### La empresa es configuración

`COMPANY_NIT` y `COMPANY_LEGAL_NAME` son parámetros, no una tabla. La base de
datos entera pertenece a una sola empresa, así que una tabla `companies` tendría
exactamente una fila y cada consulta cargaría una llave foránea que solo puede
tomar un valor — los costos de la multi-tenencia sin ninguno de sus beneficios.
La especificación lista "empresa" como campo del comprobante; aquí es el mismo
valor para todos los comprobantes de la base, así que se imprime en pantalla y
se estampa en el archivo de exógena en vez de guardarse mil veces.

Si el producto alguna vez alojara varias empresas, el cambio es una columna de
tenant y una sesión con alcance — no la remoción de algo que nunca sostuvo nada.

### Concurrencia

Dos contabilizaciones compitiendo por el mismo consecutivo es la única carrera
que importa, y se resuelve con un índice único en vez de con un bloqueo: el
perdedor recibe un `IntegrityError`, hace rollback y reintenta con el siguiente
número. Un `SELECT max(number)` bajo bloqueo serializaría todas las
contabilizaciones del sistema para protegerse de algo que pasa rara vez.

Todo lo demás se apoya en las garantías de la propia base de datos. Un
comprobante y sus líneas se escriben en una transacción; el libro lee una sola
instantánea; el refresco de la UVT es idempotente porque el año es único, así
que ejecutarlo cada noche actualiza una fila en lugar de acumularlas.

### El dinero

`Numeric(18,2)` en Postgres, `Decimal` en Python, cadenas decimales sobre HTTP y
centavos enteros en el navegador. Un float no toca un importe en ningún punto:
el servidor rechaza un asiento descuadrado por una centésima, así que el total
que el usuario está viendo tiene que ser la misma cifra que el servidor va a
revisar.

### La exógena y la UVT

El reporte se construye a partir de comprobantes contabilizados, agrupados por
tercero y concepto DIAN, y redondeados a pesos enteros por fila antes de
totalizar — el archivo que recibe la DIAN no tiene centavos. Cada generación se
guarda con los bytes que produjo, así que volver a descargarla entrega lo que se
presentó y no lo que dirían los libros hoy; una reversión que llegue después no
puede cambiar un documento ya enviado.

La UVT se obtiene de una tabla publicada por red, se guarda por año y se
registra con cada intento — incluidos los fallidos, porque un umbral que usó en
silencio una UVT vieja es exactamente lo que el log de ejecuciones existe para
hacer visible. Un valor digitado a mano manda sobre la fuente y nunca lo
sobrescribe una consulta. Un umbral de cero no necesita UVT alguna, que es lo
que mantiene el reporte utilizable para un año del que nadie ha publicado una
todavía.

## Extensiones opcionales, y por qué estas

El enunciado lista un puñado de extras y pregunta cuáles se eligieron y por qué.
Cinco de ellos están aquí:

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
- **Un solo comando levanta el sistema completo.** `docker compose up -d --build`.
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

Conocidas, y deliberadas para un ejercicio de cinco días:

- **Una empresa, una moneda, sin multi-tenencia.** Ver arriba.
- **Sin administración de usuarios.** Los usuarios existen y se autentican; no
  hay pantalla para crearlos ni roles — todo usuario autenticado puede hacer
  todo.
- **El formato de exógena es el simplificado del enunciado**, no la
  especificación 1001 real de la DIAN, que son decenas de formatos con sus
  propios diseños.
- **Sin asiento de cierre.** Cerrar un periodo frena los asientos en él; no
  cancela las cuentas de ingresos y gastos contra el patrimonio del año.
- **Sin adjuntos en los comprobantes**, sin salida en PDF, sin reportes
  impresos.
- **La fuente de la UVT es una página de terceros.** Se parsea de forma
  defensiva y cada intento queda registrado, pero un cambio de maquetación allá
  rompe la consulta — de ahí la sobrescritura manual.
- **La paginación es por offset.** Está bien para estos volúmenes; una tabla de
  millones de comprobantes querría paginación por keyset, ya que `OFFSET 900000`
  igual recorre 900.000 filas.

## Qué cambiaría para producción

- **El consecutivo pasa a ser por libro.** La contabilidad real numera los
  comprobantes por tipo (CE, CI, CC…), no con una sola serie para todo. El
  mecanismo de reintento ante conflicto no cambia; solo se mueve el alcance de
  la unicidad.
- **Traza de auditoría en cada escritura.** Los comprobantes registran quién los
  creó y contabilizó, y los periodos quién los cerró, pero los datos maestros
  no — una tabla de `quién/cuándo/qué` cubriría el resto.
- **Los trabajos en segundo plano salen del request.** El refresco de la UVT
  corre en un background task de FastAPI, que muere con el proceso. Redis ya
  está en el stack; esto pertenece a un worker con reintentos que sobrevivan a
  un reinicio.
- **Rate limiting y bloqueo en el endpoint de login**, que hoy acepta intentos
  tan rápido como lleguen.
- **Observabilidad más allá de los logs.** Cada línea es JSON y lleva un id de
  request devuelto en `X-Request-ID`, lo que hace rastreable una llamada entre
  réplicas. Siguen sin haber métricas ni trazas, y "el libro se puso lento" no
  se responde sin ellas.
- **Respaldos, y una restauración que se haya ejecutado de verdad.** Un respaldo
  sin probar es una creencia, no un respaldo.

## Requisitos

Docker. Nada más — ni Node, ni Python en la máquina.

## Desarrollo

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
```

- Web: <http://localhost:3000>
- API: <http://localhost:8000> · documentación en <http://localhost:8000/docs>

El código está montado dentro de los contenedores, así que **web y API recargan
al editar**. Postgres y Redis se publican en el host para poder conectar un
cliente externo.

## Producción

`docker-compose.override.yml` se aplica automáticamente, así que producción
significa pasar solo el archivo base:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml exec api alembic upgrade head
```

Diferencias con desarrollo:

- Imágenes construidas desde el target `prod`: sin dependencias de desarrollo,
  sin código montado y con un usuario sin privilegios (`app` en la API, `nextjs`
  en la web).
- Next se sirve desde su salida `standalone`, no desde `next dev`.
- Postgres y Redis **no** publican puertos en el host: solo se alcanzan desde la
  red de Compose.
- `DEBUG=false` y `ENVIRONMENT=production`.

Las migraciones no corren al arrancar — se disparan explícitamente, para que un
despliegue con varias réplicas nunca compita consigo mismo.

## Instancia en vivo

<http://46.224.38.172:3001> — ingresar con `demo@accounting-project.dev` /
`demo-accounting-2026`. El PUC colombiano ya está cargado: 2.446 cuentas en los
cinco niveles, así que el árbol, la búsqueda y el selector de cuentas tienen
algo real adentro.

Es una máquina de demostración, no un servicio con garantía de disponibilidad, y
comparte el host con una aplicación de producción no relacionada. Por eso la
aplicación está en el puerto 3001 y la API escucha solo en loopback: la web la
alcanza por la red de Compose, y nada más lo necesita.

## Integración y despliegue continuos

`.github/workflows/ci.yml` corre en cada push y pull request: ruff, mypy y
pytest para la API, ESLint, `tsc` y un build de producción para la web. Cada
verificación corre dentro de las propias imágenes de este repositorio, así que
los Dockerfiles quedan ejercitados por el mismo job que revisa el código.

En `main`, una vez pasan las verificaciones, las imágenes se publican en GHCR y
el servidor se actualiza:

```
push a main → verificaciones → imágenes a ghcr.io → aprovisionar → desplegar → verificar
```

Dos scripts llevan el despliegue, ambos idempotentes:

- [`scripts/provision.sh`](./scripts/provision.sh) — instala Docker si falta y
  genera el `.env` del servidor con credenciales aleatorias, una sola vez. Nunca
  se regenera: la contraseña de Postgres queda grabada en el volumen la primera
  vez que se inicializa, y rotar `JWT_SECRET` cerraría la sesión de todo el
  mundo en cada push.
- [`scripts/deploy.sh`](./scripts/deploy.sh) — trae el commit exacto, migra con
  la imagen nueva *antes* de intercambiar los contenedores, levanta el stack y
  espera al endpoint de salud. Se niega a correr si un contenedor nuestro
  pertenece a otro proyecto de Compose, si un puerto está tomado por un proceso
  ajeno o si hay menos de 2 GB de disco libre.

Nada se construye en el servidor. Tiene 3,7 GB de RAM compartidos con la base de
datos de producción de alguien más, y un `next build` allí podría invocar al OOM
killer o llenar el disco. Las imágenes llegan del registro, ya construidas.

Un paso no se puede automatizar, porque hasta que exista GitHub no tiene por
dónde entrar: instalar la llave de despliegue.
[`scripts/setup-github-deploy.sh`](./scripts/setup-github-deploy.sh) lo hace en
un comando — genera la llave, la instala y sube `SSH_PRIVATE_KEY`,
`DEPLOY_HOST` y `SSH_KNOWN_HOSTS` al repositorio:

```bash
./scripts/setup-github-deploy.sh <ip-del-servidor>
```

Sin esos secretos el job de despliegue termina en verde y lo dice: el pipeline
no está roto, está sin configurar.

## Comandos

Todo corre dentro de los contenedores:

| Comando                                                            | Descripción           |
| ------------------------------------------------------------------ | --------------------- |
| `docker compose up -d`                                             | Levantar (dev)        |
| `docker compose down`                                              | Detener               |
| `docker compose logs -f api`                                       | Logs                  |
| `docker compose exec api pytest`                                   | Pruebas de la API     |
| `docker compose exec api ruff check .`                             | Lint de la API        |
| `docker compose exec api mypy .`                                   | Tipos de la API       |
| `docker compose exec api alembic upgrade head`                     | Aplicar migraciones   |
| `docker compose exec api alembic revision --autogenerate -m "msg"` | Nueva migración       |
| `docker compose exec web npm run lint`                             | Lint de la web        |
| `docker compose exec web npm run typecheck`                        | Tipos de la web       |

## Entorno

Todo vive en el `.env` de la raíz — ver [`.env.example`](./.env.example).
`POSTGRES_USER` y `POSTGRES_PASSWORD` son obligatorios: Compose falla en lugar
de arrancar con credenciales por defecto.

La web habla con la API **solo desde el servidor** (Server Components y Server
Actions), a través del nombre del servicio de Compose. Por eso `API_URL` no es
`NEXT_PUBLIC_*`: nunca llega al navegador, no queda horneada en el bundle y
cambiarla no obliga a reconstruir la imagen.

## Notas

`docker-compose.yml` fija `name: accounting`. Sin un nombre explícito, Compose
deriva uno del directorio y puede recrear los contenedores de cualquier otro
proyecto que viva en un directorio con el mismo nombre.

Dev y prod usan etiquetas de imagen distintas (`accounting-api:dev` /
`accounting-api:prod`, y lo mismo para `web`). Con una etiqueta compartida,
cambiar de modo hace que un `up` sin `--build` reutilice en silencio la imagen
del otro modo: la web arrancaría con el `CMD` de producción encima del bind
mount de desarrollo y entraría en bucle de reinicios.

## Licencia

Por definir.
