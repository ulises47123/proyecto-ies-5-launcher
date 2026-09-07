# PROYECTO ACADÉMICO Y TÉCNICO INTEGRAL: CAMPUS VIRTUAL IES N° 5 " JOSÉ EUGENIO TELLO\ — SUITE DE ESCRITORIO Y LAUNCHER

---

## 1. PORTADA Y METADATOS DEL PROYECTO

- **Título Completo del Proyecto:** Suite de Escritorio, Launcher y Cliente Nativo Integrado para el Campus Virtual del Instituto de Educación Superior N° 5 \José Eugenio Tello\.
- **Área de Conocimiento / Disciplina:** Ingeniería de Software, Sistemas Distribuidos, Interacción Persona-Ordenador (HCI), Seguridad Informática, Web Scraping Ético, Procesamiento de Lenguaje Natural (NLP) y Visión por Computadora (OCR).
- **Nivel Académico / Profesional Esperado:** Proyecto Final Integrador / Nivel Profesional de Grado y Tecnicatura Superior en Desarrollo de Software y Administración de Redes y Sistemas.
- **Institución Destinataria:** Instituto de Educación Superior N° 5 \José Eugenio Tello\ (San Salvador de Jujuy, Argentina), en articulación con la infraestructura del Instituto Nacional de Formación Docente (INFD).
- **Fecha de Elaboración:** Septiembre de 2026.
- **Versión del Documento:** 3.5.0 (Producción / Release Candidate).

---

## 2. RESUMEN EJECUTIVO

El presente proyecto constituye una plataforma integral de software cliente de escritorio orientada a superar las limitaciones de usabilidad, latencia y fragmentación informativa que experimentan los estudiantes y docentes al interactuar con el campus virtual del IES N° 5 \José Eugenio Tello\ (alojado en la plataforma INFD).

A diferencia del acceso web tradicional mediante navegadores generales, esta suite cliente nativa, desarrollada en Python 3.11+ con una interfaz gráfica basada en CustomTkinter, integra de forma sinérgica la totalidad de las fuentes de información de la vida institucional:
1. **El Aula Virtual Oficial (/aula/):** Acceso a programas de cátedra, unidades didácticas jerárquicas, visualización de actividades con semaforización de estados de entrega, descarga de materiales bibliográficos, visualización de calificaciones estructuradas y webmail interno.
2. **Chat en Tiempo Real:** Integración directa mediante endpoints REST con la base de datos distribuida de Firebase Firestore utilizada por el campus, permitiendo leer y enviar mensajes de debate por cátedra de manera instantánea.
3. **Sitio Informativo Público (/sitio/):** Motor de indexación y búsqueda que rastrea artículos de noticias, calendarios, partes de prensa y descarga documentos PDF públicos, extrayendo automáticamente su texto mediante análisis sintáctico de flujos binarios zlib sin dependencias pesadas.
4. **Comunidad en Redes Sociales (Facebook Institucional):** Módulo de sincronización de comunicados públicos con soporte de Visión por Computadora y Reconocimiento Óptico de Caracteres (OCR mediante Tesseract), permitiendo que avisos institucionales publicados como imágenes o placas informativas sean indexados y buscables en texto plano.
5. **Seguridad Nativa con DPAPI:** Cifrado de credenciales del alumno, tokens de sesión y claves de API delegados a la API criptográfica nativa de Windows (CryptProtectData).
6. **Asistente Pedagógico Híbrido:** Asistente conversacional con animación de tipeo que responde de forma inmediata consultas sobre materias, docentes, progreso, actividades pendientes, noticias y resoluciones utilizando las bases de datos locales cacheadas, con capacidad de conectarse a Google Gemini y OpenAI GPT.

---

## 3. FILOSOFÍA Y PRINCIPIOS RECTORES DEL PROYECTO

### 3.1 Filosofía Central
El proyecto postula que **el software educativo debe garantizar un acceso transparente, equitativo y sin fricciones a la información académica**, eliminando barreras técnicas para que los estudiantes dediquen su tiempo y recursos cognitivos al aprendizaje genuino.

