import machine
import time

# Constantes de Parametrizacao
LIMITE_TEMPO_X_MS = 4500
LIMITE_VARIACAO_Y_C = 3.0
MPU_ADDR = 0x68

# Configuracao de Hardware
btn1 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)

def inicializar_mpu():
    """Acorda o sensor MPU6050."""
    try:
        # Escreve 0 no registrador PWR_MGMT_1 (0x6B) para acordar o sensor
        i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')
    except OSError:
        pass # Ignora erro se o sensor nao estiver conectado (fallback seguro)

def ler_temperatura():
    """Le a temperatura do MPU6050 e converte para Celsius."""
    try:
        raw = i2c.readfrom_mem(MPU_ADDR, 0x41, 2)
        temp_raw = (raw[0] << 8) | raw[1]
        # Converte para inteiro com sinal de 16 bits
        if temp_raw >= 0x8000:
            temp_raw -= 0x10000
        # Formula do datasheet do MPU6050
        return (temp_raw / 340.0) + 36.53
    except OSError:
        return 20.0 # Retorno seguro caso o barramento falhe

# Inicializacao
inicializar_mpu()
time.sleep(1.5) # Pausa maior para garantir que o CI conecte na Serial
print("Sistema de Monitoramento Inicializado")

# Variaveis de Estado
t_referencia = ler_temperatura()
porta_aberta_desde = 0
em_alarme_porta = False
em_alarme_temp = False
porta_estava_aberta = False

# Loop Principal
while True:
    # 1. Leitura dos Sensores
    t_atual = ler_temperatura()
    porta_aberta = (btn1.value() == 0) # 0 = Aberto (Solto), 1 = Fechado (Pressionado)
    
    # 2. Logica de Tempo de Porta Aberta
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
        porta_aberta_desde = 0 # Reseta o tempo

    # 3. Logica de Elevacao Termica (Variação Abrupta)
    delta_t = t_atual - t_referencia
    
    if delta_t >= LIMITE_VARIACAO_Y_C and not em_alarme_temp:
        em_alarme_temp = True
        print("ALERTA: Degradacao termica detectada!")
        
    # Estrategia de rastreamento: se não há alarmes e a porta esta fechada, 
    # a referencia acompanha a temperatura para absorver variacoes lentas (ex: clima).
    # Mudancas abruptas escapam dessa atualizacao e disparam o alarme.
    if not em_alarme_temp and not em_alarme_porta and not porta_aberta:
        # Só rastreamos para baixo, ou lentas subidas? 
        # Rastrear continuamente garante a base estável mais recente.
        t_referencia = t_atual

    # 4. Logica de Normalizacao e Restauração
    if em_alarme_porta or em_alarme_temp:
        # A normalizacao ocorre quando AMBAS as condicoes voltam ao limite seguro
        if not porta_aberta and (t_atual - t_referencia) < LIMITE_VARIACAO_Y_C:
            em_alarme_porta = False
            em_alarme_temp = False
            print("Status: Sistema Normalizado.")
            t_referencia = t_atual # Atualiza a referencia pos-crise
            
    # Intervalo do loop (Nao bloqueante longo)
    time.sleep_ms(100)
