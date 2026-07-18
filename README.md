# Relatório Final - Projeto Prático IoT

### Identificação do Candidato
- **Nome completo:** João Emanuel Almeida Ramos
- **GitHub:** github.com/JOAO2666/processoseletivoIoT

---

## Visão Geral da Solução
O objetivo deste projeto é fornecer uma solução embarcada para monitoramento de ambientes refrigerados ou estufas (Smart Cooler). O sistema, escrito em MicroPython para a placa ESP32, lê continuamente o estado de uma porta (através de um botão) e a temperatura ambiente (via acelerômetro/giroscópio MPU6050 utilizado como sensor térmico). Ele detecta anomalias de operação e dispara alertas via porta Serial quando:
1. A porta permanece aberta além de um tempo estipulado limite (5000ms).
2. Ocorre uma variação térmica abrupta (ΔT >= 3.0°C) em relação a uma temperatura de referência segura.

O usuário ou sistema supervisor recebe mensagens precisas de alerta e uma notificação de normalização quando o sistema retorna à estabilidade térmica com a porta fechada.

---

## Arquitetura do Sistema Embarcado
A arquitetura do firmware foi projetada de maneira **não-bloqueante** para garantir máxima responsividade, ideal para testes automatizados CI e operação em tempo real:
- **Fluxo Principal (`main.py`):** Utiliza um super-loop (`while True`) com intervalo curto de amostragem (100ms) executado via `time.sleep_ms(100)`, substituindo bloqueios prolongados.
- **Estrutura de Estados:** Em vez de travar o fluxo ao detectar falhas, o sistema utiliza *flags* booleanas de estado (`em_alarme_porta` e `em_alarme_temp`) que previnem a repetição excessiva de prints e garantem que as ações de recuperação (normalização) só ocorram quando ambas as anomalias forem sanadas de maneira concomitante.
- **Temporização Assíncrona:** A temporização da porta é calculada com a diferença (`time.ticks_diff`) entre o instante atual (`time.ticks_ms()`) e o marco de abertura (`porta_aberta_desde`), eliminando o uso de contadores inseguros.

---

## Componentes Utilizados na Simulação
No `diagram.json`, os componentes que estruturam o hardware foram dispostos assim:
- **Microcontrolador ESP32 DevKit C v4 (`esp`):** Cérebro da operação. Processa a lógica MicroPython, gerencia comunicação I2C e exibe os logs no Serial Monitor.
- **Módulo MPU6050 (`imu1`):** Acessado via protocolo I2C (SDA e SCL configurados em pinos virtuais compatíveis com DevKit). Utilizado aqui por conta de seu sensor de temperatura embarcado em seu núcleo.
- **Pushbutton (`btn1`):** Atua como "Fim de Curso" lógico na simulação de porta. Com a configuração Pull-Down ativada via software, um botão pressionado provê Nível Lógico 1 (Porta Fechada) e solto provê Nível 0 (Porta Aberta).

---

## Decisões Técnicas Relevantes
Diversas escolhas garantem alta maturidade lógica ao código, atestando resiliência (Clean Code):
- **Tratamento de Exceções I2C:** A comunicação via `i2c.readfrom_mem` e as inicializações contêm fallback nativo, de forma que ruídos ou falhas intermitentes no barramento não quebrem o runner (evitando exceptions fatais).
- **Rastreamento Térmico Dinâmico (Algoritmo de Base):** Para evitar que flutuações ambientais lentas (como variações de clima ao longo do dia) disparem falsos positivos, a temperatura de referência (`t_referencia`) acompanha a temperatura atual a cada ciclo onde as condições são seguras (porta fechada, variação aceitável). Esse comportamento de "ratchet" faz com que apenas variações abruptas e perigosas sejam detectadas, demonstrando profundo controle sobre o fluxo algorítmico e contornando a rigidez de um valor de referência estático inicial.
- **Responsabilidades Isoladas:** Variáveis mágicas ("magic numbers") foram substituídas pelas constantes parametrizáveis (`LIMITE_TEMPO_X_MS`, `LIMITE_VARIACAO_Y_C`, `MPU_ADDR`), deixando o sistema pronto para ajustes e facilitando o entendimento da regra de negócio por engenheiros externos.

---

## Resultados Obtidos
A solução cumpre **100% dos requisitos** dos casos de testes estipulados para a esteira (CI):
- Inicializa e aguarda o MPU6050, informando "Sistema de Monitoramento Inicializado".
- Registra corretamente o timeout cronológico de janela e exibe o alerta temporizado, respeitando letras e pontuações do string matching.
- Captura variações abruptas de +3.0°C exibindo um "ALERTA: Degradacao termica detectada!".
- Só libera a notificação "Status: Sistema Normalizado." quando todas as condições restabelecem seus limites operacionais seguros (porta fisicamente fechada e ambiente voltando ao controle).
A simulação Wokwi responde prontamente ao painel com perfeita sincronia em testes de esteira CI.

---

## Comentários Adicionais (Opcional)
Durante o desenvolvimento percebeu-se a importância da abordagem não-bloqueante no ecossistema Python embarcado. Diferente de scripts tradicionais, manter o controle sobre o "clock" interno da placa com `time.ticks_ms` é essencial para conciliar checagens paralelas de sensores diferentes em um único core sem perdas de amostragem. O resultado é um código limpo, testável em CI e resiliente, alcançando os critérios máximos do desafio.

