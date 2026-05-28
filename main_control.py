import sqlite3
import time
import requests
import RPi.GPIO as GPIO
from datetime import datetime
import board
import adafruit_dht

# --- CONFIGURAÇÕES DE HARDWARE ---
PINO_RELE_BOMBA = 17  # pino rele
GPIO.setmode(GPIO.BCM)
GPIO.setup(PINO_RELE_BOMBA, GPIO.OUT)
GPIO.output(PINO_RELE_BOMBA, GPIO.LOW) # Começa desligada
dht_device = adafruit_dht.DHT22(board.D4) #Configuração do sensor de umidade no gpio 4

# --- CONFIGURAÇÕES DA ESP32-CAM ---
ESP_IP = "192.168.x.x" # ip que vou anotar do lab



def ler_sensor():
    dadosSensor = [0.0, 0.0] #array para armazenar a umidade e a temperatura, respectivamente
    try:
        dadosSensor[0] = dht_device.humidity
        dadosSensor[1] = dht_device.temperature
        if dadosSensor[0] is not None and dadosSensor[1] is not None:
            print("leitura feita com sucesso")
        else:
            print("falha na leitura")
    except RuntimeError as error:
        time.sleep(2.0)
        dadosSensor = [None, None]
    return dadosSensor
    

def ler_configuracoes():
    """Lê os limites de umidade definidos pelo script de setup"""
    conn = sqlite3.connect('estufa.db')
    cursor = conn.cursor()
    cursor.execute("SELECT umidade_minima, umidade_ideal FROM configuracoes WHERE id=1")
    config = cursor.fetchone()
    conn.close()
    return config # Retorna (minima, ideal)

def salvar_leitura(umidade, temperatura, foto_path):
    """Salva os dados atuais e o caminho da foto para o Dashboard"""
    conn = sqlite3.connect('estufa.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leituras_sensores (umidade_solo, temperatura, caminho_foto)
        VALUES (?, ?, ?)
    ''', (umidade, temperatura, foto_path))
    conn.commit()
    conn.close()

def loop_principal():
    print("Iniciando monitoramento em tempo real...")
    
    while True:
        # 1. Busca os limites atuais no Banco
        u_min, u_ideal = ler_configuracoes()
        
        
        # 2. leitura do sensor
        umidade_atual = None
        temp_atual = None
        while(umidade_atual == None or temp_atual == None):
           dadosSensor = ler_sensor()
            umidade_atual = dadosSensor[0]  # Leitura da umidade
            temp_atual = dadosSensor[1]  # Leitura da temperatura
        
        print(f"[{datetime.now().strftime('%H:%M')}] Umidade: {umidade_atual}% | Alvo: {u_min}%")

        # 3. Lógica de Atuação (Bomba)
        if umidade_atual < u_min:
            print("⚠️ Umidade abaixo do limite! Irrigando...")
            GPIO.output(PINO_RELE_BOMBA, GPIO.HIGH)
            time.sleep(5) # Tempo de rega definido
            GPIO.output(PINO_RELE_BOMBA, GPIO.LOW)
            print("✅ Irrigação concluída.")

        # 4. Captura de Foto na ESP32-CAM
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_foto = f"fotos_proj_integrador/estufa_{timestamp}.jpg"
        
        try:
            res = requests.get(f"http://{ESP_IP}/capture", timeout=5)
            if res.status_code == 200:
                with open(nome_foto, 'wb') as f:
                    f.write(res.content)
                print(f"📸 Foto salva: {nome_foto}")
            
            # 5. Registra tudo no banco para o Dashboard
            salvar_leitura(umidade_atual, temp_atual, nome_foto)
            
        except Exception as e:
            print(f"❌ Falha ao comunicar com ESP32: {e}")

        # Aguarda 1 minuto para a próxima verificação (ou o tempo que preferir)
        time.sleep(60)

if __name__ == "__main__":
    try:
        loop_principal()
    except KeyboardInterrupt:
        print("\nFinalizando sistema...")
        GPIO.cleanup()
