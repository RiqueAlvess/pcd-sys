# Chat Feature - Sistema PCD

## Resumo

O sistema de chat permite a comunicação direta entre **Empresas** e **PCDs** (Pessoas com Deficiência) através de conversas relacionadas a vagas de emprego e candidaturas.

## Arquitetura

### 1. Modelos de Banco de Dados

#### Conversa (userpcd/models.py:174-201)
Representa uma conversa entre uma empresa e um PCD sobre uma vaga específica.

**Campos:**
- `pcd` (ForeignKey) - Referência ao perfil PCD
- `empresa` (ForeignKey) - Referência à empresa
- `vaga` (ForeignKey, opcional) - Vaga relacionada à conversa
- `candidatura` (ForeignKey, opcional) - Candidatura relacionada
- `criada_em` (DateTime) - Data de criação
- `atualizada_em` (DateTime) - Data da última atualização

**Métodos:**
- `mensagens_nao_lidas_pcd()` - Conta mensagens não lidas pelo PCD
- `mensagens_nao_lidas_empresa()` - Conta mensagens não lidas pela empresa
- `ultima_mensagem()` - Retorna a última mensagem da conversa

**Regras:**
- Única por combinação (pcd, empresa, vaga)
- Ordenada por atualização mais recente

#### Mensagem (userpcd/models.py:203-222)
Representa uma mensagem individual dentro de uma conversa.

**Campos:**
- `conversa` (ForeignKey) - Conversa à qual a mensagem pertence
- `remetente_empresa` (Boolean) - True se remetente é empresa, False se é PCD
- `conteudo` (TextField) - Conteúdo da mensagem
- `lida` (Boolean) - Indica se a mensagem foi lida
- `enviada_em` (DateTime) - Data/hora de envio

**Métodos:**
- `marcar_como_lida()` - Marca a mensagem como lida

### 2. Views Backend

#### PCD Views (userpcd/views.py)

**lista_conversas_pcd (linha 388-416)**
- URL: `/pcd/chat/`
- Lista todas as conversas do PCD
- Mostra última mensagem e contador de não lidas
- Paginação: 15 conversas por página

**sala_chat_pcd (linha 420-475)**
- URL: `/pcd/chat/<conversa_id>/`
- Exibe sala de chat com mensagens
- POST: Envia nova mensagem
- Marca mensagens da empresa como lidas automaticamente

#### Empresa Views (usercompany/views.py)

**lista_conversas_empresa (linha 673-701)**
- URL: `/empresa/chat/`
- Lista todas as conversas da empresa
- Mostra última mensagem e contador de não lidas
- Paginação: 15 conversas por página

**sala_chat_empresa (linha 705-760)**
- URL: `/empresa/chat/<conversa_id>/`
- Exibe sala de chat com mensagens
- POST: Envia nova mensagem
- Marca mensagens do PCD como lidas automaticamente

**iniciar_conversa (linha 764-790)**
- URL: `/empresa/candidatos/<candidatura_id>/iniciar-conversa/`
- Inicia ou retorna conversa existente
- Apenas empresa pode iniciar conversas
- Cria conversa associada à candidatura e vaga

### 3. API RESTful

#### API PCD (userpcd/api_views.py:148-236)

**ConversaViewSet**
- Base URL: `/api/pcd/conversas/`

**Endpoints:**
- `GET /api/pcd/conversas/` - Lista todas as conversas
- `GET /api/pcd/conversas/{id}/` - Detalhes da conversa com mensagens
- `POST /api/pcd/conversas/{id}/send_message/` - Envia mensagem

**Exemplo POST:**
```json
{
  "conteudo": "Olá, gostaria de mais informações sobre a vaga."
}
```

#### API Empresa (usercompany/api_views.py:358-430)

**ConversaEmpresaViewSet**
- Base URL: `/api/empresa/conversas/`

**Endpoints:**
- `GET /api/empresa/conversas/` - Lista todas as conversas
- `GET /api/empresa/conversas/{id}/` - Detalhes da conversa com mensagens
- `POST /api/empresa/conversas/{id}/send_message/` - Envia mensagem

**Exemplo POST:**
```json
{
  "conteudo": "Obrigado pelo interesse. Gostaríamos de agendar uma entrevista."
}
```

### 4. Serializers (userpcd/serializers.py)

**MensagemSerializer (linha 145-164)**
- Serializa mensagens
- Inclui identificação do remetente (PCD ou empresa)

**ConversaSerializer (linha 166-197)**
- Serializa conversas
- Inclui última mensagem
- Conta mensagens não lidas baseado no usuário

### 5. Templates Frontend

#### PCD Templates

**lista_conversas_pcd.html** (`templates/userpcd/lista_conversas_pcd.html`)
- Lista de conversas com empresas
- Badge de contador de mensagens não lidas
- Avatar circular com inicial da empresa
- Link para cada sala de chat

**sala_chat_pcd.html** (`templates/userpcd/sala_chat_pcd.html`)
- Interface de chat com mensagens
- Mensagens do PCD: azul, à direita
- Mensagens da empresa: cinza, à esquerda
- Auto-scroll para última mensagem
- Auto-refresh a cada 10 segundos
- Formulário de envio de mensagem

