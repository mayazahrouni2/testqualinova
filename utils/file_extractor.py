import os
import io
import pandas as pd
from docx import Document
import pdfplumber
import pytesseract
from PIL import Image

class FileExtractor:
    """ Extracteur multimodal robuste (OCR + parsing structuré) """

    @staticmethod
    def extract_word(file_bytes_or_path):
        is_bytes = isinstance(file_bytes_or_path, (bytes, io.BytesIO))
        doc = Document(io.BytesIO(file_bytes_or_path) if is_bytes else file_bytes_or_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
        
    @staticmethod
    def extract_excel(file_bytes_or_path):
        # On lit toutes les feuilles par défaut
        return pd.read_excel(file_bytes_or_path, sheet_name=None)

    @staticmethod
    def extract_pdf(file_path):
        """ Extraction PDF (Text + OCR fallback si nécessaire) """
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    # Fallback vers OCR si la page est une image
                    img = page.to_image(resolution=300).original
                    text += pytesseract.image_to_string(img) + "\n"
        return text

    @staticmethod
    def extract_image(file_path):
        """ Extraction OCR pour les images (preuves visuelles) """
        return pytesseract.image_to_string(Image.open(file_path))

    @classmethod
    def extract_by_extension(cls, file_path):
        """ Routage automatique par extension """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".docx", ".doc"]:
            return cls.extract_word(file_path)
        elif ext in [".xlsx", ".xls"]:
            # On retourne un dictionnaire de dataframes en texte
            data = cls.extract_excel(file_path)
            full_text = ""
            for name, df in data.items():
                full_text += f"\nSheet: {name}\n{df.to_string()}\n"
            
            print(f"DEBUG: Texte brut Excel extrait ({len(full_text)} caractères)")
            return full_text
        elif ext == ".pdf":
            return cls.extract_pdf(file_path)
        elif ext in [".png", ".jpg", ".jpeg"]:
            return cls.extract_image(file_path)
        elif ext == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
