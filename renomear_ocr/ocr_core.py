# ocr_core.py
import os
import re
import pymupdf as fitz
import pytesseract
from PIL import Image
from io import BytesIO

# No Linux (Docker) o Tesseract já fica no PATH; não precisa setar caminho.
# Se rodar no Windows localmente, descomente e ajuste a linha abaixo:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TIPOS = {
    r"promo[çc][aã]o\s+de\s+arquivamento": "Prom Arq",
    r"registro\s+de\s+ocorr[êe]ncia":      "RO",
    r"portaria":                            "Port",
    r"relat[óo]rio\s+final":                "Relat Final",
    r"auto\s+de\s+apreens[ãa]o":            "Auto de AP",
}

REGEX_REGISTRO = re.compile(r"\b(\d{2,3})[\-/](\d{3,5})[\-/](\d{4})\b")


def ocr_pagina(pagina):
    pix = pagina.get_pixmap(dpi=200)
    img = Image.open(BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang="por")


def pagina_em_branco(pagina):
    texto_ocr = ocr_pagina(pagina)
    texto_limpo = re.sub(r"[^a-zA-Z0-9À-ÿ]", "", texto_ocr)
    return len(texto_limpo) < 15


def encontrar_tipo(texto):
    texto_norm = re.sub(r"\s+", " ", texto)
    for padrao, abrev in TIPOS.items():
        if re.search(padrao, texto_norm, flags=re.IGNORECASE):
            return abrev
    return None


def encontrar_registro(texto):
    texto_limpo = texto.replace("O", "0").replace("o", "0")
    m = REGEX_REGISTRO.search(texto_limpo) or REGEX_REGISTRO.search(texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/:*?"<>|]', "-", nome).strip()


def processar_pdf(caminho_entrada, pasta_destino):
    """
    Processa o PDF e salva o resultado em pasta_destino.
    Retorna (caminho_saida, mensagem).
    """
    doc = fitz.open(caminho_entrada)

    if len(doc) == 0:
        doc.close()
        return None, "PDF vazio"

    texto_primeira = ocr_pagina(doc[0])
    tipo = encontrar_tipo(texto_primeira)
    registro = encontrar_registro(texto_primeira)

    if not tipo:
        doc.close()
        return None, "Tipo de documento não identificado."
    if not registro:
        doc.close()
        return None, "Número de registro não encontrado na 1ª página."

    removidas = 0
    for i in range(len(doc) - 1, -1, -1):
        if pagina_em_branco(doc[i]):
            doc.delete_page(i)
            removidas += 1

    nome_final = limpar_nome_arquivo(f"{tipo} - {registro}.pdf")
    saida = os.path.join(pasta_destino, nome_final)

    contador = 1
    base, ext = os.path.splitext(saida)
    while os.path.exists(saida):
        saida = f"{base} ({contador}){ext}"
        contador += 1

    doc.save(saida)
    doc.close()

    return saida, f"{removidas} página(s) em branco removida(s)"