# Estrutura Completa do Projeto Django PCD

## Visão Geral
Este é um sistema Django para gerenciamento de vagas e candidaturas para Pessoas Com Deficiência (PCD). O projeto está organizado em 3 apps principais com um sistema de roles baseado em usuários.

---

## 1. ESTRUTURA DE APPS

### App: `core`
**Responsabilidade:** Autenticação, usuários e perfis base

**Arquivos principais:**
- `/home/user/pcd-sys/core/models.py` - Modelos de usuário e perfis
- `/home/user/pcd-sys/core/views.py` - Login, cadastro e dashboard
- `/home/user/pcd-sys/core/urls.py` - Rotas de autenticação
- `/home/user/pcd-sys/core/admin.py` - Interface admin customizada

**Migrations:**
- `0001_initial.py` - Criação de User, Empresa, PCDProfile, MedicoProfile
- `0002_carga_categorias_deficiencia.py` - Carregamento de categorias

---

### App: `userpcd`
**Responsabilidade:** Funcionalidades para usuários PCD (Pessoas Com Deficiência)

**Arquivos principais:**
- `/home/user/pcd-sys/userpcd/models.py` - Modelos de vagas, candidaturas, documentos
- `/home/user/pcd-sys/userpcd/views.py` - Dashboard PCD, vagas, candidaturas
- `/home/user/pcd-sys/userpcd/urls.py` - Rotas do app PCD
- `/home/user/pcd-sys/userpcd/admin.py` - Interface admin
- `/home/user/pcd-sys/userpcd/matching.py` - Motor de matching automático
- `/home/user/pcd-sys/userpcd/signals.py` - Sinais para automação

**Migrations:**
- `0001_initial.py` - Criação dos modelos iniciais
- `0002_conversa_mensagem.py` - Sistema de mensagens

---

### App: `usercompany`
**Responsabilidade:** Funcionalidades para usuários Empresa

**Arquivos principais:**
- `/home/user/pcd-sys/usercompany/models.py` - Extensões e modelos de empresa
- `/home/user/pcd-sys/usercompany/views.py` - Dashboard empresa, gestão de vagas
- `/home/user/pcd-sys/usercompany/urls.py` - Rotas do app empresa
- `/home/user/pcd-sys/usercompany/admin.py` - Interface admin

**Migrations:**
- `0001_initial.py` - Criação dos modelos iniciais

---

## 2. MODELOS EXISTENTES

### Core Models

#### **User (Customizado - AbstractUser)**
```
- username (string) - Único
- email (string)
- password (hashed)
- role (choice) - 'root', 'empresa', 'pcd', 'medico'
- is_active (boolean)
- is_staff (boolean)
- date_joined (datetime)
- last_login (datetime)

Métodos:
- is_root()
- is_empresa()
- is_pcd()
- is_medico()
```

#### **Empresa**
```
- user (OneToOne → User)
- razao_social (string, 255)
- cnpj (string, 18) - Único
- telefone_principal (string, 20)
- telefone_secundario (string, 20, opcional)
- cnae_principal (string, 10)
- tamanho (string, 10)
- site (URL, opcional)
- criado_em (datetime)
```

#### **PCDProfile**
```
- user (OneToOne → User)
- cpf (string, 14) - Único
- telefone (string, 20)
- data_nascimento (date)
- nome_completo (string, 255, opcional)
- nome_mae (string, 255, opcional)
- endereco (text, opcional)
- formacao_academica (text, opcional)
- experiencia_profissional (text, opcional)
- deficiencias (ManyToMany → CategoriaDeficiencia)
- curriculo (file, opcional)
- laudos (file, opcional)
- criado_em (datetime)
```

#### **MedicoProfile**
```
- user (OneToOne → User)
- nome_completo (string, 255)
- crm (string, 20)
- especialidade (string, 100)
- criado_em (datetime)
- atualizado_em (datetime)
```

