
Se probó la app desde cero, arrancando el programa, logueándose, y recorriendo cada sección con un usuario real. Se encontraron 9 problemas nuevos. Algunos se repiten con los ya reportados y no fueron corregidos.

Bug 1 — La pantalla de login parpadea mientras se escribe
Reproducción:

Abrir el programa.

Empezar a escribir usuario/contraseña.

Comportamiento actual:

La página parpadea (flicker) de forma constante mientras se tipea.

Comportamiento esperado:

La pantalla debe quedar estable. Nada de parpadeos ni re-renderizados.

Preguntas para el dev:

¿Hay algún setInterval o requestAnimationFrame corriendo en el login?

¿El logo o algún elemento se re-renderiza con cada input?

Bug 2 — Foto de perfil NO se ve (REINCIDENTE)
Reproducción:

Loguearse.

Ver el sidebar / topbar / sección Ajustes.

Comportamiento actual:

La foto de perfil no carga. Ya se había reportado en la ronda anterior y sigue igual.

Comportamiento esperado:

Se debe ver la foto de perfil del usuario.

Si el usuario no tiene foto, mostrar un avatar por defecto (iniciales o placeholder).

Bug 3 — "Pendientes" muestra 3, pero al abrir una actividad no entra al contenido
Reproducción:

Ir a Mis Pendientes → dice "3".

Hacer clic en una actividad → aparece "Ir a materia".

Hacer clic en "Ir a materia" → no abre la actividad.

Comportamiento actual:

No te lleva adentro de la actividad. Te deja en el listado o no hace nada.

Comportamiento esperado:

El botón "Ir a materia" (o el nombre de la actividad) debe abrir el contenido de la actividad dentro de la materia correspondiente, como en el campus oficial.

Nota: esto se suma al Bug 1 de la ronda anterior (el nombre de la actividad no era clickeable). Ahora tampoco funciona "Ir a materia".

Bug 4 — El contenido de la actividad está vacío / con placeholders
Reproducción:

Abrir la actividad (con el mecanismo que sí funcione).

Ver el contenido.

Comportamiento actual:

Se ve:

"Sin fecha límite especificada"

"Información, recomendaciones"

"Sin consigna descriptiva"

El contenido real que subió el profesor NO se muestra.

Comportamiento esperado:

Se debe mostrar exactamente lo que hay en el campus: consigna, fecha, archivos adjuntos, recomendaciones.

Preguntas para el dev:

¿El scraping está trayendo el campo de contenido de la actividad?

¿Está devolviendo strings vacíos y vos mostrás textos de relleno? Está prohibido rellenar con texto por defecto (viola la regla de cero datos estáticos).

Si el campus realmente no tiene contenido cargado, mostrar el mismo mensaje que muestra el campus ("Sin consigna"), pero no inventar textos.

Bug 5 — Novedades muestra "nuevo Gmail" pero al abrir no hay nada
Reproducción:

Ir a Novedades.

Dice "1 nuevo Gmail" (o similar).

Abrir la novedad → no muestra nada.

También: el contador dice "2" pero no especifica qué son esas 2.

Comportamiento esperado:

Al abrir una novedad, mostrar su contenido real.

El contador debe ser claro: "2 novedades" con listado, no solo un número suelto.

Preguntas para el dev:

¿El backend devuelve contenido vacío para esa novedad?

¿El contador de novedades cuenta ítems distintos a los que se listan? (bug de datos cruzados)

Bug 6 — Asistente IA: aparenta estar activo pero no tiene API configurada
Reproducción:

Ir a Asistente IA.

Escribir un mensaje y enviar.

Sin tener API key configurada.

Comportamiento actual:

La UI aparenta estar activa, como si la IA estuviera lista.

Al enviar, no pasa nada (o falla silenciosa).

Comportamiento esperado:

Si no hay API key configurada, mostrar un cartel claro:

"Ingresá tu API Key de Gemini/OpenAI en Ajustes para usar el asistente."

Y deshabilitar el input hasta que haya key.

Preguntas para el dev:

¿Hay verificación de API key configurada antes de mostrar el chat como activo?

¿Dónde se guarda la key? ¿Se valida que exista?

Bug 7 — Estadísticas: "condición regular 100%" no tiene sentido
Reproducción:

Ir a Estadísticas.

Comportamiento actual:

Aparece "Condición regular: 100%". Es contradictorio: si es regular al 100%, ¿por qué es "regular"?

Comportamiento esperado:

Aclarar qué significa ese indicador y con qué criterio se calcula.

Si es un promedio de notas, mostrarlo como "Promedio general: X".

Si es % de aprobación, mostrarlo como "Materias aprobadas: X%".

Preguntas para el dev:

Pegá la fórmula con la que calculás ese "100%".

Bug 8 — Algunas materias muestran "null, null, null"
Reproducción:

Ir a Estadísticas (o Mis Materias).

Ver ciertas materias.

Comportamiento actual:

Aparecen como "null, null, null" literal.

Comportamiento esperado:

Nunca debe aparecer "null" en pantalla. Si un dato no existe, mostrar "—" o dejar el campo vacío.

Preguntas para el dev:

¿Por qué esas materias vienen con null desde el backend? ¿El scraping falló?

En JS, agregar filtro: valor ?? "—" en todos los campos.

Bug 9 — Cambiar tema dice "exitoso" pero no cambia nada
Reproducción:

Ir a Ajustes → cambiar de tema (claro/oscuro).

Aparece "Tema cambiado exitosamente".

Comportamiento actual:

No cambia nada visualmente. El mensaje es mentira.

Comportamiento esperado:

Al cambiar de tema, toda la UI debe cambiar de colores (sidebar, topbar, tarjetas, botones, textos).

O bien, si el tema no está implementado, no mostrar el mensaje de éxito.

Preguntas para el dev:

¿El cambio de tema aplica una clase al <body> o a :root?

¿Está implementado de verdad o es solo un botón decorativo?

Bug 10 — Faltan configuraciones en Ajustes
Reproducción:

Ir a Ajustes.

Comportamiento actual:

Faltan opciones. La sección está incompleta.

Comportamiento esperado:

Definir con el responsable qué ajustes debe tener la sección:

Tema (claro/oscuro).

API Key de IA.

Notificaciones.

Autologin.

Cambio de contraseña (si aplica).

Cerrar sesión.

Actualizaciones.

Acción: antes de tocar código, pedirle al responsable (Ulises) la lista cerrada de ajustes.

Sobre las pruebas
Antes de reportar "resuelto" cualquier bug:

Ejecutá el flujo completo de reproducción.

Grabá un video de 15-30 segundos mostrando el antes y el después.

Confirmá que ningún otro bug se rompió como efecto colateral.

Sin video, no se aprueba.

Recordatorio importante
Sigue pendiente sin resolver lo de la ronda 5: el fix de threading con future.result() que bloquea Qt. Se rechazó 3 veces. No lo pierdas de vista. Estos 10 bugs son adicionales a eso, no en lugar de eso.

Orden de prioridad:

Threading (bloqueante crítico, sin resolver).

Bugs 2, 3, 4, 5 (funcionalidad rota, datos que no llegan).

Bug 9 (UI que miente al usuario).

Bugs 1, 6, 7, 8 (UX y claridad).

Bug 10 (falta definir scope con Ulises).

