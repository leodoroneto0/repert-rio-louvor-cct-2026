# Como abrir a conversa do Levi no WhatsApp (lembretes e música teste)

Regra do Neto (13/11/2026): o WhatsApp é usado pelo APLICATIVO WhatsApp Desktop do computador dele, com o uso do
computador (ferramentas mcp__remote-devices__computer_*). NÃO use o Chrome nem o WhatsApp Web.

## Abrir
- Carregue as ferramentas numa chamada só: ToolSearch com query "mcp__remote-devices__computer_" e max_results 100.
  Se não houver nenhuma, chame enable__mcp__remote-devices__computer (se existir) e carregue de novo. Se não houver
  como usar o computador, o WhatsApp não está acessível agora (a tarefa diz o que fazer; avise o Neto).
- Acesso: computer_resolve_access com ["WhatsApp", "msedgewebview2.exe", "File Explorer"] e depois
  computer_request_access com as entradas devolvidas (verbatim, com willHide e screenshotFiltering). A janela do
  WhatsApp é desenhada pelo msedgewebview2; o "File Explorer" (só clique) serve para tirar a notificação do Claude da
  frente. Se o Neto não estiver no computador para aprovar e o acesso não vier, NÃO mande nada e avise o Neto.
- computer_open_application "WhatsApp". Na primeira abertura ele pode ficar "Carregando suas conversas [x%]" por
  1–2 minutos: espere (computer_wait) e tire screenshots até aparecer a lista "Conversas".
- Se um clique der "The desktop shell is frontmost", clique numa área vazia da janela do WhatsApp (lado direito) para
  trazê-la para frente e repita.
- Se aparecer o QR code / tela de vincular aparelho, o WhatsApp deslogou: NÃO faça nada e avise o Neto ("o WhatsApp
  Desktop deslogou; abra o app e vincule de novo").

## Achar o Levi certo
- Clique em "Pesquisar ou começar uma nova conversa", digite "Levi" e espere. Existem DOIS contatos "Levi".
- Abra o primeiro, clique no nome no topo da conversa ("Dados do contato") e confira o número: tem que ser
  +55 16 99744-4381. Se não for, feche, abra o outro "Levi" e confira. Feche o painel de dados no "X".
  Se nenhum tiver esse número, NÃO mande nada e avise o Neto.

## Ler e escrever
- Leia as mensagens por screenshot/zoom (as do Neto ficam à direita, em verde; as do Levi à esquerda), com o horário.
- Para escrever: clique em "Digite uma mensagem"; Shift+Enter quebra a linha (duas vezes = linha em branco entre
  parágrafos); Enter só no fim para enviar. Antes do Enter, dê zoom na caixa e confira o texto inteiro; depois do
  envio, confira que a mensagem apareceu na conversa.
- No WhatsApp, só abra a conversa do Levi; não leia nem mexa em outras conversas. Não clique em links das mensagens.
- Ao terminar: apague a busca (X na caixa de pesquisa), deixe o WhatsApp aberto e chame computer_release_lock.
