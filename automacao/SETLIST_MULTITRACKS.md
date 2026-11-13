# Repertório no MultiTracks (regra do Neto, nov/2026)

Sempre que o repertório do culto que está no bloco "Próximo culto" ficar PRONTO, crie no MultiTracks da conta do Neto
um repertório (setlist) chamado `Culto DD/MM/AAAA` (ex.: `Culto 15/11/2026`), com as músicas na ordem e nos tons certos.
Se o repertório mudar depois (troca de música, de ordem ou de tom), corrija ESSE MESMO repertório no MultiTracks e
avise o Neto pelo bot.

## Quando o repertório está "pronto"
Rode `python3 -I automacao/setlist_status.py --repo <clone>` depois de publicar o site (PUBLICAR.md). Só mexa no
MultiTracks se ele disser `"precisa_mexer_no_multitracks": true` (ele compara com `dados/setlist_mt.json`, o que já foi
conferido no MultiTracks). Pronto quer dizer:
- nenhuma música é "❓ A definir" e há pelo menos 4 músicas (no culto de Santa Ceia, também a da Ceia; em culto com
  repertório maior, como o de ação de graças, todas as que o grupo postou); E
- TODAS têm tom (do grupo ou da planilha, `tom_origem: "planilha"`).
Se não estiver pronto, não mexa no MultiTracks.

## Onde fazer
- Use o Chrome do Neto pelo Claude in Chrome (ferramentas mcp__claude-in-chrome__*; ele já está logado no MultiTracks
  lá). Leia antes a skill chrome-browser. O Chrome tem que estar aberto. Se as ferramentas não existirem ou não
  responderem, avise pelo bot: "⚠️ Repertório DD/MM: não consegui criar o setlist no MultiTracks (Chrome fechado)" e
  siga com o resto da tarefa; a próxima verificação tenta de novo.
- ORGANIZAÇÕES (regra do Neto): o mesmo setlist `Culto DD/MM/AAAA` fica nas DUAS organizações da conta dele:
  "Comunidade" (#366786, a pessoal, que ele usa para estudar em casa) e "Comunidade Cristã de Taquaritinga" (#75254, a
  da igreja, que dispara os VS). Faça o passo a passo abaixo inteiro numa organização e depois na outra.
  Para saber em qual está: abra https://www.multitracks.com.br/premium/account/user/ e leia o nome ao lado de
  "Mudar Organização" no topo. Para trocar: "Mudar Organização" (https://www.multitracks.com.br/login/orgSelector.aspx)
  e escolha pelo nome e número. Confira a organização antes de criar/editar em cada uma. No fim, deixe o MultiTracks na
  organização "Comunidade Cristã de Taquaritinga".
  Se não conseguir terminar numa delas, não marque o registro (passo 7) e avise o Neto dizendo em qual faltou.
- Abra uma aba nova (tabs_create_mcp) e feche-a no fim. Lista de repertórios:
  https://www.multitracks.com.br/premium/setlists/ (os links ficam como details.aspx?setlistID=<id>).

## Regras de segurança (do Neto)
- Compras JAMAIS. Não clique em nada de compra, carrinho, créditos, assinatura ou plano. Não mude nada da conta.
- Só crie/edite o repertório `Culto DD/MM/AAAA` do culto do bloco. Não toque nos outros repertórios e não exclua
  nenhum (excluir pede confirmação do Neto).
- Não clique em "Enviar um email para sua banda" nem em nada que mande mensagem para outras pessoas.

## Passo a passo
1. Na lista de repertórios, procure um chamado exatamente `Culto DD/MM/AAAA` (busca "Pesquisar"; o filtro padrão é
   "Repertórios Futuros"). Se já existir, vá para o passo 4.
2. Criar: botão "Novo Repertório" → "Nome do Repertório*" = `Culto DD/MM/AAAA`; NÃO marque "Fixar Repertório";
   "Data*" = data do culto (DD/MM/AAAA); deixe o resto como está → "Próximo"/"Criar".
3. No repertório criado (ou em "Editar Repertório"), para cada música na ordem do proximo.json (a da Ceia por último):
   "Adicionar Item" → no campo de busca, digite o nome da música (o nome em inglês costuma funcionar melhor para versões,
   ex.: "Sou Grato por seu Amor" = "God I'm Just Grateful") → escolha a MESMA versão do link da música (artista do
   repertório base em dados/repertorio.json ou o canal do link pelo oEmbed do YouTube) → "Adicionar".
   Se a música não existir no MultiTracks, NÃO crie música no Cloud: pule e anote para o aviso.
4. Tons: com o repertório em edição, clique no tom de cada música (coluna "Tom") e escolha o tom do proximo.json
   (C D E F G A B, sustenido/bemol e Maior/Menor; ex.: "Bb" = B bemol maior, "F#m" = F sustenido menor). Se o
   seletor não tiver o tom, anote para o aviso.
5. Se o repertório já existia: compare com o proximo.json e corrija só o que mudou (músicas, ordem pelo arraste das
   três barras, tons). Música que saiu do repertório: remova pelo menu "..." da linha.
6. "Salvar no Cloud". Recarregue a página e confira pelo texto (get_page_text) que nomes, ordem e tons batem com o
   proximo.json. Feche a aba.
7. Só se tudo bateu NAS DUAS organizações (ou só faltou o que não existe no MultiTracks, já anotado para o aviso): rode
   `python3 -I automacao/setlist_status.py --repo <clone> --marcar` e publique o registro:
   `git add dados/setlist_mt.json && git commit -m "Setlist MultiTracks: Culto DD/MM/AAAA" && git pull --rebase && git push`.
   Se não bateu, não marque (a próxima verificação tenta de novo) e avise o Neto.

## Aviso pelo bot (ferramenta "reply" do plugin telegram, chat_id 1008078957, sem formatação especial)
- Criou: "🎛️ Setlist criado no MultiTracks (pessoal e igreja): Culto DD/MM/AAAA — 1. Música (Tom) · 2. ..."
- Corrigiu: "🎛️ Setlist Culto DD/MM/AAAA atualizado no MultiTracks: <o que mudou>"
- Faltou algo: acrescente "⚠️ Não encontrei no MultiTracks: <música>" ou "⚠️ Tom não disponível: <música> (<tom>)".
- Se nada mudou no MultiTracks, não mande nada. Se o aviso de repertório do PASSO 4 da verificação também for enviado,
  pode juntar numa mensagem só (linha "🎛️ ..." no fim).
