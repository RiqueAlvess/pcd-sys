# Sistema de Classificação PCD e Workflow Médico

## Visão Geral

Este documento descreve o sistema completo de classificação de PCDs, avaliação médica de vagas e matching automático implementado no Portal PCD.

---

## 1. Classificação de PCDs (Obrigatória pelo Médico)

### 1.1 Estados de Classificação

O médico categoriza cada usuário PCD em um dos 5 estados:

| Estado | Emoji | Descrição |
|--------|-------|-----------|
| **Enquadrável** | ✅ | PCD totalmente apto para vagas PCD |
| **Sugestivo de Enquadrável** | ⚠️ | Pode necessitar avaliação adicional em alguns casos |
| **Não Enquadrável** | 🚫 | Não se enquadra nos critérios PCD |
| **Avaliação Médica Adicional** | 🩺 | Necessita consulta presencial ou telemedicina |
| **Necessita Laudo Atualizado** | 📄 | Documentação incompleta ou desatualizada |

### 1.2 Workflow de Avaliação de PCD

1. **PCD se cadastra** no sistema e envia documentos (currículo, laudos médicos)
2. **Médico acessa** o dashboard e vê lista de PCDs pendentes
3. **Médico analisa**:
   - Dados pessoais completos
   - Deficiências declaradas
   - Documentos enviados (laudos, CID-10)
   - Formação e experiência
4. **Médico classifica** escolhendo um dos 5 estados
5. **Médico adiciona observações** justificando a avaliação
6. **Sistema envia notificação** automática ao PCD informando o resultado

### 1.3 Notificações Automáticas

Após classificação, o PCD recebe notificação personalizada:

- **Enquadrável**: "Parabéns! Você foi classificado como Enquadrável. Agora você pode se candidatar às vagas disponíveis."
- **Sugestivo**: "Você foi classificado como Sugestivo de Enquadrável. Isso significa que você pode se candidatar às vagas..."
- **Não Enquadrável**: "Infelizmente, você não foi classificado como enquadrável no momento..."
- **Avaliação Adicional**: "É necessária uma avaliação médica adicional (presencial ou por telemedicina)..."
- **Necessita Laudo**: "É necessário um laudo médico detalhado ou exame atualizado..."

---

## 2. Workflow Médico para Avaliação de Vagas

### 2.1 Objetivo

Cada nova vaga cadastrada pelas empresas é submetida a avaliação médica prévia para definir **quais deficiências são elegíveis** para aquela vaga/capacitação.

### 2.2 Processo de Avaliação

1. **Empresa cadastra vaga** com descrição, requisitos e localização
2. **Vaga fica com status "Pendente"** de avaliação médica
3. **Médico acessa lista** de vagas pendentes
4. **Médico analisa**:
   - Descrição detalhada da vaga
   - Requisitos e responsabilidades
   - Modalidade (presencial/remoto/híbrido)
   - Acessibilidade do local
   - Tipo (emprego ou capacitação)
5. **Médico define**:
   - Status: Aprovada, Rejeitada ou Pendente
   - **Deficiências elegíveis** (múltipla seleção):
     - Físico/Motora
     - Auditiva
     - Visual
     - Intelectual/Psicológica
     - Múltipla
   - Observações médicas justificando
6. **Sistema notifica empresa** sobre o resultado
7. **Vaga aprovada** passa a aparecer para matching

### 2.3 Estados de Avaliação de Vaga

| Estado | Descrição |
|--------|-----------|
| **Pendente** | Aguardando avaliação médica |
| **Aprovada** | Vaga aprovada e disponível para matching |
| **Rejeitada** | Vaga não compatível com PCDs |

---

## 3. Matching Automático

### 3.1 Como Funciona

O sistema realiza **cruzamento automático diário** entre:
- PCDs com status "Enquadrável" ou "Sugestivo"
- Vagas com status "Aprovada" pelo médico

### 3.2 Critérios de Matching

O sistema calcula um **score de compatibilidade (0-100)** baseado em:

| Critério | Peso | Descrição |
|----------|------|-----------|
| **Deficiência** | 40% | Compatibilidade entre deficiências do PCD e deficiências elegíveis da vaga |
| **Localização** | 20% | Proximidade geográfica (mesma cidade/estado) |
| **Modalidade** | 15% | Trabalho remoto/híbrido/presencial |
| **Perfil** | 15% | Completude do perfil do PCD (quanto mais completo, maior o score) |
| **Status Médico** | 10% | Status da avaliação médica do PCD |

