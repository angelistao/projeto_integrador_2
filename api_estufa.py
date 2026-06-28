import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS  # <-- IMPORTANTE
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

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
    
@app.route('/dashboard', methods=['GET'])
def obter_dashboard():
    try:
        conn = psycopg2.connect(DB_CONN)
        cursor = conn.cursor()

        # Busca configuração e últimos dados dos sensores
        cursor.execute("SELECT nome_planta_pt, umidade_minima, umidade_ideal, info_cultivo_pt FROM configuracoes WHERE id = 1")
        config = cursor.fetchone()

        cursor.execute("SELECT umidade_solo, temperatura, to_char(data_hora, 'HH24:MI') as hora, data_hora FROM leituras_sensores ORDER BY id DESC LIMIT 6")
        historico_db = cursor.fetchall()
        
        cursor.close()
        conn.close()

        nome_planta = config[0] if config else "Desconhecida"
        u_min = config[1] if config else 0.0
        u_ideal = config[2] if config else 0.0
        
        history_data = []
        if historico_db:
            leitura_atual = historico_db[0] 
            for row in reversed(historico_db):
                history_data.append({"time": row[2], "temperature": row[1], "humidity": row[0]})
            ultima_atualizacao = leitura_atual[3].isoformat()
            temp_atual = leitura_atual[1]
            umidade_atual = leitura_atual[0]
        else:
            ultima_atualizacao = "2026-01-01T00:00:00"
            temp_atual = 0.0
            umidade_atual = 0.0

        payload = {
            "plant": {
                "type": nome_planta.capitalize(),
                "cultivar": "Automático",
                "stage": "Vegetativo",
                "bed": "Estufa Principal",
                "plantedAt": "2026-06-28"
            },
            "environment": {
                "temperature": {
                    "label": "Temperatura", "current": temp_atual,
                    "ideal": { "min": 20, "max": 30 }, "unit": "°C"
                },
                "humidity": {
                    "label": "Umidade", "current": umidade_atual,
                    "ideal": { "min": u_min, "max": u_ideal }, "unit": "%"
                }
            },
            "devices": [
                { "name": "PostgreSQL", "status": "online", "detail": "Ativo" },
                { "name": "ESP-CAM", "status": "standby", "detail": "Aguardando trigger" }
            ],
            "history": history_data if history_data else [{"time": "00:00", "temperature": 0, "humidity": 0}],
            "photos": [],
            "events": [
                { "time": history_data[-1]["time"] if history_data else "00:00", "title": "Sincronização", "detail": "Banco atualizado." }
            ],
            "updatedAt": ultima_atualizacao
        }

        return jsonify(payload), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/photos/latest', methods=['GET'])
def obter_fotos():
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)