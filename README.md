<div align="center">

# ◈ DiskForge

**Conversor de discos virtuais para Windows**

Converta discos VMDK e VDI em imagens inicializáveis com interface gráfica profissional — sem linha de comando.

[![Python](https://img.shields.io/badge/Python-3.8%2B-4d7cfe?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-4d7cfe?style=flat-square&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-27c87a?style=flat-square)](LICENSE)
[![Arquivo único](https://img.shields.io/badge/Distribui%C3%A7%C3%A3o-arquivo%20%C3%BAnico-f5a623?style=flat-square)]()

</div>

---

## Índice

- [Sobre](#sobre)
- [Funcionalidades](#funcionalidades)
- [Modos de conversão](#modos-de-conversão)
- [Requisitos](#requisitos)
- [Instalação e uso](#instalação-e-uso)
- [Interface](#interface)
- [Como usar cada modo](#como-usar-cada-modo)
- [Usando os arquivos gerados](#usando-os-arquivos-gerados)
- [Arquitetura técnica](#arquitetura-técnica)
- [Solução de problemas](#solução-de-problemas)
- [Localização dos arquivos](#localização-dos-arquivos)
- [Glossário](#glossário)
- [Licença](#licença)

---

## Sobre

DiskForge é uma ferramenta desktop para Windows que simplifica a migração de máquinas virtuais entre hypervisors (VirtualBox, VMware, QEMU/KVM). Ela envolve o motor padrão da indústria `qemu-img` em uma interface gráfica limpa, com gerenciamento automático de dependências, progresso em tempo real e log detalhado.

A aplicação inteira é distribuída como **um único arquivo Python** — sem instalador, sem dependências externas além do próprio Python.

---

## Funcionalidades

- **3 modos de conversão** — VMDK→IMG, VDI→VMDK e VDI→IMG em uma única ferramenta
- **Instalação automática do qemu-img** — baixa e instala o build correto para Windows com todas as DLLs necessárias, sem configuração manual
- **Progresso em tempo real** — percentual, tempo decorrido e ETA atualizados ao vivo durante a conversão
- **Indicador de etapas** — pipeline visual mostrando qual estágio está ativo, concluído ou pendente
- **Log com timestamp** — cada comando, resultado e erro é registrado com ícones e horário
- **Caminho de destino automático** — o nome do arquivo de saída é sugerido automaticamente com base na origem
- **Suporte a HiDPI** — chama `SetProcessDpiAwareness` na inicialização para renderização nítida em monitores de alta resolução
- **Sem janela de terminal** — subprocessos usam `CREATE_NO_WINDOW`; nenhum console preto aparece durante a conversão
- **Arquivo único** — sem instalador, basta copiar e executar

---

## Modos de conversão

| Modo | Entrada | Saída | Uso |
|------|---------|-------|-----|
| `VMDK → Imagem Inicializável` | `.vmdk` | `.img` (RAW) | Arquivar um disco VMware/QEMU como imagem bootável preservando todos os dados e layout de partições |
| `VDI → VMDK` | `.vdi` | `.vmdk` | Migrar um disco VirtualBox para VMware ou QEMU sem trocar de hypervisor |
| `VDI → Imagem Inicializável` | `.vdi` | `.img` (RAW) | Migração completa do VirtualBox para imagem RAW bootável via pipeline interno de dois estágios |

> **Nota sobre `.img` vs `.iso`:** Uma imagem RAW (`.img`) é uma cópia byte a byte do disco inteiro — tabela de partições, bootloader e dados. ISO é um formato para mídias ópticas somente-leitura e **não** serve para migração de disco rígido.

---

## Requisitos

| Componente | Versão |
|-----------|--------|
| Sistema operacional | Windows 10 ou 11 (64-bit) |
| Python | 3.8 ou superior |
| tkinter | Incluído no instalador padrão do CPython para Windows |
| qemu-img | Instalado automaticamente pelo DiskForge na primeira execução |
| Conexão com internet | Necessária apenas para a instalação inicial do qemu-img (~30 MB) |
| Espaço em disco | ~150 MB para qemu-img + DLLs, mais o tamanho da imagem gerada |

---

## Instalação e uso

### 1. Instale o Python

Baixe o Python 3.8 ou superior em [python.org/downloads](https://python.org/downloads).  
Durante a instalação, marque a opção **"Add Python to PATH"**.

### 2. Baixe o DiskForge

Baixe o arquivo `disk_converter.py` deste repositório e salve em qualquer pasta.  
Caminhos curtos sem espaços são recomendados, por exemplo:

```
C:\Tools\DiskForge\disk_converter.py
```

### 3. Execute

Abra o PowerShell ou Prompt de Comando na pasta do arquivo e execute:

```powershell
python disk_converter.py
```

A janela do DiskForge abrirá imediatamente.

### 4. Instale o qemu-img (apenas na primeira execução)

Na primeira abertura, o indicador `qemu-img` na barra lateral estará vermelho (✕).  
Clique em **"⬇ Instalar qemu-img"** e aguarde. A aplicação irá:

1. Consultar a GitHub API para obter a URL do build mais recente
2. Baixar o pacote ZIP portátil (~30 MB) para `%USERPROFILE%\.diskforge\tools\`
3. Extrair o `qemu-img.exe` e todas as DLLs necessárias
4. Executar um autoteste para confirmar que o binário funciona
5. Atualizar o indicador na sidebar para verde (●)

> **Dica:** Se o `qemu-img` já estiver instalado no sistema e na variável `PATH`, o DiskForge o detectará e usará automaticamente — sem necessidade de download.

---

## Interface

A janela do DiskForge é dividida em quatro zonas:

```
┌─────────────────┬──────────────────────────────────────────────┐
│                 │  Título e descrição do modo                  │
│   OPERAÇÕES     ├─────────────────────────────┬────────────────┤
│                 │  Arquivo de Origem          │  ETAPAS        │
│  ◈ VMDK → IMG   │  Arquivo de Destino         │  ○ Etapa 1     │
│  ⬡ VDI → VMDK   │                             │  ◉ Etapa 2     │
│  ⬢ VDI → IMG    ├─────────────────────────────┴────────────────┤
│                 │  47.3%          Decorrido: 23s    ETA: 31s   │
│  FERRAMENTAS    │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │
│  ● qemu-img     ├──────────────────────────────────────────────┤
│                 │  LOG DE SAÍDA                       limpar   │
│                 │  [14:23:39] · (77.01/100%)                   │
│                 │  [14:23:54] ✓ Imagem gerada (30.0 GB)        │
├─────────────────┴──────────────────────────────────────────────┤
│  Concluído!                          ▶ Iniciar Conversão       │
└────────────────────────────────────────────────────────────────┘
```

### Sidebar — OPERAÇÕES

Três botões de navegação, um por modo. O modo ativo é destacado com uma borda azul à esquerda.

### Sidebar — FERRAMENTAS

Exibe o status do `qemu-img`:
- **● verde** — encontrado e pronto para uso
- **✕ vermelho** — não encontrado; use o link de instalação abaixo

### Área de conteúdo

- **Arquivo de Origem** — caminho do disco a converter. Clique em *Procurar* para abrir o seletor de arquivos. O tamanho do arquivo é exibido abaixo do campo após a seleção.
- **Arquivo de Destino** — preenchido automaticamente ao selecionar a origem (sufixo `_converted` + extensão correta). Pode ser alterado manualmente ou via *Procurar*.
- **Etapas** — indicador visual do pipeline à direita, atualizado em tempo real.

### Barra de progresso

Mostra percentual (ex: `47.3%`), tempo decorrido e ETA calculados a partir do throughput atual.

### Log de saída

Cada linha tem timestamp e ícone:

| Ícone | Tipo | Significado |
|-------|------|-------------|
| `ℹ` | info | Mensagens de status gerais |
| `✓` | ok | Confirmações de sucesso |
| `⚠` | warn | Avisos não fatais |
| `✗` | error | Erros que interromperam a operação |
| `·` | log | Saída bruta do qemu-img |

---

## Como usar cada modo

### VMDK → Imagem Inicializável

Converte um disco VMware ou QEMU em uma imagem RAW bootável.

1. Clique em **"VMDK → Imagem Inicializável"** na sidebar
2. Selecione o arquivo `.vmdk` de origem
3. Confirme o caminho de destino (`.img`)
4. Clique em **"▶ Iniciar Conversão"**

O comando executado internamente é:
```
qemu-img convert -p -f vmdk -O raw <origem.vmdk> <destino.img>
```

---

### VDI → VMDK

Converte um disco VirtualBox para o formato VMDK, compatível com VMware e QEMU.

1. Clique em **"VDI → VMDK"** na sidebar
2. Selecione o arquivo `.vdi` de origem
3. Confirme o caminho de destino (`.vmdk`)
4. Clique em **"▶ Iniciar Conversão"**

O comando executado internamente é:
```
qemu-img convert -p -f vdi -O vmdk <origem.vdi> <destino.vmdk>
```

---

### VDI → Imagem Inicializável (pipeline de dois estágios)

Migração completa do VirtualBox para imagem RAW. O DiskForge executa dois estágios internamente:

```
Estágio 1:  origem.vdi  →  temp_intermediario.vmdk   (0% – 50%)
Estágio 2:  temp.vmdk   →  destino.img               (50% – 100%)
            temp.vmdk   →  (removido automaticamente)
```

1. Clique em **"VDI → Imagem Inicializável"** na sidebar
2. Selecione o arquivo `.vdi` de origem
3. Confirme o caminho de destino (`.img`)
4. Clique em **"▶ Iniciar Conversão"**

> **Atenção:** O estágio intermediário cria um arquivo `.vmdk` temporário. Certifique-se de que o disco de destino tenha espaço livre equivalente a pelo menos **2× o tamanho do disco virtual** (VMDK temporário + IMG final). O arquivo temporário é removido automaticamente ao final.

---

## Usando os arquivos gerados

### Importar `.img` no VirtualBox

O VirtualBox não aceita `.img` diretamente pela interface gráfica. Use o `VBoxManage` para converter para `.vdi` antes de importar:

```powershell
"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" convertfromraw `
  "E:\VM\disco_converted.img" `
  "E:\VM\disco_novo.vdi" --format VDI
```

Depois, crie uma nova VM no VirtualBox e na etapa de disco escolha **"Usar um disco rígido virtual existente"**, apontando para o `.vdi` gerado.

Para manter no formato VMDK:
```powershell
VBoxManage convertfromraw "disco.img" "disco.vmdk" --format VMDK
```

### Importar `.vmdk` no VMware

Crie uma nova máquina virtual no VMware Workstation ou Player. Quando solicitado a selecionar um disco, escolha **"Use an existing virtual disk"** e selecione o `.vmdk` gerado pelo DiskForge.

### Inicializar `.img` diretamente com QEMU

```bash
qemu-system-x86_64 -hda "disco_converted.img" -m 2048 -enable-kvm
```

---

## Arquitetura técnica

### Stack

| Camada | Tecnologia |
|--------|-----------|
| Interface gráfica | `tkinter` (stdlib Python) — widgets customizados com `Canvas` |
| Motor de conversão | `qemu-img` — suporta 40+ formatos de imagem |
| Threading | `threading.Thread` — conversão em thread separada; polling via `Tk.after(80ms)` |
| Comunicação entre threads | `queue.Queue` — passagem de mensagens thread-safe |
| Gerenciamento de dependências | GitHub API → download via `urllib` → extração com `zipfile` |
| Controle de processos | `subprocess.Popen` com `CREATE_NO_WINDOW`; stdout lido linha a linha |
| HiDPI | `SetProcessDpiAwareness(1)` via `ctypes.windll.shcore` |

### Processo de instalação do qemu-img

```
1. GET https://api.github.com/repos/fdcastel/qemu-img-windows-x64/releases/latest
2. Extrai URL do asset .zip com "x64" no nome
3. Download em chunks de 64 KB com callbacks de progresso
4. Extração plana de todos os arquivos (exe + DLLs) em %USERPROFILE%\.diskforge\tools\
5. qemu-img.exe --version → verifica exit code 0
6. Atualiza UI via queue
```

> O repositório `fdcastel/qemu-img-windows-x64` fornece builds portáteis do qemu-img para Windows com todas as DLLs do Visual C++ incluídas, extraídas dos builds oficiais de Stefan Weil ([qemu.weilnetz.de](https://qemu.weilnetz.de)).

### Comandos executados por modo

**VMDK → IMG**
```
qemu-img convert -p -f vmdk -O raw <origem> <destino>
```

**VDI → VMDK**
```
qemu-img convert -p -f vdi -O vmdk <origem> <destino>
```

**VDI → IMG**
```
qemu-img convert -p -f vdi  -O vmdk <origem> <temp.vmdk>
qemu-img convert -p -f vmdk -O raw  <temp.vmdk> <destino>
del <temp.vmdk>
```

### Parsing de progresso

O DiskForge captura a saída do `qemu-img` com a flag `-p` e extrai o percentual com a expressão regular:

```python
re.search(r"\((\d+(?:\.\d+)?)/100%\)", line)
```

O ETA é calculado a partir do tempo decorrido e do percentual atual:

```python
total_estimado = tempo_decorrido / (pct / 100)
eta = total_estimado - tempo_decorrido
```

---

## Solução de problemas

### `python` não é reconhecido no PowerShell

O Python não está na variável `PATH`. Reinstale e marque **"Add Python to PATH"**, ou use o caminho completo:
```powershell
C:\Python312\python.exe disk_converter.py
```

---

### Download do qemu-img falha com HTTP 404

A URL da release pode ter mudado. Delete a pasta de ferramentas e tente novamente:
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.diskforge\tools"
```
Se o problema persistir, instale o QEMU manualmente em [qemu.org/download/#windows](https://www.qemu.org/download/#windows) e adicione a pasta ao `PATH`.

---

### Conversão falha com código `3221225781` (0xC0000135)

Uma DLL necessária está faltando. Esse erro indica que a instalação anterior ficou incompleta. Delete a pasta e reinstale:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.diskforge\tools"
```

Reabra o DiskForge e clique em **"⬇ Instalar qemu-img"** novamente.

---

### Arquivo de saída maior que o esperado

Imagens RAW sempre têm o tamanho total do disco virtual, independente do espaço realmente usado. Um disco de 100 GB com 10 GB de dados gera um `.img` de 100 GB. Isso é esperado — é uma cópia fiel do disco.

---

### Pipeline VDI → IMG falha no estágio 2

Verifique se o disco de destino tem espaço livre equivalente a **2×** o tamanho do disco virtual (VMDK temporário + IMG final). O arquivo temporário é removido automaticamente, mas ambos precisam existir simultaneamente durante a conversão.

---

### Janela borrada em monitor HiDPI

O DiskForge já chama `SetProcessDpiAwareness(1)` na inicialização. Se ainda assim aparecer borrado, clique com botão direito em `disk_converter.py` → **Propriedades** → **Compatibilidade** → **"Substituir comportamento de ajuste de DPI alto"** → **Sistema (Avançado)**.

---

## Localização dos arquivos

O DiskForge armazena tudo em uma única pasta dentro do diretório do usuário:

```
%USERPROFILE%\.diskforge\
└── tools\
    ├── qemu-img.exe
    ├── *.dll                        (bibliotecas de runtime)
    └── qemu-img-portable.zip        (baixado e removido após extração)
```

Para **desinstalar completamente** o DiskForge, delete esta pasta e o arquivo `disk_converter.py`. Nenhuma entrada de registro ou outro local do sistema é utilizado.

---

## Glossário

| Termo | Definição |
|-------|-----------|
| **VMDK** | Virtual Machine Disk — formato de disco usado pelo VMware e suportado pelo QEMU |
| **VDI** | VirtualBox Disk Image — formato nativo do Oracle VirtualBox |
| **RAW / IMG** | Cópia setor a setor de um disco. Contém tabela de partições, bootloader e todos os dados. Sem compressão. Compatível universalmente. |
| **ISO** | Formato de imagem de disco óptico (ISO 9660). Projetado para sistemas de arquivos somente-leitura de CD/DVD. Não serve para migração de disco rígido. |
| **qemu-img** | Ferramenta de linha de comando do projeto QEMU para criar, converter e inspecionar imagens de disco. |
| **VBoxManage** | Ferramenta de gerenciamento CLI do VirtualBox. Pode converter imagens RAW para VDI/VMDK para importação no VirtualBox. |
| **Imagem inicializável** | Imagem de disco que contém uma tabela de partições válida, MBR ou GPT, e um bootloader — permitindo que seja usada como disco rígido virtual a partir do qual um SO pode iniciar. |
| **DLL** | Dynamic-Link Library — biblioteca compartilhada do Windows. O `qemu-img.exe` requer várias DLLs; o DiskForge as extrai junto com o executável. |
| **HiDPI** | Displays de alta densidade de pixels (ex: 4K). Requer que aplicativos declarem suporte a DPI para renderização nítida. |
| **Pipeline** | Sequência encadeada de operações. No modo VDI→IMG, o pipeline executa duas conversões em sequência: VDI→VMDK e VMDK→RAW. |

---

## Licença

Este projeto está licenciado sob a **Licença MIT** — veja o arquivo [LICENSE](LICENSE) para detalhes.

```
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> **Nota sobre dependências:** O `qemu-img` é distribuído sob a [GNU General Public License v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html). O DiskForge apenas chama o `qemu-img` como processo externo — não incorpora, modifica ou distribui seu código-fonte.

---

<div align="center">

Feito com Python e tkinter · Motor de conversão: [QEMU](https://www.qemu.org/) · Build Windows: [fdcastel/qemu-img-windows-x64](https://github.com/fdcastel/qemu-img-windows-x64)

</div>
