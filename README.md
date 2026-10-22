# Bot Maps — Clínicas sem site

Versão reestruturada do `bot_maps.py`.

## O que mudou

- Não exige telefone celular.
- Aceita telefone fixo, celular ou nenhum telefone.
- Pesquisa os perfis do Google Maps primeiro e depois abre cada perfil.
- Filtra os estabelecimentos que possuem website cadastrado.
- Salva CSV e JSON.
- Usa vários seletores de fallback.
- Usa Selenium Manager; não precisa instalar ChromeDriver manualmente.
- Tem argumentos para trocar bairro, termo e quantidade.
- Para quando aparece CAPTCHA/verificação, sem tentar contorná-la.

## Instalação no VS Code

No terminal, dentro da pasta:

```bash
python -m venv .venv
```

CMD:

```bash
.venv\Scripts\activate
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Depois:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Primeiro teste

```bash
python bot_maps.py
```

Ele procura 10 clínicas sem site em:

```text
Penha de França, São Paulo - SP
```

O Chrome será aberto para você acompanhar.

## Exemplos

20 clínicas no Tatuapé:

```bash
python bot_maps.py --local "Tatuapé, São Paulo - SP" --quantidade 20
```

Clínicas odontológicas na Mooca:

```bash
python bot_maps.py --local "Mooca, São Paulo - SP" --termo "clínicas odontológicas" --quantidade 20
```

Psicólogos:

```bash
python bot_maps.py --local "Penha, São Paulo - SP" --termo "psicólogos" --quantidade 20
```

## Arquivos gerados

Depois da execução:

```text
saida/
  clinicas_sem_site_....csv
  clinicas_sem_site_....json
```

O CSV abre no Excel.

## Observação

O Google Maps muda a estrutura da página com frequência. Esta versão reduz
a dependência de um único seletor, mas mudanças futuras do Maps ainda podem
exigir manutenção.

O script não tenta contornar CAPTCHA ou outras verificações do Google.
