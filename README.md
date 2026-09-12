# 🎓 Campus Virtual IES N°5 "José Eugenio Tello" — Launcher Híbrido Web (v3)

Una aplicación de escritorio de **nueva generación** desarrollada con **Pyloid** (Chromium embebido + backend en Python). Diseñada con una interfaz moderna y fluida estilo Discord, que facilita la visualización de clases, calificaciones, mensajería y seguimiento de actividades del Campus Virtual del Instituto de Educación Superior N° 5.

---

## 📌 Arquitectura y Tecnología

- **Motor Frontend:** Interfaz web renderizada en WebView nativo de alta velocidad, diseñada con **TailwindCSS**, HTML puro y Vanilla JavaScript. Completamente libre de recargas e interrupciones.
- **Motor Backend:** Lógica asíncrona en Python, utilizando `requests` y `beautifulsoup4` para extraer y procesar eficientemente la información de la plataforma educativa del INFD.
- **Conectividad:** Comunicación directa mediante IPC (Inter-Process Communication) vía `@Bridge` sin bloquear la interfaz. Aceleración de Hardware (GPU) optimizada para evitar parpadeos.

---

## ✨ Características Principales

- 🖥️ **Interfaz Fluida & Anti-Flicker:** Navegación por pestañas SPA con doble buffering nativo (View Transitions API), aislamiento de repintado 3D (GPU), y tamaño de fuente ampliado para legibilidad absoluta.
- 🔐 **Autenticación Desacoplada:** Login que recupera la sesión y expone todos los datos al entorno virtual usando hilos.
- 🖼️ **Imágenes de Perfil Dinámicas (4 Métodos):** Recuperación robusta de avatares protegidos por autenticación que salta la barrera de las cookies en 4 fases: Base64 en línea, Caché local, CookieSync y SVG Dinámico.
- 📚 **Visualización de Clases:** Lectura profunda del programa de la materia, renderizando PDFs, adjuntos, y el contenido con enlaces navegables y estados de entrega claros.
- 💬 **Mensajería Interna Integrada:** Lectura directa del Webmail institucional. Bandeja de Recibidos/Enviados visible nativamente como pestaña principal de la materia.
- 📊 **Calificaciones y Directorio:** Acceso rápido a las libretas de la cursada, promedios y todos los docentes y compañeros de la materia.
- 🤖 **Asistente IA (Gemini):** Integración nativa opcional de IA local para apoyo académico basado en los textos de las clases.

---

## 🛠️ Instalación y Ejecución

### Prerrequisitos
- **Python 3.10 o superior** instalado en Windows.

### Pasos de instalación:

1. **Clonar el repositorio (Rama feature/gui-web-v3-jc o main):**
   ```bash
   git clone https://github.com/ulises47123/proyecto-ies-5-launcher.git
   cd proyecto-ies-5-launcher
   ```

2. **Crear entorno virtual (Opcional recomendado):**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instalar dependencias necesarias:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Dependencias críticas: `pyloid`, `requests`, `beautifulsoup4`, `Pillow`)*

4. **Ejecutar la nueva aplicación híbrida:**
   ```bash
   python app_pyloid.py
   ```

---

## 🧪 Pruebas del Backend

Si necesitas diagnosticar la extracción de datos sin cargar la interfaz gráfica, dispones de un script de pruebas CLI en el entorno:
```bash
python pruebas/test_live_backend.py
```
*(Espera las credenciales en duro o mediante entorno virtualizado para escupir todo el JSON raspado en tiempo real).*

---

## 💡 Soporte y Antigravity CLI

Si deseas aportar o depurar módulos a bajo nivel usando herramientas de Agentes de IA:
1. Abre un CMD normal (NO administrador).
2. Ejecuta:
   ```cmd
   curl -fsSL https://antigravity.google/cli/install.cmd -o install.cmd && install.cmd && del install.cmd
   ```
3. Cierra, abre otra ventana e inicia: `agy`.

---

## 📄 Licencia

Proyecto desarrollado orgánicamente para uso de la comunidad del **IES N°5 "José Eugenio Tello"**.