#### **CategoriaDeficiencia**
```
- nome (string, 100)
Exemplos: 'Físico/Motora', 'Auditiva', 'Visual', 'Intelectual/Psicológica', 'Múltipla'
```

### UserPCD Models

#### **Vaga**
```
- empresa (FK → Empresa)
- titulo (string, 200)
- descricao (text)
- modalidade (choice) - 'presencial', 'remoto', 'hibrido'
- cidade (string, 100)
- uf (string, 2)
- salario_min (decimal, opcional)
- salario_max (decimal, opcional)
- requisitos (text)
- beneficios (text, opcional)
- acessivel (boolean) - padrão: True
- status (choice) - 'ativa', 'pausada', 'encerrada'
- criada_em (datetime)
- atualizada_em (datetime)

Relacionamentos:
- candidatos (Reverse: Candidatura)
```

#### **Candidatura**
```
- pcd (FK → PCDProfile)
- vaga (FK → Vaga)
- status (choice) - 'pendente', 'em_analise', 'entrevista', 'aprovado', 'rejeitado'
- data_candidatura (datetime)
- atualizada_em (datetime)
- observacoes (text, opcional)
- Constraint: unique_together = ['pcd', 'vaga']
```

#### **Documento**
```
- pcd (FK → PCDProfile)
- tipo (choice) - 'curriculo', 'laudo'
- arquivo (file)
- nome_original (string, 255)
- cid_10 (string, 10, opcional) - Para laudos médicos
- status (choice) - 'pendente', 'aprovado', 'rejeitado'
- data_upload (datetime)
- observacoes (text, opcional)
```

#### **Notificacao**
```
- user (FK → User)
- tipo (choice) - 'candidatura', 'documento', 'sistema'
- titulo (string, 200)
- mensagem (text)
- lida (boolean)
- criada_em (datetime)
```

#### **PerfilPCDExtendido**
```
- pcd_profile (OneToOne → PCDProfile)
- cep (string, 9, opcional)
- rua (string, 255, opcional)
- numero (string, 20, opcional)
- complemento (string, 100, opcional)
- bairro (string, 100, opcional)
- cidade (string, 100, opcional)
- uf (string, 2, opcional)
- status_medico (choice) - 'pendente', 'enquadravel', 'sugestivo', 'nao_enquadravel'
- percentual_completude (integer) - 0 a 100

Métodos:
- calcular_completude() - Calcula baseado em campos preenchidos
```

#### **Conversa**
```
- pcd (FK → PCDProfile)
- empresa (FK → Empresa)
- vaga (FK → Vaga, opcional)
- candidatura (FK → Candidatura, opcional)
- criada_em (datetime)
- atualizada_em (datetime)
- Constraint: unique_together = ['pcd', 'empresa', 'vaga']

Métodos:
- mensagens_nao_lidas_pcd()
- mensagens_nao_lidas_empresa()
- ultima_mensagem()
```

#### **Mensagem**
```
- conversa (FK → Conversa)
- remetente_empresa (boolean) - True: empresa, False: PCD
- conteudo (text)
- lida (boolean)
- enviada_em (datetime)

Métodos:
- marcar_como_lida()
```

### UserCompany Models

#### **EmpresaExtendida**
```
- empresa (OneToOne → Empresa)
- percentual_completude (integer) - 0 a 100
- total_vagas_ativas (integer)
- total_candidatos_recebidos (integer)

Métodos:
- calcular_completude() - Baseado em campos da empresa preenchidos
```

#### **VagaExtendida**
```
- vaga (OneToOne → Vaga)
- tipo (choice) - 'emprego', 'capacitacao'
- numero_vagas (integer) - Padrão: 1
- duracao_capacitacao (string, 100, opcional)
- acesso_transporte_publico (boolean)
- deficiencias_elegiveis (ManyToMany → CategoriaDeficiencia)
- status_medico (choice) - 'pendente', 'aprovada', 'rejeitada'
- observacoes_medicas (text, opcional)
- total_candidatos (integer)
- candidatos_compativel (integer)

Métodos:
- atualizar_contadores()
```