#### Empresa Templates

**lista_conversas_empresa.html** (`templates/usercompany/lista_conversas_empresa.html`)
- Lista de conversas com candidatos
- Badge de contador de mensagens não lidas
- Avatar circular com inicial do candidato
- Link para cada sala de chat

**sala_chat_empresa.html** (`templates/usercompany/sala_chat_empresa.html`)
- Interface de chat com mensagens
- Mensagens da empresa: roxo, à direita
- Mensagens do PCD: cinza, à esquerda
- Auto-scroll para última mensagem
- Auto-refresh a cada 10 segundos
- Formulário de envio de mensagem
- Link para visualizar currículo do candidato

### 6. Rotas URL

#### URLs PCD (userpcd/urls.py:25-26)
```python
path('chat/', views.lista_conversas_pcd, name='lista_conversas_pcd'),
path('chat/<int:conversa_id>/', views.sala_chat_pcd, name='sala_chat_pcd'),
```

#### URLs Empresa (usercompany/urls.py:28-30)
```python
path('chat/', views.lista_conversas_empresa, name='lista_conversas_empresa'),
path('chat/<int:conversa_id>/', views.sala_chat_empresa, name='sala_chat_empresa'),
path('candidatos/<int:candidatura_id>/iniciar-conversa/', views.iniciar_conversa, name='iniciar_conversa'),
```

#### URLs API PCD (userpcd/urls_api.py:16)
```python
router.register(r'conversas', ConversaViewSet, basename='conversa')
```

#### URLs API Empresa (usercompany/urls_api.py:20)
```python
router.register(r'conversas', ConversaEmpresaViewSet, basename='conversa-empresa')
```

## Fluxo de Uso

### 1. Iniciar Conversa (Empresa)
1. Empresa visualiza candidatos de uma vaga
2. Clica em "Iniciar Conversa" para um candidato específico
3. Sistema cria ou retorna conversa existente
4. Empresa é redirecionada para sala de chat

### 2. Enviar Mensagem
1. Usuário (empresa ou PCD) acessa sala de chat
2. Digita mensagem no formulário
3. Clica em "Enviar"
4. Mensagem é salva no banco de dados
5. Timestamp da conversa é atualizado
6. Página recarrega mostrando nova mensagem

### 3. Receber Mensagens
1. Usuário acessa lista de conversas
2. Badge mostra número de mensagens não lidas
3. Ao abrir sala de chat, mensagens são marcadas como lidas
4. Auto-refresh mantém chat atualizado

### 4. Via API
1. Aplicação faz request GET para listar conversas
2. Faz request GET para obter mensagens de conversa específica
3. Faz request POST para enviar nova mensagem
4. Sistema retorna mensagem criada em JSON

## Recursos Implementados

✅ **Backend Completo**
- Modelos Conversa e Mensagem
- Views para PCD e Empresa
- API RESTful para ambos os tipos de usuário
- Serializers para JSON
- Migrations aplicadas

✅ **Frontend Completo**
- Templates HTML/CSS responsivos
- Lista de conversas com badges
- Sala de chat interativa
- Auto-scroll e auto-refresh
- Formulários de envio

✅ **Funcionalidades**
- Marcação automática de leitura
- Contadores de mensagens não lidas
- Associação com vagas e candidaturas
- Paginação de conversas
- Identificação visual de remetente

## Segurança

- ✅ Autenticação obrigatória (@login_required)
- ✅ Verificação de tipo de usuário (is_pcd() / is_empresa())
- ✅ Usuários só acessam suas próprias conversas
- ✅ CSRF protection em formulários
- ✅ Validação de conteúdo de mensagem

## Melhorias Futuras (Opcionais)

1. **WebSockets** - Mensagens em tempo real (já configurado Channels)
2. **Notificações Push** - Avisar sobre novas mensagens
3. **Anexos** - Permitir envio de arquivos
4. **Histórico** - Busca em mensagens antigas
5. **Typing Indicators** - Mostrar quando alguém está digitando
6. **Leitura em tempo real** - Marcar como lido instantaneamente

## Dependências

- Django >= 5.0
- Django REST Framework >= 3.14.0
- Pillow (para processamento de imagens)
- Channels (para WebSockets - opcional)

## Banco de Dados

**Tabelas:**
- `userpcd_conversa` - Conversas
- `userpcd_mensagem` - Mensagens

**Migrations:**
- `userpcd/migrations/0002_conversa_mensagem.py`

## Testes

Para testar o chat:

1. Crie uma empresa e um PCD
2. PCD se candidate a uma vaga da empresa
3. Empresa acesse candidatos e clique em "Iniciar Conversa"
4. Troque mensagens entre os usuários
5. Verifique marcação de leitura e contadores

## Conclusão

O sistema de chat está **100% funcional** com backend, frontend e API implementados. Permite comunicação bidirecional entre empresas e PCDs de forma segura e eficiente.