### 3.2 Principios Rectores
1. **Soberanía y Seguridad del Usuario (Zero-Trust Local):** Ningún dato confidencial (DNI, contraseña, cookies o claves de API) se transmite a servidores de terceros ni se almacena en texto plano. Todo dato sensible se encripta en el almacenamiento local con Windows DPAPI.
2. **Concurrencia Asíncrona Total:** Todas las peticiones HTTP/HTTPS, descargas de archivos, parseos de PDF y ejecuciones de OCR corren en hilos secundarios desacoplados del bucle de eventos de la interfaz gráfica ( hreading), asegurando una respuesta de 60 FPS sin congelamientos.
3. **Resiliencia y Operación Offline:** Implementación de capas de persistencia en JSON (cache_materias.json, cache_contactos.json, cache_sitio_informativo.json, cache_facebook.json, user_cache.json). El usuario puede consultar contenidos, programas, contactos y novedades aun sin conexión a internet.
4. **Ergonomía y Accesibilidad:** Selector de 8 temas visuales optimizados (Azul clásico, Turquesa, Púrpura, Neón, Esmeralda, Ámbar, Oliva y Modo Claro), con soporte para selección de texto en todas las vistas de lectura.
5. **Monitoreo Proactivo y Pasivo:** Residencia en segundo plano mediante la bandeja del sistema (*System Tray* con pystray), comprobando novedades reales cada $ minutos y emitiendo notificaciones nativas de Windows Toast.

---

## 4. OBJETIVO GENERAL

Desarrollar, estructurar e implementar una aplicación cliente de escritorio de alto rendimiento en Python para la comunidad del IES N° 5 \José Eugenio Tello\, que centralice y automatice la autenticación criptográfica, la navegación curricular, la mensajería interna, el chat en tiempo real de cátedra, la indexación del sitio web público y redes institucionales (con OCR), y la asistencia pedagógica con IA en un entorno visual unificado.

---

## 5. OBJETIVOS ESPECÍFICOS

1. **Seguridad y Persistencia Criptográfica:** Integrar Windows DPAPI (config.py) para el cifrado y descifrado seguro de credenciales del aula, cookies de sesión y tokens de APIs en el perfil local del usuario (~/.campus_tello/).
2. **Gestión de Sesión y Resiliencia de Red:** Desarrollar ackend/session.py con políticas de reconexión automática mediante adaptadores HTTPAdapter de equests, con 3 reintentos exponenciales y validación ligera contra escritorio.cgi.
3. **Extracción Curricular y Clasificación de Contenidos:** Construir en ackend/programa.py y ackend/escritorio.py analizadores DOM con BeautifulSoup4 capaces de procesar jerarquías de unidades, distinguir actividades reales de bloques informativos de \Contenido relacionado\ y semaforizar estados (Entregada 🟢, Pendiente 🟠, Cerrada 🔴).
4. **Comunicaciones Integradas (Webmail y Firebase Chat):** Implementar en ackend/mensajes.py y ackend/cache_utils.py el acceso al correo institucional y la interacción REST con Firebase Firestore para mensajería instantánea de cátedra.
5. **Indexación Externa y Visión por Computadora (OCR):** Desarrollar ackend/sitio_informativo.py (con parser de streams PDF zlib) y ackend/facebook_scraper.py (con pytesseract y PIL) para incorporar comunicados oficiales y resoluciones al motor de búsqueda.
6. **Asistente Virtual Contextual:** Construir en ia/engine.py un motor híbrido que responda consultas locales en milisegundos mediante coincidencia de patrones y proporcione puente opcional a Google Gemini y OpenAI.

---

## 6. JUSTIFICACIÓN Y CONTEXTUALIZACIÓN

### 6.1 Problemática Identificada
- **Fricción en Autenticación:** La plataforma INFD cierra sesiones por inactividad tras lapsos breves, obligando a reescribir credenciales repetidamente.
- **Dispersión Informativa:** Las noticias académicas se reparten entre el aula virtual, el sitio web institucional (/sitio/) y las redes sociales (Facebook), dificultando que el estudiante se entere oportunamente de fechas de exámenes, becas o suspensiones de actividades.
- **Comunicados en Formato Gráfico:** Gran parte de las resoluciones se publican como imágenes o volantes en redes sociales, impidiendo la búsqueda de texto.

### 6.2 Solución Aportada
La suite consolida todas estas fuentes en una base de datos local unificada, extrae el texto de imágenes mediante OCR y de PDFs mediante parsing binario, y presenta todo el ecosistema académico en un único panel con notificaciones de escritorio en tiempo real.

---

## 7. ALCANCE Y LÍMITES DEL PROYECTO

