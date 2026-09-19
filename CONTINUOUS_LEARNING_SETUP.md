# Aprendizaje continuo controlado

Esta versión agrega aprendizaje continuo sin modificar las reglas tributarias.

## 1. Supabase

Ejecutar `data/ai_feedback.sql` en el proyecto Supabase que se utilizará para el aprendizaje.

La tabla almacena únicamente ejemplos de campo validados (`text`, `label`), no el expediente completo.

## 2. Variables de GitHub Actions

En el repositorio del AI Engine, crear dos Actions Secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

La clave `service_role` se usa solamente dentro de GitHub Actions. Nunca debe ir al frontend.

## 3. Flujo

Liquidador → `/feedback` → Supabase → GitHub Actions diario → entrenamiento → prueba contra el modelo actual → publicación solo si mejora.

El umbral inicial es de 40 ejemplos nuevos, con diversidad mínima de 5 etiquetas y 2 ejemplos por etiqueta. El candidato debe mejorar al menos 1 punto porcentual en su conjunto de validación de aprendizaje.

El workflow puede ejecutarse manualmente desde GitHub Actions para pruebas.

## 4. Seguridad funcional

La IA no modifica las fórmulas de liquidación, intereses, sanciones, pagos ni reglas DIAN. Solo aprende clasificación/interpretación de campos validados.
