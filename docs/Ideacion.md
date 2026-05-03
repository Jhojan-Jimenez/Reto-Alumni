OBSERVATORIO LABORAL AUTOMATIZADO
Universidad de La Sabana – Dirección de Alumni
Propuesta técnica, crítica y ejecutable
RESPUESTAS A LAS PREGUNTAS CRÍTICAS
Antes de la arquitectura, respondo con criterio técnico y sin eufemismos:

O*NET OnLine — ¿Tiene API? ¿Es gratuita? ¿Sirve para Colombia?
Sí existe: O*NET Web Services (services.onetcenter.org)
Sí es gratuita para uso educativo (registro requerido, aprobación en 24–48h)

PERO hay un problema crítico para Colombia:
O*NET usa clasificación SOC (Standard Occupational Classification) de EE.UU. No tiene datos de empleo colombiano. Las ofertas, salarios y demanda que reporta son del mercado norteamericano.

Veredicto: Úsalo ÚNICAMENTE como framework de taxonomía de competencias (tiene la mejor base de datos de skills del mundo con 277 ocupaciones y 35,000+ habilidades catalogadas). No lo uses como fuente de demanda laboral para Colombia.

Alternativa colombiana equivalente: CNO (Clasificación Nacional de Ocupaciones) del SENA/Ocupacol — esta sí es la fuente autoritativa para el contexto local.

LinkedIn Scraping — ¿Viable o riesgoso? ¿Alternativas legales?
Es riesgoso y no recomendado. LinkedIn prohíbe explícitamente el scraping en sus ToS. Los riesgos concretos son: bloqueo de IPs, suspensión de cuentas universitarias, potencial carta legal.

El caso hiQ Labs vs. LinkedIn (EE.UU.) protegió el scraping de datos públicos, pero esa protección no aplica en Colombia bajo la Ley 1581 de Protección de Datos.

Herramientas que propones — evaluación real:

Herramienta	Costo	Viabilidad para este proyecto	Veredicto
Apify	$49–$299/mes	Razonable para job boards públicos. Para LinkedIn: riesgo de bloqueo	Usar solo para fuentes legales
Bright Data	$500–$3,000+/mes	Inviable para presupuesto universitario	Descártalo
Coresignal	$500–$2,000+/mes	Idem, enterprise pricing	Descártalo
Alternativas legales reales para datos de empleo en Colombia:

Computrabajo.com: El mayor job board de Colombia y Latam. Datos públicos de ofertas laborales. Scraping de páginas de resultados es técnicamente factible (no tienen API, revisar ToS periódicamente).
Elempleo.com: Segundo mayor job board colombiano. Mismo enfoque.
Adzuna API: Tiene API abierta y gratuita, incluye Colombia. Esta es la joya escondida del proyecto.
Google Jobs vía SerpAPI: ~$50/mes, extrae datos de Google Jobs (que agrega Indeed, LinkedIn, Glassdoor, etc.) — excelente relación costo-beneficio.
APIs de Empleo — Evaluación honesta
API	¿Existe?	¿Gratuita?	¿Datos Colombia?	Veredicto
Indeed	API cerrada a terceros desde 2021	N/A	No disponible para proyectos independientes	Descartado
Glassdoor	Solo enterprise	No	Mínima	Descartado
Adzuna	Sí, abierta	Sí (tier gratuito)	Sí	Usar
Jooble	Sí	Sí (limitada)	Sí	Usar como complemento
SerpAPI (Google Jobs)	Sí	$50/mes	Sí (agrega todo)	Usar si hay presupuesto
Datasets en Colombia — ¿Cuáles sí sirven?
Los que SÍ sirven y son automatizables:

Fuente	Qué tiene	Acceso	Frecuencia
DANE – GEIH	Empleo, desempleo, salarios por sector/ocupación	Archivos CSV/microdata gratis	Mensual
OLE (Observatorio Laboral para la Educación)	Tasa de empleo de graduados colombianos POR CARRERA y universidad	Portal con descarga	Anual
Servicio Público de Empleo (SPE)	Ofertas laborales activas del SENA	API REST (con registro)	Tiempo real
Banco de la República	Indicadores económicos, sectores	API/CSV gratis	Mensual/trimestral
MinTrabajo – PILA	Cotizantes por sector, salarios formales	Informes públicos	Mensual
Ocupacol	Clasificación nacional de ocupaciones	Descarga gratuita	Actualización periódica
SENA – Datos abiertos	Demanda de formación, cursos más solicitados	datos.gov.co	Variable
Los que NO son automatizables (solo PDFs manuales):

