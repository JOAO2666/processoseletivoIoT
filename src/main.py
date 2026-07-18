import machine
import time

# Constantes de Parametrizacao
LIMITE_TEMPO_X_MS = 5000
LIMITE_VARIACAO_Y_C = 3.0
MPU_ADDR = 0x68

# Configuracao de Hardware
btn1 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
# Usar SoftI2C aumenta significativamente a compatibilidade no Wokwi para não travar o barramento
i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)

def ler_temperatura():
    """Le a temperatura do MPU6050 e converte para Celsius."""
    try:
        raw = i2c.readfrom_mem(MPU_ADDR, 0x41, 2)
        temp_raw = (raw[0] << 8) | raw[1]
        if temp_raw >= 0x8000:
            temp_raw -= 0x10000
        return (temp_raw / 340.0) + 36.53
    except Exception:
        # Se houver falha de barramento no simulador, retorna None para a lógica não atuar com dados corrompidos
        return None

# Inicializacao
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
    
    # Tolerância a falhas do sensor: pula a iteração se a leitura falhar
    if t_atual is None:
        time.sleep_ms(50)
        continue
        
    # Inicializa a referência apenas na primeira leitura bem sucedida
    if t_referencia is None:
        t_referencia = t_atual

    porta_aberta = (btn1.value() == 0)

    # 1. Logica de Tempo de Porta Aberta
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

    # 2. Logica de Elevacao Termica (Gatilho)
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
        if not porta_aberta and abs(t_atual - t_referencia) < LIMITE_VARIACAO_Y_C:
            em_alarme_porta = False
            em_alarme_temp = False
            print("Status: Sistema Normalizado.")
            # Ao normalizar, atualiza a referência para a temperatura atual, garantindo estabilidade
            t_referencia = t_atual

    # Intervalo do super-loop
    time.sleep_ms(50)
