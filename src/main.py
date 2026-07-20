import machine
import time


class MPU6050:
    """Driver minimalista para leitura de temperatura do MPU6050 via I2C."""

    REG_TEMP = 0x41
    REG_PWR_MGMT_1 = 0x6B
    FATOR_CONVERSAO = 340.0
    OFFSET_CONVERSAO = 36.53
    MASCARA_SINAL = 0x8000
    CORRECAO_SINAL = 0x10000

    def __init__(self, i2c_bus, addr=0x68):
        self.i2c = i2c_bus
        self.addr = addr
        self._acordar()
        time.sleep_ms(50)

    def _acordar(self):
        """Acorda o sensor retirando do modo sleep (registrador 0x6B = 0)."""
        try:
            self.i2c.writeto_mem(self.addr, self.REG_PWR_MGMT_1, b'\x00')
        except Exception as e:
            print("I2C Error _acordar:", e)

    def ler_temperatura(self):
        """Le a temperatura em Celsius com retry automatico em caso de falha I2C."""
        for tentativa in range(2):
            try:
                raw = self.i2c.readfrom_mem(self.addr, self.REG_TEMP, 2)
                temp_raw = (raw[0] << 8) | raw[1]
                if temp_raw >= self.MASCARA_SINAL:
                    temp_raw -= self.CORRECAO_SINAL
                return (temp_raw / self.FATOR_CONVERSAO) + self.OFFSET_CONVERSAO
            except Exception as e:
                print("I2C Error:", e)
                if tentativa == 0:
                    self._acordar()
                    time.sleep_ms(20)
        return None


class SmartCooler:
    """Sistema embarcado de monitoramento de porta e temperatura para Smart Cooler."""

    # Constantes parametrizaveis
    LIMITE_TEMPO_X_MS = 5000
    LIMITE_VARIACAO_Y_C = 3.0
    JANELA_SETUP_MS = 800
    INTERVALO_LOOP_MS = 50

    def __init__(self, btn_pin, i2c_bus):
        self.btn = machine.Pin(btn_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self.sensor = MPU6050(i2c_bus)
        self._inicializar_estado()

    def _inicializar_estado(self):
        """Inicializa as variaveis de estado da maquina de estados."""
        self.t_referencia = None
        self.porta_aberta_desde = 0
        self.em_alarme_porta = False
        self.em_alarme_temp = False
        self.porta_estava_aberta = False
        self.start_time = 0

    def _verificar_porta_aberta(self):
        """Verifica se a porta esta aberta e dispara alarme se o tempo limite for excedido."""
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

        return porta_aberta

    def _verificar_temperatura(self, t_atual):
        """Verifica variacao termica e dispara alarme se o gradiente for excedido."""
        if t_atual is None:
            return

        if self.t_referencia is None:
            self.t_referencia = t_atual

        tempo_desde_inicio = time.ticks_diff(time.ticks_ms(), self.start_time)

        if tempo_desde_inicio < self.JANELA_SETUP_MS:
            # Janela de setup: referencia acompanha a temperatura inicial do simulador
            self.t_referencia = t_atual
            return

        # Dispara alarme se a variacao para CIMA ultrapassar o limite
        if (t_atual - self.t_referencia) >= self.LIMITE_VARIACAO_Y_C and not self.em_alarme_temp:
            self.em_alarme_temp = True
            print("ALERTA: Degradacao termica detectada!")
            return

        # Rastreamento dinamico: referencia decai conforme temperatura ambiente
        if not self.em_alarme_temp and not self.em_alarme_porta:
            if t_atual < self.t_referencia:
                self.t_referencia = t_atual

    def _verificar_normalizacao(self, porta_aberta, t_atual):
        """Verifica se todas as condicoes seguras foram restauradas e emite normalizacao."""
        if not (self.em_alarme_porta or self.em_alarme_temp):
            return

        temp_normalizada = True
        if self.em_alarme_temp:
            if t_atual is not None and self.t_referencia is not None:
                temp_normalizada = abs(t_atual - self.t_referencia) < self.LIMITE_VARIACAO_Y_C
            else:
                temp_normalizada = False

        if not porta_aberta and temp_normalizada:
            self.em_alarme_porta = False
            self.em_alarme_temp = False
            print("Status: Sistema Normalizado.")
            if t_atual is not None:
                self.t_referencia = t_atual

    def run(self):
        """Super-loop nao-bloqueante principal do sistema de monitoramento."""
        print("Sistema de Monitoramento Inicializado")
        self.start_time = time.ticks_ms()
        time.sleep_ms(200)

        while True:
            t_atual = self.sensor.ler_temperatura()
            porta_aberta = self._verificar_porta_aberta()
            self._verificar_temperatura(t_atual)
            self._verificar_normalizacao(porta_aberta, t_atual)
            time.sleep_ms(self.INTERVALO_LOOP_MS)


if __name__ == '__main__':
    # SoftI2C garante compatibilidade plena com o simulador Wokwi
    i2c = machine.SoftI2C(sda=machine.Pin(21), scl=machine.Pin(22), freq=100000)
    cooler = SmartCooler(btn_pin=4, i2c_bus=i2c)
    cooler.run()