World Economic Forum (informe Future of Jobs): PDF anual — procesar con LLM/OCR
McKinsey Reports: PDF, sin API — idem
Hays Salary Guide Colombia: PDF anual — idem
1. VALIDACIÓN DEL ENFOQUE
Lo que está bien
La estructura de 3 bloques (APIs, scraping, datos no estructurados) es correcta conceptualmente
Identificar el problema central de los Excel manuales como el dolor principal
La idea del miniagente con Claude ya existente es un activo subutilizado que se puede escalar
Pensar en fases (0–4) es el enfoque correcto
Lo que está mal
Depender de LinkedIn scraping como fuente primaria — riesgo legal y técnico inaceptable
Ignorar el OLE (Observatorio Laboral para la Educación del MEN) — es la fuente más relevante para una universidad colombiana y la tienen completamente invisible
Ignorar DANE-GEIH — es gratuita, oficial y tiene exactamente los datos que necesitan
Bright Data y Coresignal son enterprise tools diseñadas para corporativos con presupuestos de miles de dólares mensuales — están fuera del alcance realista
Lo que cambiaría
Priorizar fuentes colombianas oficiales (DANE, OLE, SPE, Ocupacol) sobre fuentes internacionales scrapeadas
Usar el miniagente Claude existente para procesar PDFs de WEF/McKinsey en lugar de OCR genérico
Construir primero el modelo de datos, luego las integraciones — el error más común es invertir este orden
Diseñar para sostenibilidad operativa: un sistema que nadie de la universidad pueda mantener es inútil
2. ARQUITECTURA PROPUESTA (MEJORADA)

┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE INGESTA                              │
│                                                                 │
│  APIs Estructuradas    Scraping Controlado    Procesamiento PDF │
│  ─────────────────     ──────────────────     ───────────────── │
│  • DANE GEIH           • Computrabajo         • Claude API      │
│  • OLE (MEN)           • Elempleo             • WEF, McKinsey   │
│  • SPE/SENA API        • Noticias sectorial   • Hays, Deloitte  │
│  • Adzuna API          • Ocupacol web         • Reportes MinTrab│
│  • Banco República     • Google Jobs          • Excels actuales │
│  • O*NET (skills)      • (vía SerpAPI)                         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PROCESAMIENTO                        │
│                                                                 │
│  Orquestador (Apache Airflow / GitHub Actions)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ ETL Python  │  │ NLP/Skills   │  │ Calidad de datos     │   │
│  │ • Limpieza  │  │ extracción   │  │ • Duplicados         │   │
│  │ • Normaliz. │  │ (spaCy +     │  │ • Completitud        │   │
│  │ • Mapeo CNO │  │  Claude API) │  │ • Consistencia       │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE ALMACENAMIENTO                       │
│                                                                 │
│  PostgreSQL (datos estructurados)                               │
│  ├── schema: raw        (datos crudos sin procesar)             │
│  ├── schema: curated    (datos limpios y normalizados)          │
│  ├── schema: analytics  (agregaciones, indicadores)             │
│  └── schema: audit      (log de fuentes, calidad, cobertura)   │
│                                                                 │
│  Almacenamiento de archivos (S3 / Google Drive)                 │
│  └── PDFs, Excels originales, reportes procesados              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE VISUALIZACIÓN                        │
│                                                                 │
│  Apache Superset (open source, gratuito)                        │
│  ├── Panel Ejecutivo                                            │
│  ├── Panel por Carrera                                          │
│  ├── Panel de Mercado Laboral                                   │
│  └── Panel de Auditoría de Fuentes                             │
│                                                                 │
│  + Alertas automáticas vía email/Slack                         │
└─────────────────────────────────────────────────────────────────┘
3. PLAN DE IMPLEMENTACIÓN
Fase 0: Diagnóstico (Semanas 1–2)
Objetivo: Entender qué existe antes de construir nada.