#### **ProcessoSeletivo**
```
- candidatura (OneToOne → Candidatura)
- status (choice) - 'novo', 'visualizado', 'contato_iniciado', 'entrevista_marcada', 'aprovado', 'rejeitado'
- data_visualizacao_cv (datetime, opcional)
- data_contato (datetime, opcional)
- data_entrevista (datetime, opcional)
- observacoes_empresa (text, opcional)
- atualizado_em (datetime)
```

#### **NotificacaoEmpresa**
```
- empresa (FK → Empresa)
- tipo (choice) - 'novo_candidato', 'status_vaga', 'avaliacao_medica', 'sistema'
- titulo (string, 200)
- mensagem (text)
- vaga (FK → Vaga, opcional)
- candidatura (FK → Candidatura, opcional)
- lida (boolean)
- criada_em (datetime)
```

---

## 3. SISTEMA DE AUTENTICAÇÃO E ROLES

### Arquitetura de Roles
O sistema usa um modelo baseado em **role** do usuário:

| Role | Descrição | Perfil Relacionado | Acesso |
|------|-----------|------------------|--------|
| **root** | Administrador | Nenhum | Admin completo |
| **pcd** | Pessoa Com Deficiência | PCDProfile | Dashboard PCD, vagas, candidaturas |
| **empresa** | Empresa Empregadora | Empresa | Dashboard Empresa, criar vagas, ver candidatos |
| **medico** | Médico Avaliador | MedicoProfile | Avaliação de PCDs e vagas |

### Views de Autenticação
**Arquivo:** `/home/user/pcd-sys/core/views.py`

#### `login_view()`
- Autentica usuário por username/senha
- Redireciona inteligentemente baseado em role
- Cria perfil de empresa automaticamente se não existir
- Trata erros de forma robusta

#### `smart_redirect_after_login(user, request)`
- Função helper para redirecionamento seguro
- Não quebra se URLs não existirem
- Fallbacks para cada role

#### `dashboard(request)`
- Redireciona para dashboard específico do role
- Pontos de entrada: `dashboard_pcd`, `dashboard_empresa`, `admin:index`

#### `cadastro_pcd(request)` / `cadastro_empresa(request)`
- Validação de campos obrigatórios
- Verificação de duplicidade (username, CPF, CNPJ)
- Criação automática de perfis relacionados
- Login automático após cadastro

### Decoradores de Acesso
```python
@login_required - Requer autenticação
Verificações adicionais nas views:
- if not request.user.is_pcd() - Para PCDs
- if not request.user.is_empresa() - Para Empresas
```

### URLs de Autenticação
```
/core/login/ - Login
/core/logout/ - Logout
/core/dashboard/ - Dashboard (redireciona para role específico)
/core/escolha/ - Tela de escolha de tipo de usuário
/core/cadastro/pcd/ - Cadastro PCD
/core/cadastro/empresa/ - Cadastro Empresa
```

---

## 4. FUNCIONALIDADES IMPLEMENTADAS

### Para PCD (Usuários PCD)

**Dashboard (`/userpcd/dashboard/`)**
- Visualiza perfil de completude (%)
- Lista vagas compatíveis
- Mostra candidaturas recentes
- Notificações não lidas
- Status de documentos

**Perfil (`/userpcd/perfil/editar/`)**
- Edita dados pessoais
- Atualiza endereço completo
- Gerencia deficiências selecionadas
- Calcula completude do perfil em tempo real

**Vagas (`/userpcd/vagas/`)**
- Lista vagas ativas com paginação
- Filtros: modalidade, cidade, UF
- Exclui vagas já candidatadas
- Botão de candidatar (via AJAX)

**Candidaturas (`/userpcd/candidaturas/`)**
- Lista todas as candidaturas do PCD
- Status da candidatura
- Paginação

