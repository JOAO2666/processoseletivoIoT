import machine
import time

class MPU6050:
    def __init__(self, i2c_bus, addr=0x68):
        self.i2c = i2c_bus
        self.addr = addr
        self._acordar()
        time.sleep_ms(50)

    def _acordar(self):
        """Acorda o sensor MPU6050 retirando do modo sleep (0x6B = 0)."""
        try:
            self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')
        except Exception as e:
            print("I2C Error _acordar:", e)
            
    def ler_temperatura(self):
        """Le a temperatura do MPU6050 e converte para Celsius."""
        for tentativa in range(2):
            try:
                raw = self.i2c.readfrom_mem(self.addr, 0x41, 2)
                temp_raw = (raw[0] << 8) | raw[1]
                if temp_raw >= 0x8000:
                    temp_raw -= 0x10000
                return (temp_raw / 340.0) + 36.53
            except Exception as e:
                print("I2C Error:", e)
                if tentativa == 0:
                    self._acordar()
                    time.sleep_ms(20)
        return None

class SmartCooler:
    # Constantes de Parametrizacao
    LIMITE_TEMPO_X_MS = 5000
    LIMITE_VARIACAO_Y_C = 3.0

    def __init__(self, btn_pin, i2c_bus):
        self.btn = machine.Pin(btn_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self.sensor = MPU6050(i2c_bus)
        
        # Variaveis de Estado
        self.t_referencia = None
        self.porta_aberta_desde = 0
        self.em_alarme_porta = False
        self.em_alarme_temp = False
        self.porta_estava_aberta = False

    def run(self):
        print("Sistema de Monitoramento Inicializado")
        self.start_time = time.ticks_ms()
        time.sleep_ms(200)
        
        while True:
            t_atual = self.sensor.ler_temperatura()

            # 1. Logica de Tempo de Porta Aberta (Independente do sensor térmico)
            porta_aberta = (self.btn.value() == 0)
            
            if porta_aberta:
                if not self.porta_estava_aberta:
                    self.porta_aberta_desde = time.ticks_ms()
                    self.porta_estava_aberta = True
                
                tempo_aberta = time.ticks_diff(time.ticks_ms(), self.porta_aberta_desde)
                if tempo_aberta >= self.LIMITE_TEMPO_X_MS and not self.em_alarme_porta:
                    self.em_alarme_porta = True
                    print("ALERTA: Porta aberta por muito tempo!")
            else:
                self.porta_estava_aberta = False
                self.porta_aberta_desde = 0

            # 2. Logica Térmica (Só executa se o sensor estiver respondendo)
            if t_atual is not None:
                if self.t_referencia is None:
                    self.t_referencia = t_atual

                tempo_desde_inicio = time.ticks_diff(time.ticks_ms(), self.start_time)
                
                if tempo_desde_inicio < 800:
                    # Setup window: força a referência a acompanhar as mudanças iniciais do simulador
                    self.t_referencia = t_atual
                else:
                    # Aciona o alerta apenas se a variação para CIMA ultrapassar o limite.
                    if (t_atual - self.t_referencia) >= self.LIMITE_VARIACAO_Y_C and not self.em_alarme_temp:
                        self.em_alarme_temp = True
                        print("ALERTA: Degradacao termica detectada!")

                    # 3. Rastreamento Dinamico da Temperatura (Gatilho Base)
                    if not self.em_alarme_temp and not self.em_alarme_porta:
                        if t_atual < self.t_referencia:
                            self.t_referencia = t_atual

            # 4. Normalizacao Global
            if self.em_alarme_porta or self.em_alarme_temp:
                temp_normalizada = True
                if self.em_alarme_temp:
                    if t_atual is not None and self.t_referencia is not None:
                        if abs(t_atual - self.t_referencia) < self.LIMITE_VARIACAO_Y_C:
                            temp_normalizada = True
                        else:
                            temp_normalizada = False
                    else:
                        temp_normalizada = False
                        
                if not porta_aberta and temp_normalizada:
                    self.em_alarme_porta = False
                    self.em_alarme_temp = False
                    print("Status: Sistema Normalizado.")
                    if t_atual is not None:
                        self.t_referencia = t_atual

            # Intervalo do super-loop
            time.sleep_ms(50)

if __name__ == '__main__':
    # SoftI2C garante compatibilidade plena com o simulador Wokwi
    i2c = machine.SoftI2C(sda=machine.Pin(21), scl=machine.Pin(22), freq=100000)
    cooler = SmartCooler(btn_pin=4, i2c_bus=i2c)
    cooler.run()
