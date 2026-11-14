# Repertório no MultiTracks (regra do Neto, nov/2026)

QUANDO RODA (regra do Neto, 14/11): só no SÁBADO DE MANHÃ (na verificação do grupo de sábado 10h13) ou quando o Neto pedir.

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
Se não estiver pronto, não mexa no MultiTracks — EXCETO se o setlist deste culto já existir (`"ja_criado_antes": true`; o
Neto às vezes pede para criar antes com o que já tem): aí mantenha-o igual ao proximo.json a cada mudança (músicas
"❓ A definir" ficam fora do setlist, na ordem das definidas).

## Onde fazer
- SEMPRE pelo navegador interno do app do Claude (ferramentas mcp__remote-devices__Claude_Browser__*; regra do Neto),
  NUNCA pelo Chrome. Se o navegador interno não estiver disponível ou o MultiTracks estiver deslogado lá ("Entrar no
  MultiTracks.com.br" / "Sua conta se conectou em outro local"), não digite senha e não use outro navegador: avise pelo
  bot "⚠️ Repertório DD/MM: não consegui atualizar o setlist no MultiTracks (<motivo>)" e siga com o resto da tarefa; a
  próxima verificação tenta de novo. A conta só aceita um login por vez.
- ORGANIZAÇÕES (regra do Neto): o mesmo setlist `Culto DD/MM/AAAA` fica nas DUAS organizações da conta dele:
  "Comunidade" (#366786, a pessoal, que ele usa para estudar em casa) e "Comunidade Cristã de Taquaritinga" (#75254, a
  da igreja, que dispara os VS). Faça o passo a passo abaixo inteiro numa organização e depois na outra.
  Para saber em qual está: abra https://www.multitracks.com.br/premium/account/user/ e leia o nome ao lado de
  "Mudar Organização" no topo. Para trocar: "Mudar Organização" (https://www.multitracks.com.br/login/orgSelector.aspx)
  e escolha pelo nome e número. Confira a organização antes de criar/editar em cada uma. No fim, deixe o MultiTracks na
  organização "Comunidade Cristã de Taquaritinga".
  Se não conseguir terminar numa delas, não marque o registro (passo 7) e avise o Neto dizendo em qual faltou.
- Abra uma aba nova (tabs_create) e feche-a no fim. Lista de repertórios:
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
   confira "Data*" = data do culto (DD/MM/AAAA); deixe o "Tipo de Culto" e o horário como vierem (na igreja o padrão é
   "Celebração de Domingo" 18:00–20:00) → "CRIAR REPERTÓRIO". Depois clique em "Editar Repertório" para adicionar músicas.
3. No repertório criado (ou em "Editar Repertório"), para cada música na ordem do proximo.json (a da Ceia por último):
   "Adicionar Item" → no campo de busca, digite o nome da música (para versão em inglês use o nome original, ex.:
   "Sou Grato por seu Amor" = "God I'm Just Grateful (Live)" do Elevation Worship; se a busca pelo nome não achar, busque
   pelo ARTISTA, ex.: "Drops INA" → "Tudo é Teu") → escolha a MESMA versão do link da música (artista do repertório base
   em dados/repertorio.json ou o canal do link pelo oEmbed do YouTube) → abre "Adicionar Música ao Repertório": escolha o
   Tom ali (passo 4) → "ADICIONAR". Ao trocar de busca, limpe o campo antes (ctrl+a e digite), senão o texto se junta. Se a busca não disparar depois de digitar, aperte espaço e Backspace. Os títulos aparecem traduzidos (ex.: "Goodness of God" do Bethel aparece como "Bondade de Deus — Bethel Music").
   Nunca clique em "Comprar ou Alugar Tracks" nem "Solicitar Pad da Música".
   Se a música não existir no MultiTracks, NÃO crie música no Cloud: pule e anote para o aviso.
4. Tons: na janela "Adicionar Música ao Repertório" (ou clicando no tom da música com o repertório em edição) há os
   botões C D E F G A B e, embaixo, ♭ e #. A música vem marcada no tom original, às vezes com ♭ ou # ligado: clique na
   nota do proximo.json e depois confira o ♭/#: ligue o certo ou DESLIGUE clicando nele de novo (ex.: veio Bb e o tom é
   G → clique G e desligue o ♭). Dê um zoom para conferir antes de adicionar. Menor (ex.: "F#m") → "Menor".
   ATENÇÃO: a janela às vezes muda de altura depois do primeiro clique; tire um screenshot antes de clicar em ♭/#.
   PAD AMBIENTE (regra do Neto, 14/11): na organização da IGREJA, toda música fica com "Guitar Pads" no campo "Pad Ambiente"
   (select #ambientPad, valor 22; pelo javascript_tool: el.value='22' + evento change). Na pessoal, deixe "Pad Ambiente Padrão".
4b. PESSOAS (só na organização da igreja): menu "..." do repertório → "Adicionar/Remover Pessoas" → do lado esquerdo,
   clique no ⊕ de cada pessoa escalada no culto (equipe do proximo.json; nomes no MultiTracks: Ana Negreli, Andrey
   Monteiro Bertoletti, Beatriz Vasconcelos (Bia), Bianca Scavoni, Débora Oliveira, Leonardo Santos (Léo), Lucas Isaac,
   Marcelo Rodrigues, Marianne Gonçalves, Neto Leodoro, Samuel Silva (Samuel), Talita Freire, Wesley Tondati; o Cadu e o Levi só depois de
   aceitarem o convite) → "Atualizar Repertório". Quem saiu da escala: ⊖ do lado direito. Quem não está no MultiTracks
   (ex.: Daniel, Pra. Iraci) fica de fora sem aviso. NÃO use "Notificar Time"/"Email Team" nem "Adicionar Todas as
   Pessoas". Na organização pessoal não há pessoas.
4c. Música SEM TOM ainda (só quando o setlist já existe e o Neto pediu para manter): adicione no tom original que o
   MultiTracks sugere e diga no aviso que o tom é provisório; corrija quando o grupo postar o tom.
4d. Item que não é música (ex.: click "70BPM 4/4" que o Neto pôs no lugar de uma música fora do MultiTracks): se a música
   que ele substituía saiu do repertório, pergunte ao Neto (ou, sem ele, deixe e avise) antes de remover.
5. Se o repertório já existia: compare com o proximo.json e corrija só o que mudou (músicas, ordem pelo arraste das
   tons) e, na igreja, as pessoas. Música que saiu do repertório: remova pelo menu "..." da linha.
   TROCAR A ORDEM: o arraste pelas três barras NÃO funciona pela automação. Faça assim (combinado com o Neto): remova
   pelo "..." → "Remover" as músicas que precisam ir para depois e adicione-as de novo, na ordem, conferindo o tom de
   cada uma (passo 4). Só salve no fim, depois de conferir a ordem pelo texto da página.
6. "Salvar no Cloud" (abre uma janela com "Nota": deixe vazia e clique "Salvar no Cloud" de novo). Recarregue a página e confira pelo texto (get_page_text) que nomes, ordem e tons batem com o
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