**Documentos (`/userpcd/documento/upload/`)**
- Upload de currículo (PDF, JPG, PNG)
- Upload de laudo médico com CID-10
- Validação de tipo e tamanho (5MB max)
- Status: pendente/aprovado/rejeitado

**Notificações (`/userpcd/notificacoes/`)**
- Lista notificações do sistema
- Marca como lida automaticamente ao visualizar
- API para dropdown (`/api/notificacoes/`)

### Para Empresa

**Dashboard (`/usercompany/dashboard/`)**
- Estatísticas: vagas ativas, vagas totais
- Total de candidatos e candidatos novos
- Vagas recentes
- Candidaturas recentes
- Notificações não lidas

**Perfil (`/usercompany/perfil/editar/`)**
- Edita dados da empresa
- Atualiza completude (%)
- Campos: razão social, telefones, CNPJ, CNAE, tamanho, site

**Vagas (`/usercompany/vagas/`)**
- Lista vagas com filtros (status, tipo, status médico)
- Paginação
- Acesso a detalhes de cada vaga

**Criar Vaga (`/usercompany/vagas/nova/`)**
- Formulário completo com:
  - Dados básicos (título, descrição, modalidade)
  - Localização (cidade, UF)
  - Salário (min/max)
  - Requisitos e benefícios
  - Tipo (emprego/capacitação)
  - Deficiências elegíveis
  - Acessibilidade
- Vaga vai para avaliação médica automaticamente

**Editar Vaga (`/usercompany/vagas/<id>/editar/`)**
- Edita todos os campos
- Se rejeitada, permite reenviar para avaliação

**Encerrar Vaga (`/usercompany/vagas/<id>/encerrar/`)**
- Muda status para "encerrada"
- Cria notificação para empresa

**Detalhes da Vaga (`/usercompany/vagas/<id>/`)**
- Mostra informações completas
- Lista primeiros 10 candidatos
- Estatísticas de candidatos

**Candidatos (`/usercompany/vagas/<id>/candidatos/`)**
- Lista todos os candidatos de uma vaga
- Filtro por status
- Paginação (20 por página)
- Cria ProcessoSeletivo automaticamente

**Status do Candidato (`/usercompany/candidatos/<id>/status/`)**
- Atualiza status: 'pendente', 'em_analise', 'entrevista', 'aprovado', 'rejeitado'
- Registra observações
- Atualiza ProcessoSeletivo com datas

**Visualizar Currículo (`/usercompany/candidatos/<id>/curriculo/`)**
- Mostra perfil do candidato
- Exibe currículo
- Exibe laudos médicos
- Marca CV como visualizado
- Rastreia data de visualização

**Notificações (`/usercompany/notificacoes/`)**
- Lista notificações da empresa
- Ações: marcar como lida, excluir
- API para dropdown

### Sistema de Notificações

**Para PCD:**
- Candidatura enviada
- Documento processado
- Notificações do sistema

**Para Empresa:**
- Novo candidato recebido
- Status da vaga
- Avaliação médica
- Notificações do sistema

---

## 5. FUNCIONALIDADES AVANÇADAS

### Motor de Matching (`/home/user/pcd-sys/userpcd/matching.py`)
```
MatchingEngine - Calcula compatibilidade entre PCDs e Vagas

Pesos:
- Deficiência: 40 pontos
- Localização: 20 pontos
- Modalidade: 15 pontos
- Perfil completude: 15 pontos
- Status médico: 10 pontos

Score final: 0-100
```

### Signals Automáticos (`/home/user/pcd-sys/userpcd/signals.py`)
1. **Criar PerfilPCDExtendido** - Automático ao criar PCDProfile
2. **Atualizar Completude** - Automático ao salvar PCDProfile
3. **Notificar Candidatura** - Automático ao candidatar
4. **Limpar Notificações Antigas** - Função auxiliar (30+ dias)

