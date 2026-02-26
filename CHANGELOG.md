# Changelog

## [1.1.0] - 2026-02-26

### ✨ Novos Recursos
- Suporte a 9 formatos de disco: RAW, QCOW2, VMDK, VDI, VHDX, VHD, QCOW, QED e Parallels HDD
- Conversão universal entre **qualquer combinação** de formatos
- Interface gráfica profissional sem necessidade de linha de comando
- Barra de progresso em tempo real com ETA dinâmico
- Log detalhado com timestamps e ícones de status
- Detecção automática de `qemu-img` embutido
- Suporte a HiDPI em displays de alta densidade

### 🎨 Interface
- Seletor visual de formatos com descrições e hypervisors associados
- Sidebar com status da ferramenta e lista de formatos
- Layout intuitivo com 2 cards (entrada/saída) e botão de ação centralizado
- Log estruturado com cores e ícones: `ℹ`, `✓`, `⚠`, `✗`, `·`

### 🔧 Técnico
- Arquitetura thread-safe com `queue.Queue`
- Execução em thread separada (não bloqueia UI)
- Parsing de progresso em tempo real
- Cálculo dinâmico de ETA baseado em throughput
- Tratamento robusto de erros com mensagens informativas

### 📦 Distribuição
- **Um único arquivo Python** — não requer instalação
- `qemu-img` já embutido em `tools/qemu/` — sem downloads adicionais
- Executável direto via duplo clique em `DiskForge.pyw`
- ~50 MB total (ferramenta + binários)

### 📋 Requisitos
- Windows 10/11 (64-bit)
- Python 3.8+
- tkinter (incluído no Python padrão)
- Sem dependências externas

---

**[Veja o README completo para documentação técnica e solução de problemas](README.md)**