Inventario de todos los archivos Excel actuales (estructura, campos, fechas, fuentes)
Evaluación de calidad: ¿qué porcentaje de campos están completos? ¿hay consistencia entre archivos?
Identificación de variables actuales y sus definiciones (¿"salario" es bruto o neto? ¿mensual o anual?)
Mapa de stakeholders: ¿quién usa estos datos y para qué decisiones concretas?
Evaluación del miniagente Claude existente: ¿qué hace exactamente? ¿qué produce?
Definición del glosario de términos del observatorio
Entregable: Informe de diagnóstico + inventario de fuentes actuales + glosario base

Fase 1: Estructuración (Semanas 3–5)
Objetivo: Construir el modelo de datos antes de conectar cualquier fuente.

Diseño del modelo de datos relacional (esquemas, tablas, relaciones)
Definición de variables estándar comparables (ver sección 4)
Migración y limpieza de Excel históricos a PostgreSQL
Mapeo de ocupaciones históricas al CNO (Clasificación Nacional de Ocupaciones)
Definición de criterios de inclusión/exclusión de fuentes
Entregable: Base de datos poblada con datos históricos + diccionario de datos

Estructura de tablas base:


-- Tabla de ocupaciones (normalizada contra CNO)
ocupaciones (id, nombre, codigo_cno, codigo_onet, sector, nivel)

-- Tabla de competencias
competencias (id, nombre, tipo[técnica/blanda/digital], taxonomia_onet)

-- Tabla de fuentes
fuentes (id, nombre, tipo, url, frecuencia, confiabilidad, activa, ultima_actualizacion)

-- Tabla de registros laborales
registros_laborales (id, fuente_id, ocupacion_id, fecha, salario_min, salario_max, 
                     ubicacion, modalidad[presencial/remoto/hibrido], tipo_contrato,
                     nivel_educativo, experiencia_requerida)

-- Tabla de competencias por registro
registro_competencias (registro_id, competencia_id, frecuencia_mencion)

-- Tabla de auditoría
auditoria_fuentes (id, fuente_id, fecha_revision, estado, registros_obtenidos, 
                   cobertura_pct, notas)
Fase 2: Integración de Fuentes (Semanas 6–10)
Objetivo: Conectar fuentes en orden de viabilidad técnica y valor estratégico.

Orden de integración recomendado (de mayor a menor viabilidad):

DANE GEIH — descarga de microdata, procesamiento con Python pandas
OLE (Observatorio Laboral para la Educación) — scraping del portal o descarga de reportes
Adzuna API — integración directa con API REST (gratuita)
SPE/SENA — API con registro previo
Computrabajo y Elempleo — scraping de páginas de resultados (Python + BeautifulSoup/Playwright)
PDFs de reportes (WEF, McKinsey, Hays) — pipeline con Claude API para extracción estructurada
Banco de la República — descarga automática de series estadísticas
Entregable: Pipelines ETL funcionando + inventario maestro de fuentes actualizado

Fase 3: Desarrollo del Sistema (Semanas 11–16)
Objetivo: MVP funcional del observatorio.

Configuración del servidor (Railway, Render, o servidor universitario)
Despliegue de PostgreSQL + Apache Superset
Construcción de dashboards MVP (ver sección 6)
Configuración de Airflow para automatización de pipelines
Sistema de alertas por email
Documentación técnica para el equipo de la universidad
Entregable: Observatorio MVP en producción

Fase 4: Validación y Despliegue (Semanas 17–20)
Objetivo: Validar con usuarios y estabilizar.

Pruebas de calidad de datos con el equipo de Alumni
Validación de insights con la Dirección Académica
Ajuste de dashboards según feedback
Capacitación al equipo responsable
Definición de SLAs de actualización
Puesta en producción oficial
4. VARIABLES E INDICADORES (MEJORADOS)
Variables base (ya identificadas)
Competencias técnicas y blandas (skills)
Salarios (bruto mensual, por nivel, por sector)
Programas académicos más solicitados
Sectores económicos
Variables adicionales que agregan valor estratégico real
Empleabilidad:

Tasa de inserción laboral (% graduados empleados a 6, 12 y 24 meses) — dato directo del OLE
Tiempo promedio hasta el primer empleo (meses desde grado)
Tasa de adecuación ocupacional (% trabajando en área afín a su carrera)
Índice de desajuste educativo (sobre/subcualificación por programa)
Mercado laboral:

