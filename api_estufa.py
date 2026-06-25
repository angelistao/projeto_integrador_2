import os
import psycopg2
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações de Diretório
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_FOTOS = os.path.join(DIRETORIO_ATUAL, 'fotos')

# Configuração de Conexão com o Banco
DB_CONN = "dbname=estufa_db user=admin_estufa password=sua_senha_aqui host=localhost port=5432"

@app.route('/upload', methods=['POST'])
def receber_dados():
    try:
        # Recebe os dados numéricos (formulário)
        umidade = request.form.get('umidade')
        temperatura = request.form.get('temperatura')

        if not umidade or not temperatura:
            return jsonify({"erro": "Umidade e temperatura são obrigatórios"}), 400

        # Recebe e processa o arquivo da foto
        if 'foto' not in request.files:
            return jsonify({"erro": "Nenhuma foto foi enviada no payload"}), 400
            
        foto = request.files['foto']
        
        if foto.filename == '':
            return jsonify({"erro": "Nome do arquivo de imagem está vazio"}), 400

        # secure_filename remove caracteres estranhos do nome da imagem por segurança
        nome_seguro = secure_filename(foto.filename)
        caminho_fisico = os.path.join(PASTA_FOTOS, nome_seguro)
        
        # Salva a imagem no HD do Ubuntu
        foto.save(caminho_fisico)

        # Caminho relativo para salvar no banco
        caminho_banco = f"fotos/{nome_seguro}"

        # Insere as informações no PostgreSQL
        conn = psycopg2.connect(DB_CONN)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO leituras_sensores (umidade_solo, temperatura, caminho_foto)
            VALUES (%s, %s, %s)
        ''', (umidade, temperatura, caminho_banco))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "sucesso"}), 201

    except Exception as e:
        print(f"Erro na API: {e}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

if __name__ == '__main__':
    # Roda na porta 5000 do Ubuntu (preparado para o Proxy Reverso do Nginx)
    app.run(host='0.0.0.0', port=5000)