### 7.1 Dentro del Alcance (In Scope)
- Autenticación segura y autologin con Windows DPAPI y persistencia de cookies.
- Mapeo completo de materias, unidades, actividades, calificaciones y contactos (con fotos, correos y exportación a CSV).
- Envío y recepción de mensajes de Webmail y chat general de Firebase por materia.
- Visor y descargador de archivos con preservación estricta de nombres y extensiones reales.
- Scraping e indexación del sitio web público y extracción de texto de PDFs.
- Scraping de Facebook institucional con extracción de imágenes y OCR local.
- Asistente IA local con animaciones de tipeo y soporte opcional de Gemini/OpenAI.
- Modo System Tray con temporizador configurable y notificaciones Toast nativas.

### 7.2 Fuera del Alcance (Out of Scope)
- Edición de bases de datos centrales de alumnos en los servidores del INFD.
- Compilación nativa para dispositivos móviles Android/iOS (el alcance es entornos de escritorio Windows 10 / 11).

---

## 8. DESCRIPCIÓN DETALLADA DE LA ARQUITECTURA Y MÓDULOS

`
┌─────────────────────────────────────────────────────────────────────────┐
│ CAPA DE PRESENTACIÓN (UI) │
│ main.py │ ui/main_view.py │ ui/curso_detail.py │ ui/login.py │ widgets │
└────────────────────────────────────┬────────────────────────────────────┘
 │
┌────────────────────────────────────▼────────────────────────────────────┐
│ CAPA DE CONTROL Y ASISTENCIA │
│ ia/engine.py (Motor IA Local + Gemini / OpenAI API) │
│ config.py (Ajustes, 8 Temas, Cifrado DPAPI, Rutas) │
└────────────────────────────────────┬────────────────────────────────────┘
 │
┌────────────────────────────────────▼────────────────────────────────────┐
│ CAPA DE BACKEND, SCRAPING Y RED │
│ • backend/session.py: Gestión HTTP requests con reintentos y cookies │
│ • backend/escritorio.py: Parseo de cursos, avances y novedades │
│ • backend/programa.py: Árbol de unidades, actividades y entregas │
│ • backend/calificaciones.py: Evaluaciones, notas y observaciones │
│ • backend/mensajes.py: Webmail interno y adjuntos │
│ • backend/contactos.py: Docentes, compañeros, perfiles y export CSV │
│ • backend/cache_utils.py: Firebase Chat REST y gestor de cachés JSON │
│ • backend/sitio_informativo.py: Scraper del sitio público + Parser PDF │
│ • backend/facebook_scraper.py: Scraper de Facebook + OCR Tesseract │
│ • backend/user.py: Normalización dinámica del perfil del estudiante │
└────────────────────────────────────┬────────────────────────────────────┘
 │
┌────────────────────────────────────▼────────────────────────────────────┐
│ FUENTES EXTERNAS Y SERVICIOS │
│ INFD (/aula/ y /sitio/) │ Firebase Firestore │ Facebook │ Google AI │
└─────────────────────────────────────────────────────────────────────────┘
`

### 8.1 Módulo: Núcleo de Entrada y Servicio de Bandeja (main.py)
- **Propósito:** Iniciar el ciclo de vida de la aplicación, configurar el sistema de bitácoras en disco (logs/app_YYYYMMDD.log), interceptar excepciones no capturadas (sys.excepthook), gestionar el icono en la bandeja del sistema (pystray) y orquestar el temporizador de actualización periódica.
- **Entradas:** Argumentos de línea de comandos (ej. --minimized) y eventos de usuario.
- **Procesos:** Verificación de autologin rápido por cookies o credenciales cifradas, montaje de la ventana de Tkinter con CustomTkinter, despacho de hilos demonio para la bandeja y notificaciones nativas de Windows con plyer.
- **Salidas:** Ventana gráfica interactiva y proceso en segundo plano en la barra de tareas.

### 8.2 Módulo: Configuración Global, Temas y Criptografía DPAPI (config.py)
- **Propósito:** Centralizar las constantes de URLs del INFD, rutas de archivos de caché en ~/.campus_tello/, definición de las 8 paletas de color, y proveer funciones de cifrado nativo usando ctypes contra crypt32.dll (CryptProtectData y CryptUnprotectData).
- **Funcionalidades:**
 - guardar_creds() / cargar_creds(): Almacenamiento seguro de DNI y contraseña.
 - guardar_cookies_sesion() / cargar_cookies_sesion(): Persistencia de cookies de sesión cifradas.
 - set_autoinicio_windows(): Manipulación del registro de Windows (HKCU\Software\Microsoft\Windows\CurrentVersion\Run).
 - generar_archivo_informacion_desktop(): Creación automática de la ficha técnica en el escritorio del usuario.