Volumen de ofertas activas por ocupación (número de vacantes)
Relación oferta/demanda de candidatos por ocupación
Distribución por modalidad (100% remoto, híbrido, presencial)
Distribución por tipo de contrato (indefinido, temporal, prestación de servicios, freelance)
Distribución por tamaño de empresa (startup, PYME, grande, multinacional)
Tendencias y evolución:

Velocidad de crecimiento de menciones de habilidades (YoY %)
Half-life estimado de competencias técnicas (cuánto tiempo sigue siendo relevante una skill)
Skills emergentes (nuevas en los últimos 6 meses)
Skills en declive (frecuencia cayendo más del 20% YoY)
Certificaciones complementarias más mencionadas en ofertas
Brechas estratégicas:

Brecha de género: diferencia salarial y acceso por carrera
Brecha geográfica: empleabilidad Bogotá vs. resto del país
Concentración sectorial: % egresados de cada carrera concentrados en menos de 3 sectores (riesgo)
Índice de diversificación de egresados por carrera
Calidad y contexto:

Salario real vs. salario esperado según encuesta de egresados
NPS de empleabilidad (satisfacción de egresados con su trayectoria laboral)
5. SISTEMA DE FUENTES
Clasificación realista por nivel de confiabilidad y automatización

NIVEL 1: Alta confiabilidad + Alta automatización ✅✅✅
──────────────────────────────────────────────────────
• DANE - GEIH                    │ Oficial gubernamental │ Mensual
• OLE (MEN)                      │ Oficial universitario │ Anual/Semestral
• Banco de la República           │ Banco central         │ Mensual
• MinTrabajo - datos PILA         │ Oficial gubernamental │ Mensual
• SPE/SENA                        │ Gubernamental         │ Tiempo real

NIVEL 2: Alta confiabilidad + Automatización media ✅✅
──────────────────────────────────────────────────────
• Adzuna API                      │ Privado open API      │ Diario
• Computrabajo (scraping)         │ Privado               │ Semanal
• Elempleo (scraping)             │ Privado               │ Semanal
• O*NET Web Services              │ Gubernamental EE.UU.  │ Semestral
• Google Jobs via SerpAPI         │ Agregador             │ Diario

NIVEL 3: Alta confiabilidad + Solo manual/LLM ✅
──────────────────────────────────────────────────────
• World Economic Forum            │ Internacional         │ Anual
• McKinsey Global Institute       │ Consultora            │ Irregular
• Hays Salary Guide Colombia      │ Consultora RRHH       │ Anual
• Deloitte Human Capital Trends   │ Consultora            │ Anual
• ANDI, Fedesarrollo              │ Gremial/Think tank    │ Variable

NIVEL 4: Baja confiabilidad o inviable ❌
──────────────────────────────────────────────────────
• LinkedIn (scraping directo)     │ Riesgo legal          │ N/A
• Glassdoor API                   │ Solo enterprise       │ N/A
• Indeed API                      │ Cerrada               │ N/A
• Bright Data / Coresignal        │ Inviable por costo    │ N/A
Criterios de inclusión de fuentes
Criterio	Peso
Cobertura Colombia / programa específico	30%
Frecuencia de actualización	25%
Confiabilidad metodológica	25%
Viabilidad de automatización	20%
6. DASHBOARD — PROPUESTA CLARA
Panel 1: Ejecutivo (Rectores, Vicerrectores, Decanos)

