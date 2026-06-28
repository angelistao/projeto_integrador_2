import requests
from deep_translator import GoogleTranslator

# Configuração dos tradutores (Source/Target explícitos)
tradutor_en = GoogleTranslator(source='pt', target='en') 
tradutor_pt = GoogleTranslator(source='en', target='pt') 

# INSIRA A SUA CHAVE DA PERENUAL AQUI
PERENUAL_API_KEY = "sk-gVyb6a418897b35b818469" 

# URL do endpoint Flask que salvará os dados diretamente no banco PostgreSQL
API_FLASK_URL = "http://127.0.0.1:5001/configuracoes"

def setup_estufa(nome_planta_usuario):
    try:
        # 1. Traduz o nome digitado para o inglês (ex: feijão -> bean)
        nome_en = tradutor_en.translate(nome_planta_usuario)
        if not nome_en:
            print("❌ Erro ao traduzir o nome da planta.")
            return
            
        print(f"Buscando '{nome_en}' na Perenual API...")

        # 2. Requisição de busca por texto (Query Q) na API v2 da Perenual
        url = f"https://perenual.com/api/v2/species-list?key={PERENUAL_API_KEY}&q={nome_en.lower().strip()}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Erro na API externa Perenual: Status {response.status_code}")
            return

        dados_busca = response.json()
        lista_plantas = dados_busca.get('data', [])

        if not lista_plantas:
            print(f"❌ Erro: Nenhuma planta correspondente a '{nome_planta_usuario}' foi encontrada na base de dados.")
            return

        # Seleciona o primeiro resultado (geralmente o mais relevante do algoritmo de busca)
        planta_encontrada = lista_plantas[0]
        
        # 3. Mapeamento dos metadados de rega (watering) para limiares reais de umidade do solo
        rega_api = planta_encontrada.get('watering', 'average').lower()
        print(f"Nível de rega identificado na Perenual: {rega_api}")

        # Regra de negócio mapeada conforme os retornos textuais da documentação
        if "frequent" in rega_api:
            u_min, u_ideal = 60.0, 80.0
        elif "average" in rega_api:
            u_min, u_ideal = 45.0, 70.0
        else:
            u_min, u_ideal = 35.0, 55.0

        # Captura dados botânicos adicionais para enriquecer as considerações de cultivo no Dashboard
        nome_cientifico = planta_encontrada.get('scientific_name', ['Não informado'])[0]
        ciclo = planta_encontrada.get('cycle', 'Não informado')
        
        dicas_en = f"Nome científico: {nome_cientifico}. Ciclo de vida: {ciclo}. Necessidade de água definida na API como: {rega_api}."
        dicas_pt = tradutor_pt.translate(dicas_en)

        # 4. Estrutura o Payload JSON para submeter à API local Flask
        payload = {
            "nome_planta_pt": nome_planta_usuario.capitalize().strip(),
            "umidade_minima": u_min,
            "umidade_ideal": u_ideal,
            "info_cultivo_pt": dicas_pt
        }
        
        # Envia usando JSON de forma nativa e define os headers apropriados de aplicação
        headers = {'Content-Type': 'application/json'}
        res = requests.post(API_FLASK_URL, json=payload, headers=headers, timeout=5)
        
        if res.status_code == 200:
            print(f"\n[OK] Estufa configurada com sucesso no PostgreSQL para: {nome_planta_usuario}")
            print(f"-> Limiar Mínimo de Umidade para Atuação: {u_min}%")
            print(f"-> Alvo Ideal de Umidade: {u_ideal}%")
        else:
            print(f"❌ Falha ao salvar configurações na API interna: Código HTTP {res.status_code}")

    except requests.exceptions.Timeout:
        print("❌ Erro de Timeout: O servidor demorou muito para responder.")
    except Exception as e:
        print(f"❌ Erro crítico no fluxo de Setup: {e}")

if __name__ == "__main__":
    planta = input("Digite o nome da planta para configurar a estufa: ")
    if planta.strip():
        setup_estufa(planta)
    else:
        print("O nome da planta não pode ser vazio.")