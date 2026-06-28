import os
import psycopg2
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações de Diretório
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_FOTOS = os.path.join(DIRETORIO_ATUAL, 'fotos')
os.makedirs(PASTA_FOTOS, exist_ok=True)

# Configuração de Conexão com o Banco PostgreSQL
DB_CONN = "dbname=estufa_db user=admin_estufa password=estint123# host=localhost port=5432"

# --- ROTA NOVA: Recebe as configurações vindas do setup_planta.py ---
@app.route('/configuracoes', methods=['POST'])
def salvar_configuracoes():
    try:
        dados = request.json
        if not dados:
            return jsonify({"erro": "Payload JSON vazio"}), 400
            
        nome_planta = dados.get('nome_planta_pt')
        u_min = dados.get('umidade_minima')
        u_ideal = dados.get('umidade_ideal')
        info_cultivo = dados.get('info_cultivo_pt')

        # Atualiza a linha de ID 1 na tabela de configurações do PostgreSQL
        conn = psycopg2.connect(DB_CONN)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE configuracoes 
            SET nome_planta_pt = %s, 
                umidade_minima = %s, 
                umidade_ideal = %s, 
                info_cultivo_pt = %s
            WHERE id = 1
        ''', (nome_planta, u_min, u_ideal, info_cultivo))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "Configurações salvas com sucesso no Postgres"}), 200

    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")
        return jsonify({"erro": "Erro interno no servidor ao salvar configs"}), 500


# --- ROTA EXISTENTE: Recebe as leituras do main_control.py ---
@app.route('/upload', methods=['POST'])
def receber_dados():
    try:
        umidade = request.form.get('umidade')
        temperatura = request.form.get('temperatura')
        irrigou_raw = request.form.get('irrigou', 'false').lower()
        irrigou = True if irrigou_raw == 'true' else False

        if not umidade or not temperatura:
            return jsonify({"erro": "Umidade e temperatura são obrigatórios"}), 400

        caminho_banco = None
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '':
                nome_seguro = secure_filename(foto.filename)
                caminho_fisico = os.path.join(PASTA_FOTOS, nome_seguro)
                foto.save(caminho_fisico)
                caminho_banco = f"fotos/{nome_seguro}"

        conn = psycopg2.connect(DB_CONN)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO leituras_sensores (umidade_solo, temperatura, caminho_foto, irrigou)
            VALUES (%s, %s, %s, %s)
        ''', (umidade, temperatura, caminho_banco, irrigou))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "sucesso"}), 201

    except Exception as e:
        print(f"Erro na API ao receber upload: {e}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)