### Upload de Documentos
- Validação de tipo: PDF, JPG, PNG
- Limite de tamanho: 5MB
- Armazenamento: `/media/documentos/`
- Limpeza automática ao deletar

### Cálculo de Completude

**PCD:**
- 80% para campos obrigatórios (nome, telefone, CPF, data nasc, endereço, etc)
- +10% para deficiências selecionadas
- +10% para currículo enviado
- Total máximo: 100%

**Empresa:**
- 80% para campos obrigatórios (razão social, telefone, CNPJ, CNAE, tamanho)
- +10% para telefone secundário
- +10% para site
- Total máximo: 100%

---

## 6. INTERFACE ADMIN

### Customização com Unfold
- Admin modernizado com tema verde
- Sidebar configurável com navegação
- Icons e cores customizadas
- Formulários responsivos

### Modelos Registrados

**Core:**
- User (com inlines dinâmicos para Empresa/PCD/Médico)
- CategoriaDeficiencia

**UserPCD:**
- Vaga (com fieldsets colapsáveis)
- Candidatura (com display formatado)
- Documento
- Notificacao (com ações de marcar lida)
- PerfilPCDExtendido (com recálculo de completude)
- Conversa
- Mensagem

**UserCompany:**
- EmpresaExtendida (com recálculo de completude)
- VagaExtendida (com aprovação/rejeição)
- ProcessoSeletivo
- NotificacaoEmpresa

### Ações Admin Customizadas
- Marcar notificações como lidas/não lidas
- Recalcular completude de perfis
- Aprovar/rejeitar vagas
- Atualizar contadores de candidatos

---

## 7. ARQUIVOS PRINCIPAIS

### Estrutura de Diretórios
```
/home/user/pcd-sys/
├── pcd/                          # Projeto Django
│   ├── settings.py              # Configurações (Django 5.2.1)
│   ├── urls.py                  # URLs principais
│   └── wsgi.py
│
├── core/                         # App de autenticação
│   ├── models.py                # User, Empresa, PCDProfile, Médico
│   ├── views.py                 # Login, cadastro, dashboard
│   ├── urls.py
│   ├── admin.py                 # Admin customizado
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_carga_categorias_deficiencia.py
│
├── userpcd/                      # App para PCDs
│   ├── models.py                # Vaga, Candidatura, Documento, etc
│   ├── views.py                 # Dashboard PCD, vagas, candidaturas
│   ├── urls.py
│   ├── admin.py
│   ├── matching.py              # Motor de matching
│   ├── signals.py               # Automações
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_conversa_mensagem.py
│
├── usercompany/                  # App para Empresas
│   ├── models.py                # EmpresaExtendida, VagaExtendida, etc
│   ├── views.py                 # Dashboard empresa, gestão de vagas
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
│       └── 0001_initial.py
│
├── templates/                    # Templates HTML
│   ├── core/
│   ├── usercore/
│   └── usercompany/
│
├── manage.py
├── requirements.txt
└── db.sqlite3
```

---

## 8. CONFIGURAÇÃO DJANGO

**Versão:** Django 5.2.1
**Banco:** SQLite (desenvolvimento)
**Autenticação:** User model customizado
**Media:** Arquivos em `/media/`

**INSTALLED_APPS:**
- unfold (admin customizado)
- django.contrib.admin
- django.contrib.auth
- django.contrib.contenttypes
- django.contrib.sessions
- django.contrib.messages
- django.contrib.staticfiles
- core
- userpcd
- usercompany

**AUTH_USER_MODEL:** 'core.User'

---

## 9. FLUXOS PRINCIPAIS

### Cadastro de PCD
1. Acessa `/core/cadastro/pcd/`
2. Preenche: username, email, senha, telefone, CPF, data nasc, deficiências
3. Sistema cria User + PCDProfile + PerfilPCDExtendido
4. Login automático
5. Redireciona para `/userpcd/dashboard/`

