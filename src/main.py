import machine
import time

# Constantes de Parametrizacao
LIMITE_TEMPO_X_MS = 4000
LIMITE_VARIACAO_Y_C = 3.0
MPU_ADDR = 0x68

# Configuracao de Hardware
btn1 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)

def ler_temperatura():
    """Le a temperatura do MPU6050 e converte para Celsius."""
    try:
        raw = i2c.readfrom_mem(MPU_ADDR, 0x41, 2)
        temp_raw = (raw[0] << 8) | raw[1]
        if temp_raw >= 0x8000:
            temp_raw -= 0x10000
        return (temp_raw / 340.0) + 36.53
    except Exception:
        # Retorna o valor base do Wokwi (aprox 36.53) caso dê erro, 
        # garantindo que o programa nunca trave
        return 36.53

# Inicializacao
time.sleep(0.1)
print("Sistema de Monitoramento Inicializado")

# Variaveis de Estado
t_referencia = ler_temperatura()
porta_aberta_desde = 0
em_alarme_porta = False
em_alarme_temp = False
porta_estava_aberta = False

# Loop Principal
while True:
    t_atual = ler_temperatura()
    if t_atual is None:
        time.sleep_ms(50)
        continue

    porta_aberta = (btn1.value() == 0)

    # Logica de Tempo de Porta Aberta
    if porta_aberta:
        if not porta_estava_aberta:
            porta_aberta_desde = time.ticks_ms()
            porta_estava_aberta = True
        tempo_aberta = time.ticks_diff(time.ticks_ms(), porta_aberta_desde)
        if tempo_aberta >= LIMITE_TEMPO_X_MS and not em_alarme_porta:
            em_alarme_porta = True
            print("ALERTA: Porta aberta por muito tempo!")
    else:
        porta_estava_aberta = False
        porta_aberta_desde = 0

    # Logica de Elevacao Termica
    delta_t = t_atual - t_referencia
    if delta_t >= LIMITE_VARIACAO_Y_C and not em_alarme_temp:
        em_alarme_temp = True
        print("ALERTA: Degradacao termica detectada!")

    # Rastreia a referencia para baixo quando nao ha alarmes.
    # Isso permite detectar subidas abruptas a partir da base mais baixa.
    if not em_alarme_temp and not em_alarme_porta:
        if t_atual < t_referencia:
            t_referencia = t_atual

    # Normalizacao
    if em_alarme_porta or em_alarme_temp:
        if not porta_aberta and abs(t_atual - t_referencia) < LIMITE_VARIACAO_Y_C:
            em_alarme_porta = False
            em_alarme_temp = False
            print("Status: Sistema Normalizado.")
            t_referencia = t_atual

    time.sleep_ms(50)