### 8.3 Módulo: Sesión HTTP y Adaptadores de Red (ackend/session.py)
- **Propósito:** Gestionar la comunicación HTTP/HTTPS con el servidor del campus mediante equests.Session.
- **Características:**
 - Montaje de HTTPAdapter con estrategia de reintentos (Retry(total=3, backoff_factor=1)).
 - Simulación de encabezados reales de navegador (Mozilla/5.0...).
 - Autenticación mediante hash MD5 de la contraseña según el protocolo de Educativa.
 - Verificación de sesión activa y fallback ante fallos de conexión.

### 8.4 Módulo: Extracción del Escritorio y Novedades (ackend/escritorio.py)
- **Propósito:** Extraer la nómina de materias cursadas por el estudiante y los eventos recientes del campus.
- **Procesos:**
 - Análisis sintáctico de variables embebidas en scripts JavaScript de escritorio.cgi.
 - Extracción de ID de curso, nombre de la materia, color asignado, porcentaje de avance, cantidad de ítems obligatorios y fecha de último acceso.
 - Clasificación de novedades (correos, nuevas unidades, calificaciones, actividades y foros) con cálculo de fechas relativas (ej. \hace 2 horas\, \ayer\).

### 8.5 Módulo: Programa Curricular y Actividades Evaluativas (ackend/programa.py)
- **Propósito:** Estructurar el contenido didáctico de cada materia consultando ctividades.cgi y programas.cgi.
- **Procesos:**
 - Detección de bloques de unidad (id=\unidad_XXXX\).
 - Clasificación de ítems: Actividades, Archivos, Contenidos de texto, Enlaces, y discriminación de \Contenido relacionado\.
 - Semaforización inteligente de actividades: Comparación de fechas límites contra la hora del sistema para marcar estados: Entregada (🟢), Pendiente (🟠) o Cerrada sin entregar (🔴).
 - Módulo de entrega de actividades: Envío de formularios POST multipart con comentarios y archivos adjuntos mediante ealizar_entrega_actividad().

### 8.6 Módulo: Calificaciones de Cátedra (ackend/calificaciones.py)
- **Propósito:** Extraer las notas, exámenes parciales, trabajos prácticos y observaciones docentes desde calificaciones.cgi.
- **Procesos:** Navegación por subcategorías (wAccion=verexamenes), análisis de tablas y tarjetas HTML, extracción de docentes evaluadores, fechas de calificación y comentarios pedagógicos.

### 8.7 Módulo: Mensajería Institucional Webmail (ackend/mensajes.py)
- **Propósito:** Brindar acceso a la bandeja de entrada del correo interno de la plataforma.
- **Procesos:** Extracción de listas de correos, descarga limpia del cuerpo del mensaje en get_detalle_mensaje() eliminando encabezados HTML residuales y listado de enlaces a archivos adjuntos con URLs completas.

### 8.8 Módulo: Contactos, Perfiles y Exportación (ackend/contactos.py)
- **Propósito:** Listar el cuerpo docente y los compañeros de curso por materia.
- **Procesos:**
 - Lectura de los objetos JSON de Educativa (Educativa.Aula.Contactos.data).
 - Enriquecimiento con datos de perfil desde perfil.cgi (emails, teléfonos, localidad, fecha de nacimiento, foto).
 - Almacenamiento en caché de 48 horas (cache_contactos.json).
 - Exportación de la nómina completa a formato CSV UTF-8 con encabezados estandarizados.

### 8.9 Módulo: Chat en Vivo con Firebase Firestore (ackend/cache_utils.py)
- **Propósito:** Permitir la comunicación instantánea en las salas de chat de cada materia.
- **Mecanismo:**
 1. Extrae el oken, campusCollection, oomId y irebaseConfig desde chat.cgi.
 2. Autentica contra la API de Firebase (signInWithCustomToken) para obtener un idToken.
 3. Consulta y envía mensajes directamente a la colección de Firestore (chat-educativa/databases/(default)/documents/...) mediante peticiones REST seguras.
 4. Ordena cronológicamente las conversaciones y detecta si los mensajes pertenecen al usuario activo.

