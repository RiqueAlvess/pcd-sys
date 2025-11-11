# 🚀 Guia de Refatoração do Sistema PCD

## 📋 Resumo das Mudanças

Este documento descreve todas as mudanças implementadas na refatoração completa do sistema PCD, incluindo:

- ✅ **WebSocket para Chat em Tempo Real** entre candidatos aprovados e empresas
- ✅ **Sistema de Notificações Melhorado** com suporte a exclusão e marcação como lida
- ✅ **Processamento Assíncrono** com Celery para tarefas em background
- ✅ **APIs RESTful** para integração frontend/mobile
- ✅ **Notificações em Tempo Real** via WebSocket
- ✅ **Arquitetura Assíncrona** usando Django Channels

---

## 🔧 Tecnologias Adicionadas

### Novas Dependências

```txt
# WebSocket support
channels>=4.0.0
channels-redis>=4.1.0

# Redis for caching and WebSocket backend
redis>=5.0.0
aioredis>=2.0.0

# Environment variables
python-dotenv>=1.0.0

# Type hints support
django-stubs>=4.2.0
types-redis>=4.6.0

# API support
djangorestframework>=3.14.0

# Task queue for async processing
celery>=5.3.0
django-celery-beat>=2.5.0

# Production server
daphne>=4.0.0
```

### Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Instalar e configurar Redis
# Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis

# macOS:
brew install redis
brew services start redis

# Windows:
# Baixar Redis from https://redis.io/download
```

---

## 🏗️ Arquitetura do Sistema Refatorado

### 1. Configuração Django Channels

#### `pcd/settings.py`
- Adicionado `daphne` como servidor ASGI
- Configurado `CHANNEL_LAYERS` com Redis
- Adicionado `CACHES` com Redis
- Configurado Django REST Framework
- Configurado Celery para tarefas assíncronas
- Internacionalização atualizada para `pt-br`

#### `pcd/asgi.py`
- Configurado `ProtocolTypeRouter` para HTTP e WebSocket
- Adicionado `AuthMiddlewareStack` para autenticação WebSocket
- Configurado `URLRouter` para rotas WebSocket

#### `pcd/routing.py` (NOVO)
```python
websocket_urlpatterns = [
    # Chat WebSocket
    re_path(r'ws/chat/(?P<room_name>[\w-]+)/$', ChatConsumer.as_asgi()),

    # Notifications WebSocket
    re_path(r'ws/notifications/pcd/$', pcd_consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/notifications/company/$', company_consumers.NotificationConsumer.as_asgi()),
]
```

---

### 2. Sistema de Chat WebSocket

#### Consumers Criados

**`userpcd/consumers.py`** - Chat e Notificações para PCDs
- `ChatConsumer`: Gerencia chat em tempo real
  - Apenas permite chat para candidatos aprovados
  - Envia histórico de mensagens ao conectar
  - Marca mensagens como lidas automaticamente
  - Formato da sala: `pcd_{pcd_id}_empresa_{empresa_id}_vaga_{vaga_id}`

- `NotificationConsumer`: Notificações em tempo real para PCDs
  - Envia contador de notificações não lidas
  - Permite marcar como lida via WebSocket
  - Permite deletar notificações via WebSocket

**`usercompany/consumers.py`** - Notificações para Empresas
- `NotificationConsumer`: Notificações em tempo real para empresas
  - Envia contador de notificações não lidas
  - Permite marcar como lida via WebSocket
  - Permite deletar notificações via WebSocket

#### Como Usar o Chat

**Frontend JavaScript Exemplo:**
```javascript
// Conectar ao chat
const roomName = 'pcd_1_empresa_2_vaga_5';
const chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat/' + roomName + '/'
);

// Receber mensagens
chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log('Nova mensagem:', data);
    // Atualizar UI com a mensagem
};

// Enviar mensagem
function sendMessage(message) {
    chatSocket.send(JSON.stringify({
        'type': 'chat_message',
        'message': message
    }));
}

