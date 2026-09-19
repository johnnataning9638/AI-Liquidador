# DIAN AI ENGINE — v0.7.0

Aprendizaje continuo controlado sobre la base estable v0.6.6.

- El API conserva la interpretación y las reglas determinísticas existentes.
- `/feedback` recibe únicamente ejemplos de campos confirmados/corregidos.
- Los ejemplos persistentes se almacenan en Supabase.
- GitHub Actions puede reentrenar automáticamente de forma programada.
- Un nuevo modelo solo se publica si supera al modelo actual en un conjunto de validación independiente.
- Las reglas tributarias y el motor de liquidación quedan fuera del aprendizaje neuronal.

Consulta `CONTINUOUS_LEARNING_SETUP.md` para la configuración.

# DIAN AI ENGINE — v0.6.3

Segunda versión del motor de IA.

## Qué cambió

- Dataset v2 ampliado.
- Entrenamiento enfocado en casos difíciles: NIT vs RECIBO vs TDJ.
- Soporte explícito de números en notación científica como `4,9111E+12`.
- Reglas determinísticas con prioridad para campos críticos.
- Reporte de validación por clase.
- Benchmark de los casos que detectamos durante las pruebas.

## Importante

La red neuronal NO debe decidir sola reglas tributarias ni imputaciones.
La arquitectura es:

**Reglas determinísticas → interpretación segura**
**Red neuronal → interpretación ambigua**
**Motor DIAN → cálculo exacto**

## Comandos

Activar entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Entrenar:

```powershell
python src/train.py
```

Benchmark:

```powershell
python tests/benchmark.py
```

Predicción:

```powershell
python src/predict.py "4,9111E+12"
python src/predict.py "3,0047E+12"
```

El modelo queda en:

`models/field_classifier.pt`

y el reporte en:

`models/validation_report.json`


## v0.3 — corrección NIT vs VALOR

Se corrigió la prioridad de clasificación de números puros.

Ahora, antes de tratarlos como valores monetarios, el motor reconoce una estructura de NIT de 9 dígitos cuyo primer dígito es 8 o 9, con soporte opcional de dígito de verificación.

Esto evita el caso detectado durante las pruebas:

`900123456` → `VALOR` ❌

y lo convierte en:

`900123456` → `NIT` ✅

La prioridad queda:

1. TDJ explícito
2. NIT explícito
3. Recibo/Documento Fuente explícito
4. Fecha
5. Notación científica documental
6. NIT por estructura
7. Valor
8. Red neuronal para ambigüedades


## v0.4 — intérprete de registros

Ahora el motor no solo clasifica celdas: intenta reconstruir registros completos.

Soporta:
- tablas horizontales con encabezados;
- tablas verticales/transpuestas;
- datos sin encabezados;
- campos en distinto orden;
- notación científica para Documento Fuente;
- normalización de fechas;
- normalización de valores;
- agrupación de documento + fecha + valor + estado.

### Probar

```powershell
python tests/structured_tests.py
```

También puedes probar directamente:

```powershell
python src/interpret.py "Documento Fuente`tFecha Presentacion`tValor Pagado`tEstado`n4,9111E+12`t5/03/2026`t4.137.000`tINICIAL"
```

La salida será JSON con `records`.


### Ejemplo sin encabezados

```text
INICIAL    4,9111E+12    5/03/2026    4.137.000
INICIAL    4,9111E+12    18/03/2026   3.579.000
```

El intérprete intenta reconstruir dos registros completos, manteniendo la relación documento-fecha-valor.


## v0.5 — orden libre sin encabezados

Se reforzó la reconstrucción de registros sin títulos:
- el orden de documento, fecha, valor y estado dentro de una fila no importa;
- se pueden reconstruir registros con datos repartidos en varias líneas;
- estados DIAN frecuentes se reconocen de forma determinística;
- el agrupamiento busca completar documento + fecha + valor;
- se conserva la conversión de notación científica.

Prueba:

```powershell
python tests/structured_tests.py
```


## v0.6.3 — adaptador de pagos DIAN

Convierte los registros interpretados por el motor en la estructura de la tabla de pagos:

- `tdj_no`
- `recibo_no`
- `fecha_pago`
- `valor_pago`
- `tipo`
- `tasa`
- `observacion`

Reconoce TDJ escritos como `TDJ 123456789` o `Título de depósito judicial 123456789`.
Los recibos en notación científica se normalizan a dígitos completos.

**Importante:** este adaptador solo estructura los datos. No imputa valores a impuesto, intereses o sanción.

### Prueba

```powershell
python tests/payment_adapter_tests.py
```

### Procesar un archivo

```powershell
python src/payments.py data/muisca_8_registros.txt
```


## v0.6.3 — corrección de filas sin encabezados

Se corrigió la lectura de portapapeles cuando los separadores tabulares llegan convertidos a espacios. El motor ahora detecta filas de pagos por tokens estructurados (fecha, valor, notación científica y estado) sin dividir arbitrariamente texto libre.

Incluye regresiones para:
- filas horizontales separadas por espacios;
- datos verticales;
- TDJ;
- los 8 registros Muisca de prueba;
- adaptación final a la tabla de pagos.

### Pruebas

```powershell
python tests/structured_regression_tests.py
python tests/payment_adapter_tests.py
python src/payments.py data/muisca_8_registros.txt
```

## Integración con Liquidador DIAN Web v16.32.32

El API local expone:

- `GET /health`
- `POST /classify`
- `POST /interpret/payments`

El endpoint `/interpret/payments` recibe `{ "text": "..." }` y devuelve registros adaptados a pagos DIAN. El adaptador únicamente estructura datos; la imputación y liquidación permanecen en el motor JavaScript del Liquidador.

Inicio:

```powershell
uvicorn src.api:app --host 127.0.0.1 --port 8787
```

## Inicio local del AI Engine (Windows)

La forma recomendada de iniciar el servicio es ejecutar `run_ai_engine.bat`.
El lanzador verifica Python, dependencias y la carga real de `src.api` antes de iniciar Uvicorn. Si ocurre un error, **la ventana permanece abierta** para mostrar el diagnóstico.

Servicio local:
- API: `http://127.0.0.1:8787`
- Salud: `http://127.0.0.1:8787/health`

Si el servicio no inicia, ejecutar `diagnostico_ai_engine.bat` y revisar el mensaje que aparece en pantalla.

No cierre la ventana negra mientras el Liquidador Web esté usando la IA.


### v0.6.3 — Importación inteligente de obligación

Se agrega `POST /interpret/obligation` para validar con IA DIAN los campos NIT, razón social, año y hasta seis cuotas. La IA no sustituye la extracción determinística: el Liquidador compara ambos resultados y bloquea la aplicación cuando detecta discrepancias en datos determinísticos.


## FASE DE ESTABILIZACION v0.6.6
- Confianza estructural por registro de pago.
- Anomalias estructurales visibles en la respuesta del API.
- Benchmark de regresion en `tests/stability_benchmark.py`.
- Contrato del API versionado y limite basico de solicitudes POST.
- La confianza nunca decide impuestos, intereses o sanciones.


## v0.7.1 - aprendizaje continuo y depuración

Los ejemplos confirmados se procesan solo una vez. Después de aceptar un nuevo modelo,
se marcan con `processed_at` y `training_run_id`. Se conserva una memoria pequeña de
hasta 10 ejemplos procesados por etiqueta y se eliminan los más antiguos para evitar
crecimiento indefinido de Supabase.
