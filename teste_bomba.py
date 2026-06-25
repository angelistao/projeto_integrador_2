import RPi.GPIO as GPIO
import time

# Define o modo de numeração dos pinos como BCM (como no seu main_control.py)
GPIO.setmode(GPIO.BCM)

PINO_RELE_BOMBA = 11
GPIO.setup(PINO_RELE_BOMBA, GPIO.OUT)

try:
    print("--- INICIANDO TESTE DO RELÉ ---")
    
    print("Enviando sinal ALTO (HIGH) para o pino 11... [Bomba deve LIGAR]")
    GPIO.output(PINO_RELE_BOMBA, GPIO.HIGH)
    
    # Mantém ligado por 3 segundos para teste seguro
    time.sleep(3)
    
    print("Enviando sinal BAIXO (LOW) para o pino 11... [Bomba deve DESLIGAR]")
    GPIO.output(PINO_RELE_BOMBA, GPIO.LOW)
    
    print("--- TESTE CONCLUÍDO COM SUCESSO ---")

except KeyboardInterrupt:
    print("\nTeste interrompido pelo usuário.")

finally:
    # Limpa as configurações de GPIO para segurança do hardware
    GPIO.cleanup()
    print("GPIO limpo e liberado.")