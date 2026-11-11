# Como atualizar o bloco "Próximo culto" (site + dashboard)

Todas as tarefas automáticas que mexem no bloco "Próximo culto" seguem ESTE procedimento, à risca e nesta ordem.
Regra do Neto: o site e o dashboard têm que terminar SEMPRE iguais e certos. Se alguma etapa falhar, ele é avisado.

## 1. Montar a entrada
- Parta do `dados/proximo.json` atual quando for o MESMO culto (mesma data): mantenha as músicas que já estão lá e só
  acrescente/corrija o que mudou no grupo. Nunca apague uma música que não foi tirada no grupo.
- Grave em `/tmp/proximo_bruto.json`:
  `{"data":"AAAA-MM-DD","culto":"Domingo","evento":"Santa Ceia ou vazio","equipe":[{"funcao":"Voz","nomes":"..."}],"musicas":[{"titulo":"...","cantor":"...","tom":"...","link":"https://...","letra":"<se já houver>"}]}`
- Equipe na ordem Voz, Teclado, Guitarra, Violão, Baixo, Bateria (junte funções da mesma pessoa; omita VS).
- Músicas na ordem do repertório, com QUEM CANTA (não o artista); sem cantor ou tom, deixe vazio.
- **Tom da planilha (regra do Neto):** se a música chegou no grupo SEM tom, deixe o tom vazio na entrada: o proximo.py
  preenche sozinho com o tom daquele cantor na planilha (dados/tons.json) e marca `"tom_origem": "planilha"`. Ao partir
  do proximo.json atual, mantenha o campo `tom_origem` como está. Se o grupo postar um tom, coloque o tom do grupo
  (ele vale por cima e o proximo.py tira a marca). No aviso pelo bot, tom da planilha aparece como "🎼 Tom: X (da planilha)".
- **Música da Santa Ceia:** a do momento da Ceia não é uma das 4 músicas normais. Coloque nela `"momento":"Ceia"`.
  Ela é SEMPRE a nº 5: o site e o dashboard mostram "5. 🍷 Ceia: <música>" e as vagas 3/4 ainda sem música como
  "❓ A definir". No aviso pelo bot: "*5\. 🍷 Ceia: Nome da Música*".
- Links de letra: só MultiTracks ou Letras.mus.br, gravados em `dados/letras.json` (nunca copiar a letra). Link do
  MultiTracks SEMPRE pelo site brasileiro `https://www.multitracks.com.br/songs/...` (regra do Neto: é ele que mostra a letra
  em português que o ministério canta; o proximo.py converte sozinho se vier multitracks.com).

## 2. Gerar
`python3 -I automacao/proximo.py --repo <clone> --entrada /tmp/proximo_bruto.json`

Confira na saída que todas as músicas estão lá, na ordem certa, com cantor/tom/link certos. Se não estiverem, corrija a
entrada e rode de novo.

## 3. Publicar no site (PRIMEIRO o site, DEPOIS o dashboard)
`python3 -I automacao/publicar.py --repo <clone> --msg "Próximo culto DD/MM: repertório"`

- `"status": "sem_mudancas"` → nada mudou: NÃO mexa no dashboard. Fim.
- `"status": "erro"` → NÃO mexa no dashboard. Avise o Neto pelo bot (ver etapa 5) dizendo a etapa e o detalhe.
- `"status": "publicado"` → siga para a etapa 4 com o `arquivo_dashboard` e o `sha256` impressos.

## 4. Atualizar o dashboard (artifact `3858bb77-c142-48ff-8d11-398ba38d4772`)
1. `upload_asset` do `arquivo_dashboard` com name `proximo.json`. Confira que o `sha256` devolvido é IGUAL ao impresso
   pelo publicar.py. Se não for, repita o upload uma vez; se ainda não bater, avise o Neto e pare.
2. `db_get` de `datasets/proximo` para pegar a `version`.
3. `db_write` op `update` com `ifVersion`, trocando `source` para
   `{"kind":"file","url":<url do upload>,"name":"proximo.json"}` e `updated` para
   `{"at":<agora ISO>,"by":"Claude (tarefa automática): próximo culto DD/MM"}`. Se der conflito de versão, faça
   `db_get` de novo e repita.
4. `db_get` de `datasets/proximo` mais uma vez e confira que o `source.url` é o do seu upload.
Se as ferramentas do dashboard não estiverem disponíveis, avise o Neto que o site foi atualizado mas o dashboard não.

## 5. Aviso de falha
Qualquer falha nas etapas 3 ou 4 → mensagem pelo bot (ferramenta "reply" do plugin telegram, chat_id `1008078957`,
sem formatação especial): "⚠️ Próximo culto DD/MM: falhou <etapa> — <detalhe curto>. Site: <atualizado/não>.
Dashboard: <atualizado/não>." Nunca termine a tarefa com o site e o dashboard diferentes sem avisar.

## Arquivos
No repositório, só altere `dados/proximo.json`, `dados/proximo_linhas.json`, `dados/letras.json`, `dados/escala.json` e `index.html`.
Nunca altere a planilha nem os outros dados.