// Marcar como lidas
function markAsRead() {
    chatSocket.send(JSON.stringify({
        'type': 'mark_as_read'
    }));
}
```

---

### 3. Sistema de Notificações Melhorado

#### Funcionalidades Implementadas

**Para PCDs:**
- ✅ Listar notificações
- ✅ Marcar notificação individual como lida
- ✅ Marcar todas como lidas
- ✅ Deletar notificação
- ✅ Contador de não lidas em tempo real via WebSocket
- ✅ Receber notificações em tempo real via WebSocket

**Para Empresas:**
- ✅ Listar notificações
- ✅ Marcar notificação individual como lida
- ✅ Marcar todas como lidas
- ✅ Deletar notificação
- ✅ Contador de não lidas em tempo real via WebSocket
- ✅ Receber notificações em tempo real via WebSocket

#### APIs REST para Notificações

**PCDs:**
```bash
# Listar notificações
GET /api/pcd/notificacoes/
GET /api/pcd/notificacoes/?lida=false
GET /api/pcd/notificacoes/?tipo=candidatura
GET /api/pcd/notificacoes/?limit=10

# Marcar como lida
POST /api/pcd/notificacoes/{id}/mark_as_read/

# Marcar todas como lidas
POST /api/pcd/notificacoes/mark_all_as_read/

# Deletar notificação
DELETE /api/pcd/notificacoes/{id}/

# Contador de não lidas
GET /api/pcd/notificacoes/unread_count/
```

**Empresas:**
```bash
# Listar notificações
GET /api/empresa/notificacoes/
GET /api/empresa/notificacoes/?lida=false
GET /api/empresa/notificacoes/?tipo=novo_candidato
GET /api/empresa/notificacoes/?limit=10

# Marcar como lida
POST /api/empresa/notificacoes/{id}/mark_as_read/

# Marcar todas como lidas
POST /api/empresa/notificacoes/mark_all_as_read/

# Deletar notificação
DELETE /api/empresa/notificacoes/{id}/

# Contador de não lidas
GET /api/empresa/notificacoes/unread_count/
```

#### WebSocket para Notificações

**Frontend JavaScript Exemplo:**
```javascript
// Conectar ao WebSocket de notificações (PCD)
const notificationSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/notifications/pcd/'
);

notificationSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);

    if (data.type === 'notification') {
        // Nova notificação recebida
        console.log('Nova notificação:', data.notification);
        // Atualizar UI
    } else if (data.type === 'unread_count') {
        // Atualizar contador
        console.log('Não lidas:', data.count);
        // Atualizar badge
    }
};

// Marcar como lida via WebSocket
function markNotificationAsRead(notificationId) {
    notificationSocket.send(JSON.stringify({
        'type': 'mark_as_read',
        'notification_id': notificationId
    }));
}

// Deletar via WebSocket
function deleteNotification(notificationId) {
    notificationSocket.send(JSON.stringify({
        'type': 'delete',
        'notification_id': notificationId
    }));
}
```

---

### 4. Processamento Assíncrono com Celery

#### Configuração Celery

**`pcd/celery.py`** (NOVO)
- Configurado Celery com Redis como broker
- Configurado Celery Beat para tarefas periódicas
- Tarefas agendadas:
  - Limpeza de notificações antigas (PCDs): diariamente às 3h
  - Limpeza de notificações antigas (Empresas): diariamente às 3h

#### Tarefas Assíncronas Criadas

**`userpcd/tasks.py`** (NOVO)
- `limpar_notificacoes_antigas_task()`: Remove notificações lidas antigas (30+ dias)
- `enviar_notificacao_websocket_task()`: Envia notificação via WebSocket
- `atualizar_contador_notificacoes_task()`: Atualiza contador via WebSocket
- `processar_upload_documento_task()`: Processa upload de documento
- `calcular_compatibilidade_vagas_task()`: Calcula compatibilidade de vagas

**`usercompany/tasks.py`** (NOVO)
- `limpar_notificacoes_antigas_empresa_task()`: Remove notificações antigas (60+ dias)
- `enviar_notificacao_empresa_websocket_task()`: Envia notificação via WebSocket
- `atualizar_contador_notificacoes_empresa_task()`: Atualiza contador via WebSocket
- `atualizar_estatisticas_vaga_task()`: Atualiza estatísticas de vaga
- `enviar_relatorio_semanal_empresa_task()`: Envia relatório semanal

#### Executar Celery

**Desenvolvimento:**
```bash
# Terminal 1: Celery Worker
celery -A pcd worker -l info