### Cadastro de Empresa
1. Acessa `/core/cadastro/empresa/`
2. Preenche: username, email, senha, dados da empresa (CNPJ, razão social, etc)
3. Sistema cria User + Empresa + EmpresaExtendida
4. Login automático
5. Redireciona para `/usercompany/dashboard/`

### Fluxo de Candidatura
1. PCD acessa `/userpcd/vagas/`
2. Escolhe vaga
3. Clica em "Candidatar"
4. Sistema cria Candidatura (status: pendente)
5. Cria Notificacao para PCD
6. Empresa recebe NotificacaoEmpresa
7. Cria ProcessoSeletivo automaticamente

### Fluxo de Avaliação (Empresa)
1. Empresa acessa `/usercompany/vagas/<id>/candidatos/`
2. Visualiza currículo do candidato
3. Atualiza status (em_analise → entrevista → aprovado/rejeitado)
4. Sistema registra datas e observações
5. ProcessoSeletivo é atualizado

---

## 10. SEGURANÇA

### Proteções Implementadas
- @login_required em todas as views com autenticação
- Verificação de role específica em views sensíveis
- @csrf_protect em POSTs
- Validação de propriedade (empresa só vê suas vagas)
- Upload de arquivo com validação de tipo e tamanho
- Limpeza automática de arquivos ao deletar documento

### Configurações de Segurança
- DEBUG = True (desenvolvimento)
- SECRET_KEY configurado
- ALLOWED_HOSTS = [] (precisa ser preenchido para produção)

---

## 11. PRÓXIMOS PASSOS / FUNCIONALIDADES PLANEJADAS

Baseado na estrutura atual:
1. Dashboard médico para avaliação
2. Sistema de matching automático (já tem engine pronta)
3. Chat em tempo real entre PCD e Empresa
4. Integração de APIs externas (CEP, CNPJ)
5. Relatórios e análises
6. Sistema de recomendações
7. Envio de emails de notificação

---

## 12. ENDPOINTS PRINCIPAIS

### Core (Autenticação)
- `POST /core/login/` - Login
- `GET /core/logout/` - Logout
- `GET /core/dashboard/` - Dashboard (redireciona)
- `GET /core/escolha/` - Escolha de tipo
- `POST /core/cadastro/pcd/` - Cadastro PCD
- `POST /core/cadastro/empresa/` - Cadastro Empresa

### UserPCD (PCD)
- `GET /userpcd/dashboard/` - Dashboard
- `GET/POST /userpcd/perfil/editar/` - Editar perfil
- `POST /userpcd/deficiencias/atualizar/` - Atualizar deficiências
- `POST /userpcd/documento/upload/` - Upload documento
- `GET /userpcd/vagas/` - Listar vagas
- `POST /userpcd/candidatar/<id>/` - Candidatar
- `GET /userpcd/candidaturas/` - Minhas candidaturas
- `GET /userpcd/notificacoes/` - Notificações
- `GET /userpcd/api/notificacoes/` - API notificações

### UserCompany (Empresa)
- `GET /usercompany/dashboard/` - Dashboard
- `GET/POST /usercompany/perfil/editar/` - Editar perfil
- `GET /usercompany/vagas/` - Minhas vagas
- `GET/POST /usercompany/vagas/nova/` - Criar vaga
- `GET /usercompany/vagas/<id>/` - Detalhes vaga
- `GET/POST /usercompany/vagas/<id>/editar/` - Editar vaga
- `POST /usercompany/vagas/<id>/encerrar/` - Encerrar vaga
- `GET /usercompany/vagas/<id>/candidatos/` - Candidatos
- `POST /usercompany/candidatos/<id>/status/` - Atualizar status
- `GET /usercompany/candidatos/<id>/curriculo/` - Ver currículo
- `GET /usercompany/notificacoes/` - Notificações
- `GET /usercompany/api/notificacoes/` - API notificações

---

**Última atualização:** 2025-11-10
**Versão do Django:** 5.2.1
**Banco de dados:** SQLite3
