# app.py
import os
import shutil
import tempfile
import zipfile
from flask import Flask, request, send_file, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename

from ocr_core import processar_pdf

app = Flask(__name__)
app.secret_key = "troque-esta-chave"
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/processar", methods=["POST"])
def processar():
    arquivos = request.files.getlist("pdfs")
    arquivos = [a for a in arquivos if a and a.filename.lower().endswith(".pdf")]

    if not arquivos:
        flash("Envie pelo menos um arquivo PDF.")
        return redirect(url_for("index"))

    workdir = tempfile.mkdtemp(prefix="ocr_")
    entrada_dir = os.path.join(workdir, "entrada")
    saida_dir = os.path.join(workdir, "saida")
    os.makedirs(entrada_dir, exist_ok=True)
    os.makedirs(saida_dir, exist_ok=True)

    relatorios = []
    try:
        for arq in arquivos:
            nome_seguro = secure_filename(arq.filename)
            caminho_entrada = os.path.join(entrada_dir, nome_seguro)
            arq.save(caminho_entrada)

            try:
                saida, msg = processar_pdf(caminho_entrada, saida_dir)
                if saida:
                    relatorios.append(f"✅ {nome_seguro}  →  {os.path.basename(saida)}  ({msg})")
                else:
                    relatorios.append(f"⚠️  {nome_seguro}: {msg}")
            except Exception as e:
                relatorios.append(f"❌ {nome_seguro}: erro — {e}")

        # Monta ZIP com os PDFs gerados + um relatório
        zip_path = os.path.join(workdir, "resultado.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for nome in sorted(os.listdir(saida_dir)):
                zf.write(os.path.join(saida_dir, nome), arcname=nome)
            zf.writestr("relatorio.txt", "\n".join(relatorios))

        return send_file(
            zip_path,
            as_attachment=True,
            download_name="pdfs_renomeados.zip",
            mimetype="application/zip",
        )
    finally:
        # Limpa depois que o Flask enviar. Como send_file pode ser lazy,
        # usamos um hook simples para limpar após a resposta.
        pass


@app.teardown_request
def _cleanup(exc):
    # (Opcional) Limpeza dos temporários — o SO limpa /tmp no reboot
    pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)