### 8.10 Módulo: Scraper del Sitio Web Público y Parser PDF (ackend/sitio_informativo.py)
- **Propósito:** Indexar las publicaciones y documentos del sitio oficial https://ies5tello-juj.infd.edu.ar/sitio/.
- **Características:**
 - Rastrear artículos de noticias y enlaces a archivos PDF públicos.
 - Almacenar los documentos en ~/.campus_tello/cache/sitio/.
 - Extraer texto de archivos PDF mediante la función nativa extract_text_from_pdf_bytes() basada en descompresión de flujos zlib y análisis de operadores de texto PDF (Tj, TJ), permitiendo indexar resoluciones sin necesidad de dependencias binarias externas.
 - Proporcionar la función uscar_en_sitio_informativo() para consultas de palabras clave con sistema de puntuación (*relevance scoring*).

### 8.11 Módulo: Scraper de Redes Sociales y OCR Tesseract (ackend/facebook_scraper.py)
- **Propósito:** Extraer comunicados de la página institucional de Facebook y procesar el texto contenido en imágenes informativas.
- **Características:**
 - Consulta móvil optimizada de las páginas y grupos oficiales del IES N° 5.
 - Descarga de imágenes de publicaciones a ~/.campus_tello/cache/facebook/imagenes/.
 - Procesamiento con pytesseract y PIL buscando automáticamente ejecutables en rutas estándar de Windows (C:\Program Files\Tesseract-OCR\tesseract.exe).
 - Guardado en cache_facebook.json y búsqueda de texto por concordancia léxica.

### 8.12 Módulo: Normalización del Perfil de Usuario (ackend/user.py)
- **Propósito:** Centralizar y asegurar la obtención dinámica de la identidad del estudiante sin datos estáticos.
- **Procesos:** Extracción del DNI, nombre y apellido completos y URL de foto de perfil desde escritorio.cgi, opbar-user-name o estadisticas.cgi, persistiendo en user_cache.json para disponibilidad inmediata en UI y logs.

### 8.13 Módulo: Asistente Pedagógico con Inteligencia Artificial (ia/engine.py)
- **Propósito:** Proveer un tutor virtual inteligente para responder dudas del estudiante.
- **Arquitectura:**
 - **Modo Local:** Motor determinístico y semántico que responde instantáneamente preguntas sobre identidad, materias asignadas, docentes a cargo, actividades pendientes, entregas realizadas, publicaciones del sitio web y comunicados de Facebook con datos de las cachés locales.
 - **Modo Cloud:** Conectividad con Google Gemini (gemini-3.6-flash) y OpenAI (gpt-4o-mini), inyectando como contexto de sistema el estado académico completo del alumno.
 - **Manejo de Errores y Fallback:** Conmutación automática al modo local ante fallos de conexión o cuotas de API agotadas, con limpieza de formato y tipografía legible.

### 8.14 Módulos de Interfaz de Usuario (ui/)
- **ui/theme.py:** Administrador reactivo de temas con patrón Observer (egistrar_listener_tema).
- **ui/widgets.py:** Componentes reutilizables estilizados (tarjetas, botones con badges, separadores, encabezados).
- **ui/login.py:** Pantalla de autenticación con selector de temas y recordatorio seguro de credenciales.
- **ui/main_view.py:** Tablero principal con barra lateral, vista de materias con barra de progreso, panel de novedades, interfaz conversacional con animación de escritura de tres puntos (...), estadísticas y configuración.
- **ui/curso_detail.py:** Vista detallada de materia con pestañas: Programa con acordeón de unidades, Visor de Mensajes con botones de acción, Calificaciones, Contactos (con visualización de avatares y exportación CSV) y Chat General de Firebase con lectura y envío de mensajes.
- **ui/tutorial.py:** Modal interactivo de bienvenida que explica las funciones principales al primer inicio.

---

## 9. METODOLOGÍA DE TRABAJO Y GESTIÓN DE CALIDAD

Se aplicó un modelo de ciclo de vida iterativo e incremental guiado por pruebas en entorno real con credenciales institucionales:
1. **Fase de Mapeo de Protocolo:** Captura de respuestas HTTP y endpoints REST de Educativa y Firebase.
2. **Fase de Aislamiento de Capas:** Desacoplamiento riguroso entre los parsers de backend y los widgets de CustomTkinter.
3. **Fase de Refactor y Resiliencia:** Implementación de DPAPI, manejo de streams PDF zlib, OCR con Tesseract y selección de texto en la interfaz.
4. **Fase de Pruebas de Carga y Rendimiento:** Validación de tiempos de respuesta menores a 200 ms en visualizaciones cacheadas.

