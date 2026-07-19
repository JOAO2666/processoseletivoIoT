import machine
import time

# Constantes de Parametrizacao
LIMITE_TEMPO_X_MS = 5000
LIMITE_VARIACAO_Y_C = 3.0
MPU_ADDR = 0x68

# Configuracao de Hardware
btn1 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
# Usar Hardware I2C (mais estável no Wokwi)
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
MPU_ADDR_REAL = 0x68

def ler_temperatura():
    """Le a temperatura do MPU6050 e converte para Celsius."""
    for tentativa in range(2):
        try:
            raw = i2c.readfrom_mem(MPU_ADDR_REAL, 0x41, 2)
            temp_raw = (raw[0] << 8) | raw[1]
            if temp_raw >= 0x8000:
                temp_raw -= 0x10000
            return (temp_raw / 340.0) + 36.53
        except Exception:
            if tentativa == 0:
                acordar_mpu()
                time.sleep_ms(20)

    # Retorna None caso haja falha de leitura (fallback elegante sem hardcodes)
    return None

def acordar_mpu():
    """Acorda o sensor MPU6050 retirando do modo sleep (0x6B = 0)."""
    try:
        i2c.writeto_mem(MPU_ADDR_REAL, 0x6B, b'\x00')
    except Exception:
        pass

# Inicializacao
acordar_mpu()
time.sleep(0.1)
print("Sistema de Monitoramento Inicializado")

# Variaveis de Estado
t_referencia = None
porta_aberta_desde = 0
em_alarme_porta = False
em_alarme_temp = False
porta_estava_aberta = False

# Loop Principal
while True:
    t_atual = ler_temperatura()

    # 1. Logica de Tempo de Porta Aberta (Independente do sensor térmico)
    porta_aberta = (btn1.value() == 0)
    
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

    # 2. Logica Térmica (Só executa se o sensor estiver respondendo)
    if t_atual is not None:
        # Inicializa a referência apenas na primeira leitura bem sucedida
        if t_referencia is None:
            t_referencia = t_atual

        # Aciona o alerta apenas se a variação para CIMA ultrapassar o limite.
        if (t_atual - t_referencia) >= LIMITE_VARIACAO_Y_C and not em_alarme_temp:
            em_alarme_temp = True
            print("ALERTA: Degradacao termica detectada!")

        # 3. Rastreamento Dinamico da Temperatura (Gatilho Base)
        # Se a temperatura cair de forma natural, adotamos ela como nova referência base.
        if not em_alarme_temp and not em_alarme_porta:
            if t_atual < t_referencia:
                t_referencia = t_atual

    # 4. Normalizacao Global
    # Se o sistema estava em alarme, ele só normaliza quando a porta é fechada E a temperatura volta a ficar próxima à referência
    if em_alarme_porta or em_alarme_temp:
        # A temperatura só impede a normalização se estiver em alarme
        temp_normalizada = True
        if em_alarme_temp:
            if t_atual is not None and t_referencia is not None:
                if abs(t_atual - t_referencia) < LIMITE_VARIACAO_Y_C:
                    temp_normalizada = True
                else:
                    temp_normalizada = False
            else:
                temp_normalizada = False # Se o sensor falhou em alarme, espera voltar
                
        if not porta_aberta and temp_normalizada:
            em_alarme_porta = False
            em_alarme_temp = False
            print("Status: Sistema Normalizado.")
            if t_atual is not None:
                t_referencia = t_atual

    # Intervalo do super-loop
    time.sleep_ms(50)
