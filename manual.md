1. Regla principal (no negociable)

En el HTML/JS NO se escribe ningún dato del usuario ni de la institución. Se escriben solo etiquetas vacías (<span id="...">) o placeholders que el backend en Python rellena al iniciar sesión con los datos reales del scraping.

Ejemplo correcto:

```html
<h2>Carrera: <span id="nombre-carrera"></span></h2>
<p>Materias activas: <span id="materias-activas"></span></p>
<p>Usuario: <span id="nombre-usuario"></span></p>
```

Ejemplo incorrecto (prohibido):

```html
<h2>Carrera: Tecnicatura Superior en Soporte de Infraestructura TIC</h2>
<p>Materias activas: 6</p>
<p>Usuario: Juan Pérez</p>
```

---

2. Qué puede ser estático y qué NO

Elemento ¿Estático?
Botones (forma, color, hover, active) ✅ SÍ
Logos e íconos (IES N°5, etc.) ✅ SÍ
Estructura HTML (divs, ids, clases) ✅ SÍ
Nombre del usuario ❌ NO — dinámico
Nombre de la carrera ❌ NO — dinámico
Materias activas (número y lista) ❌ NO — dinámico
Mis tareas / pendientes / novedades ❌ NO — dinámico
Mensajería ❌ NO — dinámico
Calificaciones ❌ NO — dinámico
Ajustes del usuario ❌ NO — dinámico
Asistente IA ❌ NO — dinámico
Estadísticas ❌ NO — dinámico

Si un dato cambia entre un alumno de Química y uno de TIC, es dinámico. Punto.

---

3. Filosofía obligatoria: un módulo = una responsabilidad

No se permiten archivos gigantes que hacen todo. Estructura mínima:

```
modules/
├── auth.py          # Solo login, logout, sesión
├── scraper.py       # Solo scraping del campus
├── materias.py      # Solo materias y calificaciones
├── pendientes.py    # Solo tareas y pendientes
├── novedades.py     # Solo novedades
├── mensajeria.py    # Solo mensajería
├── asistente_ia.py  # Solo IA
├── ajustes.py       # Solo preferencias del usuario
└── ui_helpers.py    # Solo estilos de botones (hover, active, focus)
```

Cada módulo hace una sola cosa y la hace bien.

---

4. Correcciones puntuales pendientes

4.1 Logo del terciario

· Falta el logo del IES N°5 en la parte superior del launcher, al lado de "Launcher Oficial N°5".
· Va en assets/logo_ies5.png y se carga una sola vez al iniciar.

4.2 Borde blanco en "Mis materias"

· El botón "Mis materias" tiene un borde/outline blanco persistente aunque no esté seleccionado.
· Los demás botones (Asistencia, Novedades, etc.) no lo tienen. Hay que igualarlo al resto.
· En CSS: quitar outline, border y box-shadow en :focus y :active. Que solo se pinte al hacer hover o cuando esté seleccionado, igual que los otros.

4.3 Congelamiento al entrar a "Mis materias"

· Al hacer clic en "Mis materias" el programa se tilda unos segundos.
· Causa: el scraping o la carga de datos se ejecuta en el hilo principal.
· Solución: mover toda operación de red/scraping a un hilo separado (threading) y actualizar la UI con root.after(). Nunca bloquear el hilo principal.

4.4 Botón "Actualizar" deja el programa en "No responde"

· Mismo problema que 4.3: operación bloqueante en el hilo principal.
· Debe ejecutarse en segundo plano con un indicador de carga visible.
· Al terminar, refresca todas las secciones de una vez.

---

5. Reglas de entrega (obligatorias)

Antes de entregar cualquier cambio, el desarrollador debe testear y confirmar que:

1. ✅ Login con dos usuarios distintos (ej: alumno de Química y alumno de TIC) → el nombre, la carrera y las materias cambian correctamente.
2. ✅ Cerrar sesión y volver a entrar con otro usuario → no quedan datos del usuario anterior.
3. ✅ Ningún botón queda con borde blanco persistente al navegar.
4. ✅ Clic en "Mis materias" → entra sin tildarse.
5. ✅ Clic en "Actualizar" varias veces seguidas → no se congela.
6. ✅ El logo del IES N°5 se ve arriba del launcher.
7. ✅ Buscar en el HTML la palabra "Tecnicatura", "Soporte", "TIC" o cualquier nombre propio hardcodeado → no debe aparecer ninguno.

No se entrega nada a medias. Si algo no está probado, no se manda.

---

6. Respuesta que necesito del desarrollador

Que confirme por escrito:

1. ¿En qué rama o repo está la versión con HTML/JS? (link o nombre de rama)
2. ¿Con qué tecnología se embebe el HTML dentro de Python? (¿PyWebView, Eel, Electron, Flask?)
3. ¿Cuántos archivos HTML/JS hay actualmente y en cuáles hay datos hardcodeados?
4. ¿Puede comprometerse a testear los 7 puntos del apartado 5 antes de entregar?
ermines de programar, se requiere que vos te steés el mismo.