### 3.3 Classificação de Match

| Score | Nível |
|-------|-------|
| 80-100 | Excelente |
| 60-79 | Muito Bom |
| 40-59 | Bom |
| 20-39 | Regular |
| 0-19 | Baixo |

### 3.4 Notificações de Match

- PCDs recebem notificação apenas se o **score >= 50**
- Não são enviadas notificações duplicadas (mesma vaga) em menos de **7 dias**
- Notificação inclui:
  - Score e nível de compatibilidade
  - Nome da empresa e vaga
  - Localização e modalidade
  - Link para se candidatar

---

## 4. Acessos e Roles de Usuários

### 4.1 Perfis do Sistema

| Perfil | Tipo de Cadastro | Permissões |
|--------|------------------|------------|
| **Root** | Pré-definido | Administração total (Django Admin) |
| **Médico** | Adicionado por Root | Avaliar PCDs e vagas |
| **Empresa** | Cadastro público | Publicar vagas, ver candidatos compatíveis |
| **PCD** | Cadastro público | Completar perfil, submeter documentos, candidatar-se |

### 4.2 Médico

**Acesso ao sistema:**
- URL: `/medico/dashboard/`
- Login com credenciais de médico (role='medico')

**Funcionalidades:**
- Dashboard com estatísticas
- Listar e filtrar PCDs pendentes
- Avaliar PCDs individualmente
- Listar e filtrar vagas pendentes
- Avaliar vagas e definir deficiências elegíveis

---

## 5. Comandos de Management

### 5.1 Executar Matching Diário

```bash
python manage.py executar_matching
```

**Opções:**
- `--verbose`: Mostra informações detalhadas

**Output:**
```
🚀 Iniciando matching automático...

✅ Matching executado com sucesso!

📊 Estatísticas:
  - Vagas processadas: 15
  - PCDs elegíveis: 42
  - Matches encontrados: 87
  - Notificações enviadas: 23
  - Executado em: 10/11/2025 08:00:00
```

### 5.2 Configuração de Cron (Execução Automática Diária)

Adicione ao crontab para executar todos os dias às 8h:

```bash
crontab -e
```

Adicione a linha:
```
0 8 * * * cd /path/to/pcd-sys && source venv/bin/activate && python manage.py executar_matching
```

---

## 6. Estrutura de Arquivos

### 6.1 Models

**`core/models.py`:**
- `User` - Usuário customizado com roles
- `PCDProfile` - Perfil base do PCD
- `MedicoProfile` - Perfil do médico
- `CategoriaDeficiencia` - Categorias de deficiências

**`userpcd/models.py`:**
- `PerfilPCDExtendido` - Campos adicionais do PCD incluindo status médico
- `Vaga` - Vagas de emprego/capacitação
- `Documento` - Currículos e laudos
- `Notificacao` - Notificações para PCDs

**`usercompany/models.py`:**
- `VagaExtendida` - Campos médicos da vaga (deficiências elegíveis, status)
- `NotificacaoEmpresa` - Notificações para empresas

### 6.2 Views

**`core/views.py`:**
- `dashboard_medico` - Dashboard do médico
- `listar_pcds_pendentes` - Lista de PCDs para avaliar
- `avaliar_pcd` - Formulário de avaliação de PCD
- `listar_vagas_pendentes` - Lista de vagas para avaliar
- `avaliar_vaga` - Formulário de avaliação de vaga

### 6.3 Templates

**`core/templates/core/medico/`:**
- `dashboard.html` - Dashboard médico
- `listar_pcds.html` - Lista de PCDs
- `avaliar_pcd.html` - Form de avaliação de PCD
- `listar_vagas.html` - Lista de vagas
- `avaliar_vaga.html` - Form de avaliação de vaga

### 6.4 Matching Engine

**`userpcd/matching.py`:**
- `MatchingEngine` - Motor de matching com algoritmo de compatibilidade
- `executar_matching_diario()` - Função de matching em lote

### 6.5 Management Commands

**`userpcd/management/commands/executar_matching.py`:**
- Comando Django para executar matching via CLI

---

## 7. Fluxo Completo do Sistema

### 7.1 Fluxo PCD

