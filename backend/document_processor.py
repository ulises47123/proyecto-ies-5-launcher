"""
backend/document_processor.py — Procesamiento de archivos PDF, DOCX e Imágenes (OCR)
y extracción estructurada con conversión de tablas a ASCII y generación de base de conocimiento.
"""
import os
import shutil
import json
import re
from typing import Dict, Any, List
from config import DATA_ORIGINAL_DIR, DATA_PROCESSED_DIR, KB_JSON_FILE


class DocumentProcessor:
    def __init__(self):
        os.makedirs(DATA_ORIGINAL_DIR, exist_ok=True)
        os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(KB_JSON_FILE), exist_ok=True)

    def format_table_ascii(self, rows: List[List[str]]) -> str:
        """Convierte una matriz 2D de celdas en una tabla ASCII legible."""
        if not rows:
            return ""
        clean_rows = []
        for r in rows:
            clean_rows.append([str(c or "").strip().replace("\n", " ") for c in r])
        
        col_widths = {}
        for r in clean_rows:
            for idx, c in enumerate(r):
                col_widths[idx] = max(col_widths.get(idx, 0), len(c))
        
        if not col_widths:
            return ""
        
        num_cols = max(col_widths.keys()) + 1
        sep = "+" + "+".join("-" * (col_widths.get(i, 0) + 2) for i in range(num_cols)) + "+"
        
        lines = [sep]
        for idx, r in enumerate(clean_rows):
            padded = []
            for i in range(num_cols):
                val = r[i] if i < len(r) else ""
                padded.append(f" {val.ljust(col_widths.get(i, 0))} ")
            lines.append("|" + "|".join(padded) + "|")
            if idx == 0:
                lines.append(sep)
        lines.append(sep)
        return "\n".join(lines)

    def extract_from_image(self, file_path: str) -> str:
        """Extrae texto de una imagen utilizando OCR (Tesseract)."""
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(file_path)
            texto = pytesseract.image_to_string(img, lang="spa+eng")
            return texto.strip()
        except Exception as e:
            return f"[OCR no disponible o error procesando imagen: {e}]"

    def extract_from_docx(self, file_path: str) -> str:
        """Extrae texto y tablas formateadas en ASCII desde un DOCX."""
        try:
            import docx
            doc = docx.Document(file_path)
            text_parts = []
            for p in doc.paragraphs:
                if p.text.strip():
                    text_parts.append(p.text.strip())
            
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    table_data.append([cell.text for cell in row.cells])
                if table_data:
                    ascii_tbl = self.format_table_ascii(table_data)
                    text_parts.append("\n" + ascii_tbl + "\n")
            
            return "\n\n".join(text_parts).strip()
        except Exception as e:
            return f"[Error extrayendo DOCX: {e}]"

    def extract_from_pdf(self, file_path: str) -> str:
        """Extrae texto y tablas desde un archivo PDF."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for idx, page in enumerate(reader.pages):
                page_txt = page.extract_text() or ""
                if page_txt.strip():
                    text_parts.append(f"--- Página {idx + 1} ---\n" + page_txt.strip())
            return "\n\n".join(text_parts).strip()
        except Exception as e:
            return f"[Error extrayendo PDF: {e}]"

    def generate_index(self, content: str) -> List[str]:
        """Detecta encabezados, unidades, secciones y palabras clave en el texto."""
        index_items = []
        lines = content.splitlines()
        patterns = [
            r'^(?:unidad|módulo|modulo|capítulo|capitulo|sección|seccion|eje|tema)\s+\d+[:\.\-]?\s*(.*)',
            r'^(?:objetivos?|fundamentación|fundamentacion|contenidos?|metodología|metodologia|evaluación|evaluacion|cronograma|bibliografía|bibliografia|criterios?|condiciones?|fechas?)\b[:\.\-]?\s*(.*)',
            r'^(?:\d+\.[\d\.]*)\s+([A-ZÁÉÍÓÚÑ].*)',
            r'^([A-ZÁÉÍÓÚÑ\s]{4,40}):?$'
        ]
        
        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) > 80:
                continue
            for p in patterns:
                m = re.match(p, line_str, re.IGNORECASE)
                if m:
                    clean = line_str.replace("#", "").strip()
                    if clean and clean not in index_items:
                        index_items.append(clean)
                    break
        return index_items

    def process_file(self, file_path: str, materia: str = "", carrera: str = "") -> Dict[str, Any]:
        """Procesa un archivo original, realiza backup, extrae texto/tablas y actualiza la base de conocimiento."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No existe el archivo: {file_path}")

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # 1. Copia de seguridad en /data/original_files/
        backup_path = os.path.join(DATA_ORIGINAL_DIR, filename)
        if os.path.abspath(file_path) != os.path.abspath(backup_path):
            shutil.copy2(file_path, backup_path)

        # 2. Extracción de contenido
        content = ""
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"]:
            content = self.extract_from_image(backup_path)
        elif ext in [".docx", ".doc"]:
            content = self.extract_from_docx(backup_path)
        elif ext == ".pdf":
            content = self.extract_from_pdf(backup_path)
        elif ext in [".txt", ".csv", ".md"]:
            with open(backup_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            raise ValueError(f"Formato no soportado: {ext}")

        # 3. Guardar archivo .txt en /data/processed/
        base_name = os.path.splitext(filename)[0]
        processed_file = os.path.join(DATA_PROCESSED_DIR, f"{base_name}.txt")
        with open(processed_file, "w", encoding="utf-8") as f:
            f.write(content)

        # 4. Generar índice
        index_list = self.generate_index(content)
        
        # Detectar tipo de documento
        doc_type = "general"
        lower_txt = (filename + " " + content[:500]).lower()
        if any(w in lower_txt for w in ["plan", "planificac", "programa", "materia", "cátedra", "catedra"]):
            doc_type = "planificacion"
        elif any(w in lower_txt for w in ["parcial", "evaluac", "examen", "trabajo práctico", "tp"]):
            doc_type = "evaluacion"
        elif any(w in lower_txt for w in ["resoluc", "comunicado", "reglamento", "circular"]):
            doc_type = "institucional"

        # 5. Guardar/Actualizar en knowledge_base.json
        doc_entry = {
            "titulo": base_name.replace("_", " ").title(),
            "fuente": filename,
            "archivo_procesado": f"{base_name}.txt",
            "indice": index_list,
            "contenido": content,
            "tipo": doc_type,
            "materia": materia or "General",
            "carrera": carrera or "IES N°5"
        }

        self._update_knowledge_base(doc_entry)
        return doc_entry

    def _update_knowledge_base(self, doc_entry: Dict[str, Any]):
        kb_data = {"documentos": []}
        if os.path.exists(KB_JSON_FILE):
            try:
                with open(KB_JSON_FILE, "r", encoding="utf-8") as f:
                    kb_data = json.load(f)
            except Exception:
                kb_data = {"documentos": []}

        docs = kb_data.get("documentos", [])
        docs = [d for d in docs if d.get("fuente") != doc_entry.get("fuente")]
        docs.append(doc_entry)
        kb_data["documentos"] = docs

        with open(KB_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, ensure_ascii=False, indent=2)