┌─────────────────────────────────────────────────────┐
│  OBSERVATORIO LABORAL – Universidad de La Sabana    │
│  Actualizado: 03/05/2026                            │
├────────────┬────────────┬────────────┬──────────────┤
│ Tasa empleo│ Salario    │ Vacantes   │ Skills       │
│ egresados  │ promedio   │ activas    │ emergentes   │
│   87.3%    │ $4.2M COP  │  12,450    │   +23 nuevas │
│  ▲ +2.1%   │  ▲ +5.4%   │  ▼ -3.2%  │  este mes    │
├────────────┴────────────┴────────────┴──────────────┤
│  MAPA DE CALOR: Empleabilidad por Facultad          │
│  [Tabla con semáforo: rojo/amarillo/verde]          │
├─────────────────────────────────────────────────────┤
│  TOP 10 SKILLS MÁS DEMANDADAS (Colombia)           │
│  [Gráfico de barras horizontales con tendencia]     │
├─────────────────────────────────────────────────────┤
│  ALERTAS ESTRATÉGICAS                               │
│  ⚠ Ingeniería Industrial: brecha de habilidades    │
│    digitales detectada (+40% menciones IA)          │
│  ⚠ Psicología: crecimiento en salud mental digital │
│  ✅ Derecho: mayor inserción laboral en 3 años      │
└─────────────────────────────────────────────────────┘
Panel 2: Por Carrera (Directores de programa)
Mapa de calor skills requeridas vs. skills enseñadas (brecha curricular)
Evolución salarial de egresados del programa (comparado con el promedio nacional)
Sectores más frecuentes de inserción
Top empresas empleadoras de egresados de esa carrera
Tendencia de vacantes para ese perfil (últimos 24 meses)
Certificaciones complementarias más valoradas
Panel 3: Tendencias de Mercado
Gráfico de líneas: evolución de menciones de top 20 skills (12 meses)
Mapa de calor sectorial: crecimiento/contracción por industria
Comparativo salarios Colombia vs. región (cuando haya dato)
Nuevas ocupaciones emergentes (aparecieron en últimos 6 meses)
Ocupaciones en declive (caída sostenida de vacantes)
Panel 4: Auditoría de Fuentes (Equipo operativo)
Estado de cada fuente: activa / inactiva / con errores
Última actualización exitosa por fuente
Número de registros por fuente
Indicador de cobertura general del sistema (%)
Fuentes nuevas identificadas pendientes de evaluación
Log de errores de ingesta
Sistema de Alertas
Trigger	Canal	Destinatario
Nueva skill aparece +50 menciones/semana	Email	Director de programa
Fuente sin actualizar +72h	Email	Equipo técnico
Salario promedio varía >10% un mes	Dashboard alert	Panel ejecutivo
Nueva ocupación detectada (no existe en BD)	Email	Equipo Alumni
Fuente deja de estar disponible	Email	Equipo técnico
7. SISTEMA DE AUDITORÍA
Inventario maestro de fuentes
Cada fuente en el sistema tiene un registro en la tabla fuentes con:

Estado: activa, pausada, descontinuada, en_evaluacion
Frecuencia esperada de actualización
Fecha de última actualización exitosa
Porcentaje de campos completos en su última ingesta
Score de confiabilidad (1–5, calculado automáticamente)
Detección de nuevas fuentes
Estrategia automatizada:

Monitor semanal de Google Alerts configurado para: "mercado laboral Colombia" + "informe" + "2026"
Monitor de publicaciones del DANE, MinTrabajo y OLE (RSS feeds donde existan)
Revisión trimestral manual de fuentes internacionales (WEF calendar, McKinsey publication schedule)
Pipeline de Claude API que analiza los nuevos documentos detectados y determina si son relevantes
Estrategia manual:

Revisión semestral con panel de expertos de la universidad
Encuesta anual a empleadores frecuentes de egresados (¿qué fuentes de información usan?)
Indicadores de calidad del sistema
Indicador	Meta	Frecuencia de medición
Cobertura de fuentes activas	> 90%	Semanal
Completitud de registros	> 85%	Mensual
Frecuencia de actualización cumplida	> 95%	Mensual
Duplicados detectados y eliminados	< 2%	Mensual
Tiempo desde publicación hasta ingesta	< 7 días (automático) / < 30 días (manual)	Por evento
8. INSIGHTS ESTRATÉGICOS (MÍNIMO 5)
El sistema debe generar automáticamente estos análisis:

Insight 1: Brecha curricular crítica
Cruzar las top 20 skills demandadas en ofertas laborales para egresados de cada programa con el plan de estudios actual. Resultado: lista priorizada de competencias que la universidad NO está enseñando pero el mercado SÍ está exigiendo. Acción directa: actualización curricular.

Insight 2: Programas en riesgo de obsolescencia
Programas cuyos egresados muestran simultáneamente: (a) aumento del tiempo para conseguir primer empleo, (b) caída en salario relativo al promedio, y (c) reducción de vacantes para su perfil. Estos son los programas que necesitan intervención urgente.

Insight 3: Nuevas carreras o especializaciones viables
Clusters de skills emergentes que aparecen juntos frecuentemente en ofertas pero no corresponden a ningún programa existente. Ejemplo detectado en el mercado colombiano actual: "Data Governance + ESG Reporting + Regulación financiera" — ninguna carrera de pregrado lo enseña integradamente.

