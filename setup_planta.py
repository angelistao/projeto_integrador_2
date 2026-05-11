import requests
import sqlite3
from deep_translator import GoogleTranslator

# configuração dos tradtores
tradutor_en = GoogleTranslator(source='pt', target='en') 
tradutor_pt = GoogleTranslator(source='en', target='pt') 

def configurar_banco_inicial():
    """cria as tabelas caso elas ainda não existam no SQLite"""
    conn = sqlite3.connect('estufa.db')
    cursor = conn.cursor()
    
    # criando a tabela de configurações com as colunas de tradução
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY,
            nome_planta_pt TEXT,
            umidade_minima REAL,
            umidade_ideal REAL,
            info_cultivo_pt TEXT
        )
    ''')
    
    # Garante que existe ao menos uma linha para o ID 1
    cursor.execute('INSERT OR IGNORE INTO configuracoes (id) VALUES (1)')
    conn.commit()
    conn.close()

def setup_estufa(nome_planta_usuario):
    configurar_banco_inicial()
    
    try:
        # traduz o nome para busca na API
        nome_en = tradutor_en.translate(nome_planta_usuario)
        print(f"Buscando '{nome_en}' no Harvest Helper...")

        # requisição para a API
        url = f"http://harvesthelper.herokuapp.com/api/v1/plants/{nome_en.lower().replace(' ', '-')}"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Erro: Planta '{nome_planta_usuario}' não encontrada.")
            return

        dados = response.json()

        # 3. Tradução dos dados retornados
        print("Traduzindo informações para o Dashboard...")
        dicas_pt = tradutor_pt.translate(dados.get('planting_considerations', 'Sem dicas disponíveis.'))
        rega_en = dados.get('watering', '')
        
        #  limiares de umidade
        # Mapeamento básico baseado em palavras-chave da API
        if "frequent" in rega_en.lower() or "much" in rega_en.lower():
            u_min, u_ideal = 60.0, 80.0
        else:
            u_min, u_ideal = 40.0, 65.0

        # salvando no Banco de Dados
        conn = sqlite3.connect('estufa.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE configuracoes 
            SET nome_planta_pt = ?, 
                umidade_minima = ?, 
                umidade_ideal = ?, 
                info_cultivo_pt = ?
            WHERE id = 1
        ''', (nome_planta_usuario.capitalize(), u_min, u_ideal, dicas_pt))
        
        conn.commit()
        conn.close()
        print(f"\n[OK] Estufa configurada para: {nome_planta_usuario}")
        print(f"Limiar de Irrigação: {u_min}%")

    except Exception as e:
        print(f"Erro no Setup: {e}")

if __name__ == "__main__":
    planta = input("Digite o nome da planta para configurar a estufa: ")
    setup_estufa(planta)