# Terminal 2: Celery Beat (tarefas agendadas)
celery -A pcd beat -l info

# Terminal 3: Django Server
python manage.py runserver
# OU
daphne -b 0.0.0.0 -p 8000 pcd.asgi:application
```

**Produção:**
```bash
# Usar supervisord ou systemd para gerenciar processos
# Exemplo supervisord.conf:

[program:pcd_celery]
command=/path/to/venv/bin/celery -A pcd worker -l info
directory=/path/to/pcd-sys
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:pcd_celerybeat]
command=/path/to/venv/bin/celery -A pcd beat -l info
directory=/path/to/pcd-sys
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log

[program:pcd_daphne]
command=/path/to/venv/bin/daphne -b 0.0.0.0 -p 8000 pcd.asgi:application
directory=/path/to/pcd-sys
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/daphne/server.log
```

---

### 5. Signals Refatorados

#### `userpcd/signals.py`
- ✅ Adicionado envio de notificações via WebSocket usando Celery
- ✅ Adicionado processamento assíncrono de documentos
- ✅ Melhorada documentação com docstrings
- ✅ Adicionado type hints

#### `usercompany/signals.py`
- ✅ Adicionado envio de notificações via WebSocket usando Celery
- ✅ Adicionado atualização assíncrona de estatísticas
- ✅ Melhorada documentação com docstrings
- ✅ Adicionado type hints

---

### 6. APIs RESTful Completas

#### Endpoints para PCDs

**Notificações:**
```
GET    /api/pcd/notificacoes/
GET    /api/pcd/notificacoes/{id}/
POST   /api/pcd/notificacoes/{id}/mark_as_read/
POST   /api/pcd/notificacoes/mark_all_as_read/
DELETE /api/pcd/notificacoes/{id}/
GET    /api/pcd/notificacoes/unread_count/
```

**Conversas (Chat):**
```
GET    /api/pcd/conversas/
GET    /api/pcd/conversas/{id}/
POST   /api/pcd/conversas/{id}/send_message/
```

**Vagas:**
```
GET    /api/pcd/vagas/
GET    /api/pcd/vagas/{id}/
POST   /api/pcd/vagas/{id}/candidatar/
```

**Candidaturas:**
```
GET    /api/pcd/candidaturas/
GET    /api/pcd/candidaturas/{id}/
```

#### Endpoints para Empresas

**Notificações:**
```
GET    /api/empresa/notificacoes/
GET    /api/empresa/notificacoes/{id}/
POST   /api/empresa/notificacoes/{id}/mark_as_read/
POST   /api/empresa/notificacoes/mark_all_as_read/
DELETE /api/empresa/notificacoes/{id}/
GET    /api/empresa/notificacoes/unread_count/
```

**Candidaturas:**
```
GET    /api/empresa/candidaturas/
GET    /api/empresa/candidaturas/{id}/
POST   /api/empresa/candidaturas/{id}/update_status/
POST   /api/empresa/candidaturas/{id}/add_observation/
```

**Processos Seletivos:**
```
GET    /api/empresa/processos-seletivos/
GET    /api/empresa/processos-seletivos/{id}/
PUT    /api/empresa/processos-seletivos/{id}/
PATCH  /api/empresa/processos-seletivos/{id}/
```

**Vagas Extendidas:**
```
GET    /api/empresa/vagas-extendidas/
GET    /api/empresa/vagas-extendidas/{id}/
GET    /api/empresa/vagas-extendidas/{id}/statistics/
PUT    /api/empresa/vagas-extendidas/{id}/
PATCH  /api/empresa/vagas-extendidas/{id}/
```

---

## 🚀 Como Executar o Sistema Refatorado

### 1. Preparação

```bash
# Clone o repositório
git clone <repo-url>
cd pcd-sys

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Instale e inicie Redis
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Verifique se Redis está rodando
redis-cli ping  # Deve retornar PONG
```

### 2. Configuração

```bash
# Execute migrações
python manage.py makemigrations
python manage.py migrate

# Crie superusuário
python manage.py createsuperuser

# Colete arquivos estáticos
python manage.py collectstatic
```

### 3. Executar Serviços

**Desenvolvimento (3 terminais):**

```bash
# Terminal 1: Redis (se não estiver rodando como serviço)
redis-server

