import time
import logging
import psycopg2
from gpiozero import OutputDevice
import board
import adafruit_dht

# --- CONFIGURAÇÕES ---
# Pinos e Hardware
PINO_BOMBA = 17
SENSOR_DHT = board.D4
UMIDADE_MINIMA = 40.0

# Configuração PostgreSQL
DB_CONFIG = {
    "host": "192.168.x.x",  # Substitua pelo IP do seu servidor
    "database": "estufa_db",
    "user": "seu_usuario",
    "password": "sua_senha",
    "port": 5432
}

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def enviar_para_postgres(umidade, temp):
    """Tenta enviar dados para o servidor remoto."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO leituras (umidade_solo, temperatura, timestamp) VALUES (%s, %s, NOW())",
            (umidade, temp)
        )
        conn.commit()
        cur.close()
    except Exception as e:
        logging.error(f"Falha ao conectar no Postgres: {e}")
    finally:
        if conn:
            conn.close()

def main():
    # Inicialização do Hardware
    bomba = OutputDevice(PINO_BOMBA, initial_value=False, active_high=True)
    dht_device = adafruit_dht.DHT22(SENSOR_DHT)
    
    logging.info("Sistema de estufa iniciado.")

    while True:
        try:
            # Leitura do sensor
            umidade = dht_device.humidity
            temperatura = dht_device.temperature

            if umidade is not None and temperatura is not None:
                logging.info(f"Leitura: {umidade}% - {temperatura}°C")
                
                # Envio Remoto
                enviar_para_postgres(umidade, temperatura)

                # Lógica de Irrigação (Independente do banco)
                if umidade < UMIDADE_MINIMA:
                    logging.warning("Umidade baixa! Acionando bomba.")
                    bomba.on()
                    time.sleep(4)
                    bomba.off()
                    logging.info("Irrigação finalizada.")
            else:
                logging.error("Falha ao ler DHT22.")
        
        except Exception as e:
            logging.error(f"Erro no ciclo principal: {e}")

        time.sleep(30) # Intervalo de 30 segundos

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Sistema encerrado pelo usuário.")
