import sqlite3
import time
import requests
import RPi.GPIO as GPIO
from datetime import datetime
import board
import adafruit_dht
import os

# --- CONFIGURAÇÕES DE HARDWARE ---
PINO_RELE_BOMBA = 17  # Pino do relé da bomba
GPIO.setmode(GPIO.BCM)
GPIO.setup(PINO_RELE_BOMBA, GPIO.OUT)
GPIO.output(PINO_RELE_BOMBA, GPIO.LOW)  # Começa desligada

# GPIO 4
dht_device = adafruit_dht.DHT22(board.D4)

# ip da esp (tirado do taura)
ESP_IP = "192.168.4.148"

# --- GERENCIAMENTO DE TEMPOS (Padrão de Produção) ---
INTERVALO_SENSORS = 30         # tempo de verificação dos sensores a cada 30 segundos
INTERVALO_FOTO = 12 * 60 * 60  # 12 horas


def ler_sensor():
    """Le o sensor DHT22 retornando (umidade, temperatura) ou (None, None)"""
    try:
        umidade = dht_device.humidity
        temperatura = dht_device.temperature
        if umidade is not None and temperatura is not None:
            return umidade, temperatura
    except RuntimeError as error:
        print(f"Aviso DHT22 (Flutuação de sinal): {error.args[0]}")
    return None, None


def ler_configuracoes():
    """Lê os limites de umidade definidos no Banco de Dados"""
    conn = sqlite3.connect('estufa.db')
    cursor = conn.cursor()
    cursor.execute("SELECT umidade_minima, umidade_ideal FROM configuracoes WHERE id=1")
    config = cursor.fetchone()
    conn.close()
    return config  # Retorna (minima, ideal)


def salvar_leitura(umidade, temperatura, foto_path):
    """Salva os dados atuais e o caminho da foto (se houver) no Banco de Dados"""
    conn = sqlite3.connect('estufa.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leituras_sensores (umidade_solo, temperatura, caminho_foto)
        VALUES (?, ?, ?)
    ''', (umidade, temperatura, foto_path))
    conn.commit()
    conn.close()


def loop_principal():
    print("Iniciando monitoramento comandado pela Raspberry Pi...")
    
    # checar se o repositório das fotos existe
    os.makedirs("fotos_proj_integrador", exist_ok=True)
    
    # Registra o timestamp da última foto (0 garante que tira uma foto logo ao iniciar o script)
    last_photo_time = 0 
    
    while True:
        # 1. Busca os limites atuais no Banco
        config = ler_configuracoes()
        u_min = config[0] if config else 40.0 # Fallback caso banco falhe
        
        # 2. Leitura controlada do sensor (máximo de 5 tentativas com intervalo)
        umidade_atual, temp_atual = None, None
        tentativas = 0
        while (umidade_atual is None or temp_atual is None) and tentativas < 5:
            umidade_atual, temp_atual = ler_sensor()
            if umidade_atual is None:
                tentativas += 1
                time.sleep(2.0) # Delay obrigatório entre tentativas de leitura do DHT
        
        # Se falhar totalmente, exibe erro mas não quebra o script
        if umidade_atual is None or temp_atual is None:
            print(f"[{datetime.now().strftime('%H:%M')}] ❌ Falha crítica: Não foi possível ler o DHT22 neste ciclo.")
        else:
            print(f"[{datetime.now().strftime('%H:%M')}] Umidade: {umidade_atual}% | Alvo Mínimo: {u_min}% | Temp: {temp_atual}°C")

            # 3. Lógica de Atuação (Bomba)
            if umidade_atual < u_min:
                print("Umidade abaixo do limite! Irrigando...")
                GPIO.output(PINO_RELE_BOMBA, GPIO.HIGH)
                time.sleep(4) 
                GPIO.output(PINO_RELE_BOMBA, GPIO.LOW)
                print("✅ Irrigação concluída.")

        # 4. Controle de Tempo Assíncrono para a Foto
        current_time = time.time()
        nome_foto = None  # Por padrão, não há foto nova neste ciclo de 1 minuto
        
        if current_time - last_photo_time >= INTERVALO_FOTO:
            print("📸 Intervalo de 12h atingido. Requisitando captura à ESP32-CAM...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_foto = f"fotos_proj_integrador/estufa_{timestamp}.jpg"
            
            try:
                # Timeout estendido para 10s para dar tempo da ESP ligar o flash/estabilizar
                res = requests.get(f"http://{ESP_IP}/capture", timeout=10)
                if res.status_code == 200:
                    with open(nome_foto, 'wb') as f:
                        f.write(res.content)
                    print(f"📸 Foto salva com sucesso: {nome_foto}")
                    last_photo_time = current_time  # Atualiza a marca temporal do sucesso
                else:
                    print(f"⚠️ ESP32 retornou erro HTTP: {res.status_code}")
                    nome_foto = None
            except Exception as e:
                print(f"❌ Falha ao comunicar com ESP32: {e}")
                nome_foto = None  # Força o script a tentar novamente no próximo ciclo de loop

        # 5. Registra tudo no banco para o Dashboard (mesmo se nome_foto for None)
        if umidade_atual is not None and temp_atual is not None:
            salvar_leitura(umidade_atual, temp_atual, nome_foto)

        # Aguarda o intervalo definido para checar os sensores novamente
        time.sleep(INTERVALO_SENSORS)


if __name__ == "__main__":
    try:
        loop_principal()
    except KeyboardInterrupt:
        print("\nFinalizando sistema...")
        GPIO.cleanup()
