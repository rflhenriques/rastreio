# Rastreio de Envios

Sistema web para acompanhar encomendas enviadas pelos Correios. Cada pedido recebe um **link único**, e o cliente abre esse link para ver, em uma página com a identidade da empresa, em que etapa está o envio: do fechamento do contrato até a entrega.

Desenvolvido para a **Lance Replay**, empresa de sistemas de gravação para quadras esportivas, que envia peças novas e de reposição aos seus clientes.

> **Status:** protótipo funcional com um provedor de rastreio **simulado**. A integração com a API Rastro dos Correios é o próximo passo (veja o [Roadmap](#roadmap)).


## O problema

Hoje o cliente recebe apenas o código de rastreio dos Correios e precisa consultá-lo em outro site. Isso traz três problemas:

- O rastreio dos Correios só existe **depois da postagem**, então o cliente fica sem informação entre o fechamento do pedido e o envio.
- Perguntas como "cadê a minha peça?" chegam ao suporte com frequência.
- A experiência não tem a marca da empresa.

## A solução

- A equipe cria o pedido no painel, e o sistema gera um **link único** com a mensagem pronta para colar no grupo de WhatsApp do cliente.
- O cliente acompanha as **etapas internas** (contrato fechado, em preparação, pronto para postagem) e as **etapas dos Correios** (postado, em trânsito, saiu para entrega, entregue) na mesma linha do tempo.
- Uma rotina agendada consulta o provedor de rastreio e atualiza os pedidos, sem trabalho manual.

## Funcionalidades

**Página pública do cliente** (`/rastreio/<token>`)

- Andamento em etapas e histórico completo, do evento mais recente para o mais antigo.
- Tema escuro e claro, com a escolha guardada no navegador.
- Prévia de compartilhamento (Open Graph) para o link no WhatsApp.
- Link inexistente mostra uma página genérica (404), sem revelar informações.

**Painel dos funcionários** (`/painel`)

- Login, logout e criação de usuários por comando de terminal (não há cadastro público).
- Lista de pedidos, criação de pedido (peça nova ou reposição) e página de detalhe.
- Avanço das etapas internas e cadastro do código de rastreio dos Correios, com consulta imediata.
- Botões para copiar o link e a mensagem do WhatsApp.
- Ações sem recarregar a página, com proteção contra clique duplo.

**Automação**

- Comando `atualizar-rastreios`, pensado para rodar agendado algumas vezes por dia.

## Como funciona

```
Funcionário ──► Painel (login) ──► Banco de dados ◄── Rotina agendada ──► Provedor de rastreio
                                         │                                 (simulado hoje,
                                         ▼                                  Correios depois)
                              Página pública (link único)
                                         │
                                         ▼
                              Cliente, pelo link no WhatsApp
```

A página pública **lê do banco de dados**, nunca da API de rastreio. A rotina agendada é quem consulta o provedor e grava os eventos.

## Decisões de projeto

| Decisão | Motivo |
|---|---|
| A página pública lê do banco, e uma rotina atualiza o banco | Página rápida, consumo da API previsível e continua funcionando se a API cair |
| Um token aleatório e longo **por pedido** | Um link vazado expõe uma encomenda, e não todo o histórico do cliente. O token não é sequencial, então não dá para adivinhar links |
| Provedores de rastreio plugáveis (`app/provedores/`) | Trocar o simulado pela API real é mudar uma variável de ambiente, sem tocar no resto |
| O provedor devolve o status no vocabulário do sistema | O atualizador não precisa conhecer o formato de cada API |
| O status só **avança**, nunca retrocede | Evita que uma resposta parcial ou fora de ordem faça o cliente ver "em trânsito" depois de "entregue" |
| Eventos repetidos são ignorados antes de gravar, e o banco tem restrição de unicidade | Rodar a atualização várias vezes não duplica o histórico |
| Datas guardadas em UTC e exibidas no horário de Brasília | O SQLite não guarda fuso, então a conversão acontece só na exibição |
| Regras de negócio em `app/servicos/`, fora das rotas | Dá para testá-las sem navegador e reaproveitá-las |
| Cada ação de avanço envia a etapa que a tela mostrava | Cliques duplos ou duas pessoas agindo ao mesmo tempo não pulam etapas |
| Fonte Inter hospedada no próprio sistema | Sem requisições a terceiros a cada visita (privacidade e desempenho) |

## Modelo de dados

- **Usuario:** nome, e-mail único e hash da senha.
- **Pedido:** token único, tipo de envio, nome do cliente, código de rastreio (opcional), status, datas.
- **Evento:** pedido, origem (interna ou Correios), descrição, local e momento. Uma restrição de unicidade impede eventos duplicados.

## Segurança

- Senhas guardadas apenas como hash.
- Proteção CSRF em todos os formulários e ações.
- O parâmetro `next` do login só aceita caminhos internos (sem redirecionamento para sites externos).
- Mesma mensagem para e-mail inexistente e senha errada.
- Página pública com `Cache-Control: no-store`, `Referrer-Policy: no-referrer` e `noindex`.
- HTML escapado automaticamente nos templates.
- Credenciais e segredos apenas em variáveis de ambiente (`.env`, fora do Git).

## Como rodar

Requisitos: Python 3.10 ou superior.

```powershell
# 1. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 2. Configuração
copy .env.example .env              # Linux/macOS: cp .env.example .env
# gere uma chave e cole no SECRET_KEY do .env:
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Banco de dados
flask --app app db upgrade

# 4. Primeiro usuário do painel
flask --app app criar-usuario

# 5. Servidor de desenvolvimento
flask --app app run --debug
```

O painel fica em `http://127.0.0.1:5000/painel/`. No Windows, o pacote `tzdata` (já no `requirements.txt`) é necessário para a conversão de fuso horário.

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SECRET_KEY` | Sim | Assina a sessão e os formulários. O app não sobe sem ela |
| `DATABASE_URL` | Não | Padrão: SQLite local em `instance/rastreio.db` |
| `PROVEDOR_RASTREIO` | Não | Provedor de rastreio. Padrão: `simulado` |
| `URL_BASE_PUBLICA` | Não | Endereço público do sistema, usado nos links e na prévia. Padrão: `http://127.0.0.1:5000` |
| `NOME_EMPRESA` | Não | Nome exibido nas páginas. Padrão: `Lance Replay` |

### Comandos

```powershell
flask --app app criar-usuario          # cria um usuário do painel
flask --app app atualizar-rastreios    # consulta o provedor e atualiza os pedidos em andamento
```

Para agendar a atualização, use o cron (Linux) ou o Agendador de Tarefas (Windows). Exemplo de cron, duas vezes ao dia:

```
0 8,18 * * * cd /caminho/do/projeto && .venv/bin/flask --app app atualizar-rastreios
```

### Provedor simulado

Para desenvolver e demonstrar sem depender dos Correios, o provedor simulado gera eventos a partir do momento em que o pedido ficou pronto para postagem, um a cada 2 minutos. O **código** define até onde o pacote chega:

| Código | Chega até |
|---|---|
| `AA000000005BR` | Postado |
| `AA000000001BR` | Em trânsito |
| `AA000000003BR` | Saiu para entrega |
| `AA000000004BR` | Entregue |

## Testes

```powershell
pytest                                          # roda toda a suíte
pytest --cov=app --cov-report=term-missing      # com relatório de cobertura
```

Os testes usam um banco SQLite em memória, recriado a cada teste, e um provedor de rastreio falso, então não dependem de rede nem do relógio. Cobrem as regras de negócio (etapas, código dos Correios, atualizador), o provedor simulado, os modelos, as rotas do painel (login, proteção, CSRF, ações), a página pública e os comandos de terminal.

## Estrutura do projeto

```
app/
├── __init__.py        # create_app() (a factory da aplicação)
├── models.py          # Usuario, Pedido, Evento
├── comandos.py        # comandos de terminal
├── painel/            # área dos funcionários
├── publico/           # página do cliente
├── provedores/        # contrato e provedores de rastreio
├── servicos/          # regras de negócio
├── static/            # CSS, JS, imagens e fonte
└── templates/
migrations/            # migrações do banco (Alembic)
tests/                 # testes automatizados
```

## Roadmap

- [ ] Provedor da **API Rastro dos Correios** (token por cartão de postagem, consulta de objetos), testado primeiro em homologação.
- [ ] Preparação para publicar: ponto de entrada WSGI, Dockerfile, HTTPS e agendamento.
- [ ] Limite de tentativas no login e na página pública, e páginas de erro 500 e 429.
- [ ] Previsão de entrega na página do cliente (a API Rastro devolve a data prevista).
- [ ] Editar e excluir pedidos no painel.
- [ ] Notificações automáticas ao cliente.

## Limitações conhecidas

- Não há "voltar etapa" nem edição de eventos no painel.
- O código de rastreio só pode ser trocado enquanto não houver eventos dos Correios.
- Duas requisições exatamente simultâneas ainda podem passar pela verificação de etapa; para o porte de uso previsto (uma equipe pequena), isso é aceitável.

## Créditos e licenças

- Fonte [Inter](https://github.com/rsms/inter), sob a licença SIL Open Font License 1.1 (arquivo em `app/static/fonts/`).
- O logotipo e as cores pertencem à Lance Replay.