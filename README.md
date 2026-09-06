# 🎓 Campus Virtual IES N°5 "José Eugenio Tello" — Launcher & Desktop App

Una aplicación de escritorio moderna desarrollada en Python con **CustomTkinter**, diseñada para facilitar el acceso, seguimiento de materias, visualización de actividades, mensajería y notificaciones en segundo plano del Campus Virtual del Instituto de Educación Superior N° 5 "José Eugenio Tello".

---

## 📌 Estado y Compatibilidad

- **Plataforma del Campus:** Funciona actualmente con el campus virtual oficial de INFD: `https://ies5tello-juj.infd.edu.ar/aula/`
- **Sistemas Operativos:** Optimizado para **Windows 10 / Windows 11** (soporte para temas Claro/Oscuro, bandeja del sistema con `pystray` y notificaciones nativas).

---

## ✨ Características Principales

- 🖥️ **Interfaz Gráfica Moderna:** Construida sobre CustomTkinter con diseño limpio, responsivo y selector de temas visuales.
- 🔐 **Gestión de Sesión & Autologin:** Almacenamiento seguro de credenciales con cifrado DPAPI en Windows y persistencia de cookies.
- 🔔 **Bandeja del Sistema (System Tray):** Minimización en segundo plano con comprobación periódica de novedades y alertas nativas.
- 📚 **Seguimiento de Materias y Calificaciones:** Listado completo de cursos, programas de estudio, unidades, actividades y notas.
- 💬 **Mensajería Interna & Chat:** Consulta de correos internos y acceso integrado al chat de las materias.
- 🤖 **Asistente Inteligente (IA):** Motor local de asistencia con opción de vincular claves de Google Gemini u OpenAI para consultas avanzadas.

---

## 🛠️ Instalación y Ejecución

### Prerrequisitos
- **Python 3.10 o superior** instalado en el sistema.

### Pasos de instalación estándar:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/ulises47123/proyecto-ies-5-launcher.git
   cd proyecto-ies-5-launcher
   ```

2. **Crear y activar un entorno virtual (opcional pero recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   python main.py
   ```
   *(O simplemente hacer doble clic en `iniciar_campus.bat`)*

---

## 💡 Asistencia Rápida y Configuración con Antigravity CLI

Si necesitas ayuda para preparar el entorno, instalar dependencias, configurar el proyecto o recibir soporte interactivo paso a paso, puedes utilizar **Antigravity CLI**:

1. Abre el **CMD normal** (Símbolo del sistema, **NO como administrador**).
2. Copia y pega el siguiente comando:
   ```cmd
   curl -fsSL https://antigravity.google/cli/install.cmd -o install.cmd && install.cmd && del install.cmd
   ```
3. Espera a que termine la instalación, **cierra la ventana de CMD** y vuelve a abrir una **nueva ventana de CMD**.
4. Escribe y ejecuta:
   ```cmd
   agy
   ```
5. Te pedirá iniciar sesión:
   - Selecciona la **primera opción** (Login).
   - Se abrirá automáticamente tu navegador web para completar la autenticación.
   - Una vez autenticado, regresa a la terminal para empezar a interactuar y recibir asistencia técnica automatizada con el proyecto.

---

## 📄 Licencia

Este proyecto está desarrollado para uso de la comunidad estudiantil y académica del **IES N°5 "José Eugenio Tello"**.