---

## 10. CRONOGRAMA, HITOS Y FASES DE DESARROLLO

- **Hito 1 (Arquitectura Base & Seguridad):** Implementación de session.py, config.py con DPAPI y user.py.
- **Hito 2 (Navegación Curricular y Evaluaciones):** Desarrollo de escritorio.py, programa.py y calificaciones.py.
- **Hito 3 (Comunicaciones y Tiempo Real):** Implementación de mensajes.py y el motor de Firebase Chat en cache_utils.py.
- **Hito 4 (Indexación Externa, PDF y OCR):** Desarrollo de sitio_informativo.py y acebook_scraper.py.
- **Hito 5 (Interfaz y Asistente IA):** Desarrollo de vistas CustomTkinter, animaciones de tipeo en ia/engine.py y empaquetado con PyInstaller.

---

## 11. RECURSOS Y REQUERIMIENTOS DEL SISTEMA

### 11.1 Software y Librerías
- **Intérprete:** Python 3.10 o superior (64-bit).
- **Librerías Core:** customtkinter, equests, eautifulsoup4, pillow, pystray, plyer.
- **Librerías Opcionales:** pytesseract (para OCR de imágenes), google-generativeai, openai.

### 11.2 Plataforma y Hardware
- Sistema Operativo: Microsoft Windows 10 / Windows 11.
- Memoria RAM: Mínimo 200 MB libres para ejecución fluida.

---

## 12. CRITERIOS DE ÉXITO Y EVALUACIÓN

1. **Rendimiento de Autenticación:** Inicio de sesión y carga del tablero en menos de 1.5 segundos utilizando cookies descifradas vía DPAPI.
2. **Integridad de Datos:** Coincidencia exacta del 100% de materias, actividades y calificaciones respecto a la interfaz oficial del INFD.
3. **Fluidez de Usuario:** Cero congelamientos de ventana en la interfaz gráfica durante peticiones de red pesadas o análisis de PDFs.
4. **Resiliencia Operativa:** Capacidad de consultar el programa completo y contactos en modo fuera de línea sin errores de ejecución.

---

## 13. CONCLUSIONES Y PROYECCIÓN FUTURA

El desarrollo de la **Suite de Escritorio y Launcher para el Campus Virtual del IES N° 5** demuestra la viabilidad y el enorme valor agregado de articular tecnologías modernas de cliente nativo (CustomTkinter, Criptografía DPAPI, APIs REST de Firebase y Modelos de Lenguaje) con infraestructuras educativas públicas preexistentes. 

El resultado es una herramienta que no solo simplifica radicalmente el trabajo cotidiano del alumno, sino que establece un estándar escalable para otras instituciones de educación superior del país que utilicen la plataforma del INFD.

---

## 14. GLOSARIO DE TÉRMINOS TÉCNICOS

- **DPAPI (*Data Protection API*):** Interfaz nativa de seguridad de Windows que permite a las aplicaciones cifrar y descifrar datos utilizando claves derivadas de la cuenta del usuario logueado en el sistema operativo.
- **CustomTkinter:** Biblioteca de interfaz gráfica para Python que extiende Tkinter con soporte para temas oscuros/claros modernos, esquinas redondeadas y escalado de alta densidad (DPI).
- **Firebase Firestore REST:** Protocolo de comunicación HTTP que interactúa con la base de datos distribuida en tiempo real de Google Cloud sin requerir SDKs pesados de C++/NodeJS.
- **OCR (*Optical Character Recognition*):** Tecnología que convierte imágenes de texto (como fotografías de carteles o volantes digitales) en caracteres de texto plano editables y buscables.
- **Zlib Stream Decompression:** Algoritmo de descompresión de datos sin pérdida utilizado internamente en el formato PDF para empaquetar flujos de texto e instrucciones gráficas.
- **System Tray (Bandeja del Sistema):** Sector de la barra de tareas de Windows donde las aplicaciones pueden seguir ejecutándose en segundo plano mostrando un icono de estado.
- **Semaforización de Actividades:** Clasificación visual mediante códigos de color (Verde, Naranja, Rojo) para identificar el estado de cumplimiento de una tarea académica.