# Terminal 2: Celery Worker + Beat
celery -A pcd worker -B -l info

# Terminal 3: Django/Daphne Server
daphne -b 0.0.0.0 -p 8000 pcd.asgi:application
# ou
python manage.py runserver
```

### 4. Testar

```bash
# Acessar aplicação
http://localhost:8000

# Acessar admin
http://localhost:8000/admin

# Testar APIs
http://localhost:8000/api/pcd/notificacoes/
http://localhost:8000/api/empresa/notificacoes/
```

---

## 📊 Fluxos do Sistema

### Fluxo de Chat

```
1. Candidato é aprovado (status='aprovado')
   ↓
2. Sistema cria/atualiza Conversa
   ↓
3. PCD e Empresa podem acessar chat
   ↓
4. Conectam via WebSocket: ws://host/ws/chat/{room_name}/
   ↓
5. Trocam mensagens em tempo real
   ↓
6. Mensagens são salvas no banco
   ↓
7. Mensagens são marcadas como lidas automaticamente
```

### Fluxo de Notificações

```
1. Evento ocorre (candidatura, documento, etc)
   ↓
2. Signal cria Notificacao no banco
   ↓
3. Signal chama task Celery para enviar via WebSocket
   ↓
4. Task envia notificação via WebSocket (se usuário conectado)
   ↓
5. Task atualiza contador de não lidas via WebSocket
   ↓
6. Frontend recebe e exibe notificação em tempo real
```

### Fluxo de Processamento Assíncrono

```
1. Evento dispara signal
   ↓
2. Signal salva no banco (síncrono)
   ↓
3. Signal envia task para Celery (assíncrono)
   ↓
4. Celery processa task em background
   ↓
5. Task envia atualizações via WebSocket
```

---

## 🔐 Segurança

### WebSocket Authentication

- Todos os WebSocket consumers usam `AuthMiddlewareStack`
- Usuários não autenticados são desconectados automaticamente
- Chat verifica se usuário tem permissão para acessar a sala
- Chat só permite acesso para candidatos aprovados

### API Authentication

- Todas as APIs usam `IsAuthenticated` permission
- Session authentication via Django
- Usuários só podem acessar seus próprios dados

---

## 🧪 Testes

```bash
# Rodar todos os testes
python manage.py test

# Testar app específico
python manage.py test userpcd
python manage.py test usercompany

# Testar com coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 📝 Migração de Sistema Legado

### Dados Existentes

Todos os dados existentes são mantidos. As mudanças são aditivas:
- ✅ Modelos existentes não foram alterados
- ✅ Novas funcionalidades adicionadas via signals
- ✅ APIs criadas para acessar dados existentes

### Compatibilidade

- ✅ Sistema legado continua funcionando
- ✅ WebSocket é opcional (graceful degradation)
- ✅ APIs podem ser usadas gradualmente

---

## 🐛 Troubleshooting

### Redis não conecta

```bash
# Verificar se Redis está rodando
redis-cli ping

# Reiniciar Redis
sudo systemctl restart redis

# Verificar porta
netstat -an | grep 6379
```

### Celery não processa tasks

```bash
# Verificar se worker está rodando
celery -A pcd inspect active

# Limpar tasks antigas
celery -A pcd purge

# Verificar logs
tail -f celery.log
```

### WebSocket não conecta

```bash
# Verificar se Daphne está rodando
ps aux | grep daphne

# Testar conexão WebSocket
wscat -c ws://localhost:8000/ws/notifications/pcd/

# Verificar logs do Daphne
tail -f daphne.log
```

---

## 📚 Recursos Adicionais

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Redis Documentation](https://redis.io/documentation)

---

## 🎯 Próximos Passos

- [ ] Adicionar testes automatizados
- [ ] Implementar rate limiting nas APIs
- [ ] Adicionar Docker Compose para desenvolvimento
- [ ] Implementar CI/CD pipeline
- [ ] Adicionar monitoramento com Sentry
- [ ] Implementar logs estruturados
- [ ] Adicionar documentação Swagger/OpenAPI

---

## 👥 Contribuindo

Para contribuir com o projeto:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).

---

**Desenvolvido com ❤️ para inclusão de PCDs no mercado de trabalho**