Insight 4: Concentración sectorial como riesgo
Si el 70% de egresados de una carrera va al mismo sector, un shock sectorial (como ocurrió con banca en 2020 o petróleo en 2015) puede generar una crisis de empleabilidad. El sistema identifica estas concentraciones y propone diversificación.

Insight 5: Retorno de inversión educativa por programa
Cruzar costo de la matrícula vs. salario promedio de egresados a 24 meses vs. tiempo hasta primer empleo. Genera un índice de retorno educativo que puede usarse tanto para asesorar estudiantes como para posicionar programas ante el mercado.

Insight 6: Skills con mayor crecimiento no cubiertos por certificaciones
Identificar competencias técnicas en alto crecimiento donde los egresados de La Sabana no tienen ventaja competitiva, y que podrían cubrirse con certificaciones cortas o cursos de extensión (nueva línea de negocio para la universidad).

Insight 7: Brechas de género estructurales
Por carrera y sector: diferencia salarial, diferencia en tiempo de inserción, y sectores donde la brecha es más pronunciada. Esto tiene valor tanto estratégico como de posicionamiento institucional.

9. STACK TECNOLÓGICO SUGERIDO
Diseñado para ser sostenible por un equipo universitario sin presupuesto de empresa tecnológica:

Capa	Herramienta	Costo	Justificación
Lenguaje base	Python 3.11+	Gratuito	Ecosistema de datos más completo
ETL / Scraping	Scrapy + Playwright	Gratuito	Scraping robusto para webs dinámicas
Procesamiento PDF/IA	Claude API (claude-sonnet-4-6)	Pay-per-use (~$3/1M tokens)	Ya lo usan, escalarlo
NLP / Skills extraction	spaCy + Claude API	Gratuito + pay-per-use	Mejor combinación costo-calidad
Orquestación	GitHub Actions (simple) → Airflow (escala)	Gratuito → $20/mes	Empezar simple, migrar cuando crezca
Base de datos	PostgreSQL	Gratuito	Robusto, soporte amplio, open source
Hosting BD	Supabase (gratis hasta 500MB) o Railway	Gratis/$5 mes	Fácil de administrar
Dashboard	Apache Superset	Gratuito	Mejor opción open source para BI
Hosting app	Railway o Render	$5–$20/mes	Más simple que AWS para este caso
Monitoreo	Grafana + Prometheus	Gratuito	Alertas de salud del sistema
Control de versiones	GitHub	Gratuito	Versionamiento de código y pipelines
Documentación	Notion o Confluence	Gratis/pagado	Ya probablemente lo usan
Costo mensual estimado en operación: $50–$150 USD/mes (hosting + APIs)

10. CRONOGRAMA REALISTA

CORTO PLAZO (0–3 meses)
┌──────────────────────────────────────────────────────────────┐
│ Mes 1: Diagnóstico + modelo de datos + migración de Excel    │
│ Mes 2: Integración DANE, OLE, SPE, Adzuna (fuentes tier 1)  │
│ Mes 3: MVP Dashboard (3 paneles básicos) + pruebas internas  │
└──────────────────────────────────────────────────────────────┘

MEDIANO PLAZO (4–6 meses)
┌──────────────────────────────────────────────────────────────┐
│ Mes 4: Integración Computrabajo + Elempleo (scraping)        │
│ Mes 5: Pipeline de PDFs con Claude API (WEF, McKinsey, Hays) │
│ Mes 6: Sistema de alertas + panel de auditoría + capacitación│
└──────────────────────────────────────────────────────────────┘

LARGO PLAZO (7–12 meses)
┌──────────────────────────────────────────────────────────────┐
│ Mes 7–8: Motor de insights automatizados con Claude API      │
│ Mes 9–10: Integración de encuesta de egresados al sistema    │
│ Mes 11–12: Versión 2.0 con ML predictivo (skills forecast)   │
└──────────────────────────────────────────────────────────────┘
FUNCIONAMIENTO DEL OBSERVATORIO (FLUJO OPERACIONAL)

CAPTURA → TRANSFORMACIÓN → ALMACENAMIENTO → VISUALIZACIÓN → DECISIÓN

Fuente se actualiza
        │
        ▼