```
1. PCD se cadastra →
2. Completa perfil e envia documentos →
3. Médico avalia e classifica →
4. PCD recebe notificação do status →
5. Se enquadrável/sugestivo:
   - Sistema faz matching diário
   - PCD recebe notificações de vagas compatíveis
   - PCD se candidata às vagas
```

### 7.2 Fluxo Empresa

```
1. Empresa se cadastra →
2. Publica vaga →
3. Médico avalia vaga e define deficiências elegíveis →
4. Empresa recebe notificação (aprovada/rejeitada) →
5. Se aprovada:
   - Vaga entra no matching automático
   - Empresa vê apenas candidatos compatíveis
```

### 7.3 Fluxo Médico

```
1. Root cria conta de médico →
2. Médico faz login →
3. Dashboard mostra PCDs e vagas pendentes →
4. Médico avalia PCDs:
   - Analisa documentos
   - Classifica em um dos 5 estados
   - Adiciona observações
5. Médico avalia vagas:
   - Analisa descrição e requisitos
   - Define deficiências elegíveis
   - Aprova ou rejeita
```

---

## 8. APIs e Funções Úteis

### 8.1 Funções de Matching

```python
from userpcd.matching import (
    MatchingEngine,
    get_vagas_recomendadas,
    get_candidatos_recomendados,
    calcular_compatibilidade,
    executar_matching_diario
)

# Buscar vagas compatíveis com um PCD
vagas = get_vagas_recomendadas(pcd_profile, limit=10)

# Buscar candidatos compatíveis com uma vaga
candidatos = get_candidatos_recomendados(vaga, limit=10)

# Calcular compatibilidade específica
resultado = calcular_compatibilidade(pcd_profile, vaga)
# Retorna: {'score': 85, 'nivel': 'Excelente', 'detalhes': {...}}

# Executar matching diário manualmente
stats = executar_matching_diario()
```

### 8.2 Criar Notificações

```python
from core.views import criar_notificacao_avaliacao_pcd, criar_notificacao_avaliacao_vaga

# Notificar PCD após avaliação
criar_notificacao_avaliacao_pcd(pcd_profile, status_medico='enquadravel')

# Notificar empresa após avaliação de vaga
criar_notificacao_avaliacao_vaga(vaga, status_medico='aprovada')
```

---

## 9. Migrations Realizadas

### 9.1 Arquivo: `userpcd/migrations/0003_*.py`

**Alterações em PerfilPCDExtendido:**
- ✅ Adicionado campo `observacoes_medicas` (TextField)
- ✅ Adicionado campo `data_avaliacao_medica` (DateTimeField)
- ✅ Adicionado campo `medico_avaliador` (ForeignKey para User)
- ✅ Alterado `status_medico` para incluir 5 estados (max_length=30)

### 9.2 Arquivo: `usercompany/migrations/0002_*.py`

**Alterações em VagaExtendida:**
- ✅ Adicionado campo `data_avaliacao_medica` (DateTimeField)
- ✅ Adicionado campo `medico_avaliador` (ForeignKey para User)

---

## 10. Próximos Passos Recomendados

### 10.1 Funcionalidades Adicionais

- [ ] Dashboard para Root com estatísticas gerais
- [ ] Relatórios de matching (PDF)
- [ ] Sistema de agendamento de avaliações presenciais
- [ ] Integração com calendário para telemedicina
- [ ] Envio de emails em vez de apenas notificações internas
- [ ] Sistema de mensagens entre médico e PCD
- [ ] Histórico de avaliações médicas

### 10.2 Melhorias de UX

- [ ] Filtros avançados nas listagens
- [ ] Paginação nas listagens
- [ ] Busca por texto
- [ ] Ordenação customizável
- [ ] Exportação de listas (CSV, Excel)

### 10.3 Infraestrutura

- [ ] Configurar servidor de emails
- [ ] Configurar Celery para tasks assíncronas
- [ ] Adicionar cache (Redis)
- [ ] Implementar logs estruturados
- [ ] Monitoramento e alertas

---

## 11. Contatos e Suporte

Para dúvidas ou suporte sobre o sistema:
- **Documentação técnica**: Este arquivo
- **Issues**: GitHub Issues
- **Email**: suporte@portalpcd.com.br

---

**Última atualização:** 10/11/2025
**Versão:** 1.0.0
**Autor:** Sistema Automatizado
