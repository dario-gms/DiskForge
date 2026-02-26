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
- **Executável Windows compilado** (`DiskForge.exe`) — pronto para usar, sem instalação
- Python já embutido no executável — sem dependências externas
- Clique duplo para executar — não requer terminal ou Python instalado
- ~80-150 MB total (tudo incluído)

### 📋 Requisitos
- Windows 10/11 (64-bit)
- Sem dependências externas

---

**[Veja o README completo para documentação técnica e solução de problemas](README.md)**