Pipeline Python se activa (Airflow/GitHub Actions)
        │
        ├── Si API: llamada REST → JSON → normalización → PostgreSQL
        ├── Si scraping: Playwright → HTML → parse → normalización → PostgreSQL
        └── Si PDF: descarga → Claude API → JSON estructurado → normalización → PostgreSQL
                │
                ▼
        Validaciones de calidad automáticas
        (duplicados, rangos, completitud)
                │
                ▼
        Carga en schema: curated
                │
                ▼
        Actualización de agregaciones (analytics schema)
                │
                ▼
        Superset refresca dashboards
                │
                ▼
        Alertas si hay cambios relevantes
                │
                ▼
        Director/Decano recibe email o ve dashboard
                │
                ▼
        Decisión académica (curricular, nueva carrera, etc.)
Frecuencias de actualización por tipo de fuente:

Tipo	Frecuencia
APIs de ofertas laborales (Adzuna, SPE)	Diaria
Scraping de job boards (Computrabajo, Elempleo)	Semanal
DANE GEIH	Mensual (al publicarse)
Reportes PDF (WEF, McKinsey)	Al detectar nueva publicación
OLE (MEN)	Semestral/Anual
ESTRATEGIA DE MANTENIMIENTO
Roles y responsabilidades:

Rol	Dedicación	Responsabilidad
Analista de datos (1 persona)	4h/semana	Revisión de calidad, actualización de fuentes manuales, generación de informes
Desarrollador/estudiante practicante	20h/semana	Mantenimiento de pipelines, corrección de errores, nuevas integraciones
Líder del observatorio (Alumni)	2h/semana	Validación de insights, comunicación con facultades
Control de calidad:

Revisión mensual de logs de ingesta (¿qué fuentes fallaron?)
Auditoría trimestral de cobertura (¿hay fuentes nuevas que deberíamos incluir?)
Revisión semestral del modelo de datos (¿hay nuevas variables estratégicamente relevantes?)
Backup automático diario de base de datos
DIAGRAMA DE ARQUITECTURA SIMPLIFICADO

┌──────────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                             │
│  ┌──────┐ ┌──────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ DANE │ │ OLE  │ │  Adzuna  │ │Computrab.│ │ PDFs (WEF/McK.)  │  │
│  │ GEIH │ │ MEN  │ │   API    │ │ Elempleo │ │ vía Claude API   │  │
│  └──┬───┘ └──┬───┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
└─────┼────────┼──────────┼────────────┼────────────────┼────────────┘
      │        │          │            │                │
      └────────┴──────────┴────────────┴────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│              PIPELINE ETL (Python + Airflow)                        │
│         Extracción → Limpieza → Normalización → Carga               │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│           POSTGRESQL (Supabase/Railway)                              │
│   schema:raw │ schema:curated │ schema:analytics │ schema:audit     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                          ┌────────┴────────┐
                          │                 │
                          ▼                 ▼
              ┌─────────────────┐  ┌────────────────┐
              │ Apache Superset │  │ Alertas Email  │
              │   Dashboards    │  │ (SMTP/Slack)   │
              └────────┬────────┘  └────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Usuarios:     │
              │  • Rectores    │
              │  • Decanos     │
              │  • Directores  │
              │  • Alumni      │
              └────────────────┘
CONCLUSIÓN EJECUTIVA
El proyecto es técnicamente viable con el stack propuesto. El mayor riesgo no es técnico sino operativo: si no se asigna al menos una persona con dedicación parcial para el mantenimiento, el sistema se deteriora en 6 meses.

Los tres elementos más críticos para el éxito son:

Priorizar OLE y DANE como fuentes core — son gratuitas, oficiales y tienen exactamente lo que la universidad necesita
Abandonar LinkedIn scraping y Bright Data/Coresignal como ideas — reemplazarlos con Adzuna API + Computrabajo/Elempleo scraping + Google Jobs vía SerpAPI
Escalar el miniagente Claude existente para procesamiento de PDFs — es el activo más subutilizado que ya tienen
La diferencia entre este observatorio y los Excel manuales no es solo tecnología: es pasar de datos que describen el pasado a un sistema que anticipa el futuro.

Propuesta elaborada para: Reto de Aprendizaje Experiencial – Dirección de Alumni, Universidad de La Sabana
Fecha: 03/05/2026