#!/usr/bin/env python3
"""Atualiza o repertório do Louvor CCT a partir de cultos novos.

Uso:
  python3 -I automacao/atualizar.py --repo <pasta do repositório> --novos <novos.json> [--xlsx <planilha.xlsx>]

novos.json: lista de cultos já realizados, por exemplo
  [{"data": "2026-11-01", "tipo": "Domingo", "evento": "", "musicas": ["Meu Lugar", "Tu és Deus (A Ele)"]}]

O que faz:
  1. Padroniza o nome de cada música pela grafia do repertório base (dados/repertorio.json),
     usando dados/aliases.json para os casos conhecidos de grafia diferente.
  2. Ignora cultos cuja data já está registrada.
  3. Acrescenta os cultos em dados/registros.json.
  4. Se --xlsx for passado, acrescenta as linhas na aba Registros da planilha (editando o XML,
     para não perder os botões de link) e acrescenta ao ranking as músicas que ainda não estão nele.
  5. Gera de novo o index.html (página pública) a partir de automacao/template.html.
  6. Imprime um resumo em JSON.
Nunca altera a aba Repertório Base nem a aba Tons.
"""
import argparse, datetime, html, json, os, re, shutil, tempfile, unicodedata, zipfile


def chave(s):
    s = str(s).replace('’', "'").replace('´', "'")
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s)


def corrige_deus(nome):
    """Regra do Neto: em nome de música, "Deus" sempre com D maiúsculo."""
    return re.sub(r'\bdeus\b', 'Deus', nome, flags=re.I)


def carregar(p, padrao):
    return json.load(open(p, encoding='utf8')) if os.path.exists(p) else padrao


def salvar(p, obj):
    with open(p, 'w', encoding='utf8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)


def serial_excel(data):
    d = datetime.date.fromisoformat(data)
    return (d - datetime.date(1899, 12, 30)).days


def esc(s):
    return html.escape(str(s), quote=False)


CANTORES = {'ana': 'Ana', 'bia': 'Bia', 'beatriz': 'Bia', 'debora': 'Débora', 'elisa': 'Elisa', 'leo': 'Léo', 'leonardo': 'Léo',
            'levi': 'Pr. Levi', 'prlevi': 'Pr. Levi', 'pastorlevi': 'Pr. Levi', 'lucas': 'Lucas', 'marianne': 'Marianne', 'mariane': 'Marianne',
            'iraci': 'Pra. Iraci', 'praiaci': 'Pra. Iraci', 'prairaci': 'Pra. Iraci', 'pastoraraci': 'Pra. Iraci', 'pastorairaci': 'Pra. Iraci',
            'talita': 'Talita', 'wesley': 'Wesley'}


def separar_cantores(texto):
    """'Talita e Débora' -> ['Talita', 'Débora'] com os nomes como estão na planilha (cantores desconhecidos ficam de fora)."""
    partes = re.split(r'\s*(?:,|\+|/|&|\be\b)\s*', str(texto or ''))
    out = []
    for p in partes:
        c = CANTORES.get(chave(p))
        if c and c not in out:
            out.append(c)
    return out


class Aba:
    """Edita uma aba do .xlsx direto no XML, preservando o resto do arquivo."""

    def __init__(self, tmp, arquivo, strings):
        self.p = os.path.join(tmp, 'xl', 'worksheets', arquivo)
        self.s = open(self.p, encoding='utf8').read()
        self.strings = strings
        self.attrs = {int(r): a for r, a, _ in re.findall(r'<row r="(\d+)"([^>]*)>(.*?)</row>', self.s, re.S)}
        self.linhas = {int(r): b for r, _, b in re.findall(r'<row r="(\d+)"([^>]*)>(.*?)</row>', self.s, re.S)}

    def celulas(self, r):
        return {m.group(1): m.group(0) for m in re.finditer(r'<c r="([A-Z]+)' + str(r) + r'"(?:[^>]*?/>|[^>]*?>.*?</c>)', self.linhas.get(r, ''), re.S)}

    def valor(self, xml):
        m = re.search(r't="s"[^>]*>.*?<v>(\d+)</v>', xml, re.S)
        if m:
            return self.strings[int(m.group(1))]
        m = re.search(r'<is>.*?<t[^>]*>(.*?)</t>', xml, re.S)
        if m:
            return html.unescape(m.group(1))
        m = re.search(r'<v>([^<]*)</v>', xml)
        return m.group(1) if m else ''

    def estilo(self, r, col):
        m = re.search(r' s="(\d+)"', self.celulas(r).get(col, ''))
        return m.group(1) if m else None

    def texto(self, r, col, t, s=None):
        s = s or self.estilo(r, col)
        st = f' s="{s}"' if s else ''
        self.definir(r, col, f'<c r="{col}{r}"{st} t="inlineStr"><is><t>{esc(t)}</t></is></c>')

    def definir(self, r, col, xml):
        corpo = self.linhas.get(r)
        if corpo is None:
            self.linhas[r] = xml
            return
        cs = self.celulas(r)
        if col in cs:
            self.linhas[r] = corpo.replace(cs[col], xml, 1)
        else:
            todas = list(cs.items()) + [(col, xml)]
            self.linhas[r] = ''.join(x for _, x in sorted(todas, key=lambda t: (len(t[0]), t[0])))

    def salvar(self):
        corpo = ''.join(f'<row r="{r}"{self.attrs.get(r, "")}>{self.linhas[r]}</row>' for r in sorted(self.linhas))
        self.s = re.sub(r'<sheetData>.*?</sheetData>|<sheetData/>', lambda m: '<sheetData>' + corpo + '</sheetData>', self.s, count=1, flags=re.S)
        maior = max(self.linhas)
        self.s = re.sub(r'<dimension ref="([A-Z]+)\d+:([A-Z]+)\d+"/>', lambda m: f'<dimension ref="{m.group(1)}1:{m.group(2)}{maior}"/>', self.s, count=1)
        open(self.p, 'w', encoding='utf8').write(self.s)


def letras(a, b):
    out, c = [], a
    while True:
        out.append(c)
        if c == b:
            return out
        c = chr(ord(c) + 1)


def _ordem_alfa(t):
    import unicodedata
    return unicodedata.normalize('NFD', str(t)).encode('ascii', 'ignore').decode().lower().strip()


def inserir_linha_ordenada(tmp, aba, col_m, cols, tabela_xml, musica):
    """Insere uma linha nova (vazia nos cantores) na aba de tons, em ordem alfabética pelo nome da música,
    descendo as linhas de baixo e aumentando a tabela. Devolve o número da linha criada.
    (Regra do Neto: toda música do repertório base, inclusive a música teste, aparece na aba Tons.)"""
    usadas = sorted(r for r in aba.linhas if r > 1 and aba.valor(aba.celulas(r).get(col_m, '')))
    alvo = next((r for r in usadas if _ordem_alfa(aba.valor(aba.celulas(r).get(col_m, ''))) > _ordem_alfa(musica)), (usadas[-1] + 1) if usadas else 2)
    modelo = alvo if alvo in aba.linhas else (usadas[-1] if usadas else 2)
    attrs_modelo = aba.attrs.get(modelo, '')
    estilos = {c: aba.estilo(modelo, c) for c in [col_m] + cols}
    novas, attrs = {}, {}
    for r in sorted(aba.linhas, reverse=True):
        n = r + 1 if r >= alvo else r
        novas[n] = re.sub(r'(<c r="[A-Z]+)%d"' % r, lambda m: f'{m.group(1)}{n}"', aba.linhas[r]) if n != r else aba.linhas[r]
        attrs[n] = aba.attrs.get(r, '')
    aba.linhas, aba.attrs = novas, attrs
    aba.attrs[alvo] = attrs_modelo
    aba.linhas[alvo] = ''
    aba.texto(alvo, col_m, musica, estilos[col_m])
    for c in cols:
        st = estilos[c]
        aba.definir(alvo, c, f'<c r="{c}{alvo}"' + (f' s="{st}"' if st else '') + '/>')
    tp = os.path.join(tmp, 'xl', 'tables', tabela_xml)
    t = open(tp, encoding='utf8').read()
    t = re.sub(r'ref="([A-Z]+\d+):([A-Z]+)(\d+)"', lambda m: f'ref="{m.group(1)}:{m.group(2)}{int(m.group(3)) + 1 if int(m.group(3)) >= alvo - 1 else m.group(3)}"', t)
    open(tp, 'w', encoding='utf8').write(t)
    return alvo


def editar_tons(tmp, strings, mudancas, base):
    """mudancas: lista de {musica, cantor, tom}. Atualiza a aba Tons (músicas do repertório base) ou a aba Outras (as demais)."""
    feitos, divergentes = [], []
    tratadas = set()
    abas = {
        'Tons': (Aba(tmp, 'sheet2.xml', strings), 'A', letras('B', 'L'), 'table2.xml'),
        'Outras': (Aba(tmp, 'sheet4.xml', strings), 'B', letras('C', 'M'), 'table4.xml'),
    }
    for nome_aba, (aba, col_m, cols, tabela) in abas.items():
        cab = {CANTORES.get(chave(aba.valor(aba.celulas(1).get(c, ''))), aba.valor(aba.celulas(1).get(c, ''))): c for c in cols}
        tp = os.path.join(tmp, 'xl', 'tables', tabela)
        tab = open(tp, encoding='utf8').read()
        m = re.search(r'ref="([A-Z]+)1:([A-Z]+)(\d+)"', tab)
        fim = int(m.group(3))
        linha_de = {}
        for r in range(2, fim + 1):
            v = aba.valor(aba.celulas(r).get(col_m, ''))
            if v:
                linha_de[chave(v)] = r
        mexeu = False
        for mu in mudancas:
            noBase = mu['musica'] in base
            ident = (chave(mu['musica']), mu['cantor'])
            if ident in tratadas:
                continue
            if (nome_aba == 'Tons') != noBase and chave(mu['musica']) not in linha_de:
                continue
            col = cab.get(mu['cantor'])
            if not col:
                continue
            tratadas.add(ident)
            r = linha_de.get(chave(mu['musica']))
            if r is None:
                open(tp, 'w', encoding='utf8').write(tab)
                r = inserir_linha_ordenada(tmp, aba, col_m, cols, tabela, mu['musica'])
                tab = open(tp, encoding='utf8').read()
                fim += 1
                linha_de = {chave(aba.valor(aba.celulas(x).get(col_m, ''))): x for x in aba.linhas if x > 1 and aba.valor(aba.celulas(x).get(col_m, ''))}
                mexeu = True
            antes = aba.valor(aba.celulas(r).get(col, ''))
            if antes.strip() == str(mu['tom']).strip():
                continue
            if antes.strip() and not mu.get('forcar'):
                divergentes.append({'aba': nome_aba, 'musica': mu['musica'], 'cantor': mu['cantor'], 'planilha': antes, 'grupo': mu['tom']})
                continue
            aba.texto(r, col, mu['tom'], aba.estilo(r, col) or aba.estilo(2, col))
            feitos.append({'aba': nome_aba, 'musica': mu['musica'], 'cantor': mu['cantor'], 'antes': antes or '—', 'depois': mu['tom']})
            mexeu = True
        if mexeu:
            open(tp, 'w', encoding='utf8').write(tab)
            aba.salvar()
    return feitos, divergentes


def editar_xlsx(caminho, cultos_novos, mudancas_tons=None, base=frozenset()):
    """Acrescenta os cultos na aba Registros (sheet3.xml) e as músicas novas ao ranking (Tabela8)."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        z.extractall(tmp)
    sp = os.path.join(tmp, 'xl', 'worksheets', 'sheet3.xml')
    s = open(sp, encoding='utf8').read()
    ss = open(os.path.join(tmp, 'xl', 'sharedStrings.xml'), encoding='utf8').read()
    strings = [html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))) for si in re.findall(r'<si>(.*?)</si>', ss, re.S)]

    def valor(celula_xml):
        m = re.search(r't="s"[^>]*>.*?<v>(\d+)</v>', celula_xml, re.S)
        if m:
            return strings[int(m.group(1))]
        m = re.search(r'<is>.*?<t[^>]*>(.*?)</t>', celula_xml, re.S)
        if m:
            return html.unescape(m.group(1))
        m = re.search(r'<v>([^<]*)</v>', celula_xml)
        return m.group(1) if m else ''

    linhas = {int(r): b for r, b in re.findall(r'<row r="(\d+)"[^>]*>(.*?)</row>', s, re.S)}

    def celulas(r):
        return {m.group(1): m.group(0) for m in re.finditer(r'<c r="([A-Z]+)' + str(r) + r'"(?:[^>]*?/>|[^>]*?>.*?</c>)', linhas.get(r, ''), re.S)}

    ultima = max(r for r in linhas if r >= 3 and valor(celulas(r).get('C', '')))

    def definir(r, col, xml_celula):
        corpo = linhas.get(r)
        if corpo is None:
            linhas[r] = xml_celula
            return
        cs = celulas(r)
        if col in cs:
            linhas[r] = corpo.replace(cs[col], xml_celula, 1)
        else:
            todas = list(cs.items()) + [(col, xml_celula)]
            ordem = lambda c: (len(c), c)
            linhas[r] = ''.join(x for _, x in sorted(todas, key=lambda t: ordem(t[0])))

    r = ultima
    for culto in cultos_novos:
        n = len(culto['musicas'])
        for i, musica in enumerate(culto['musicas']):
            r += 1
            primeiro, ultimo_do_culto = i == 0, i == n - 1
            sb, sc, sd = ('6', '7', '104') if primeiro else (('10', '11', '106') if ultimo_do_culto else ('8', '9', '105'))
            definir(r, 'B', f'<c r="B{r}" s="{sb}"><v>{serial_excel(culto["data"])}</v></c>')
            definir(r, 'C', f'<c r="C{r}" s="{sc}" t="inlineStr"><is><t>{esc(musica)}</t></is></c>')
            if primeiro and culto.get('tipo'):
                definir(r, 'D', f'<c r="D{r}" s="{sd}" t="inlineStr"><is><t>{esc(culto["tipo"])}</t></is></c>')
            else:
                definir(r, 'D', f'<c r="D{r}" s="{sd}"/>')
            if primeiro and culto.get('evento'):
                definir(r, 'E', f'<c r="E{r}" s="98" t="inlineStr"><is><t>{esc(culto["evento"])}</t></is></c>')
    ultima_nova = r

    # ranking (Tabela8 em J4:K...): conta tudo de novo e acrescenta músicas que ainda não estão nele
    todas = [valor(celulas(x).get('C', '')) for x in range(3, ultima_nova + 1)]
    todas = [t for t in todas if t]
    contagem = {}
    for t in todas:
        contagem[chave(t)] = contagem.get(chave(t), 0) + 1
    tp = os.path.join(tmp, 'xl', 'tables', 'table3.xml')
    tab = open(tp, encoding='utf8').read()
    fim_tab = int(re.search(r'ref="J4:K(\d+)"', tab).group(1))
    no_ranking = {chave(valor(celulas(x).get('J', ''))) for x in range(5, fim_tab + 1)}
    for x in range(5, fim_tab + 1):
        nome = valor(celulas(x).get('J', ''))
        k = celulas(x).get('K')
        if nome and k:
            definir(x, 'K', re.sub(r'<v>[^<]*</v>', f'<v>{contagem.get(chave(nome), 0)}</v>', k))
    acrescentadas = []
    for t in dict.fromkeys(todas):
        if chave(t) not in no_ranking:
            fim_tab += 1
            no_ranking.add(chave(t))
            acrescentadas.append(t)
            definir(fim_tab, 'I', f'<c r="I{fim_tab}" s="2"><v>{fim_tab - 4}</v></c>')
            definir(fim_tab, 'J', f'<c r="J{fim_tab}" s="20" t="inlineStr"><is><t>{esc(t)}</t></is></c>')
            definir(fim_tab, 'K', f'<c r="K{fim_tab}" s="20"><f>COUNTIF($C$3:$C$582,J{fim_tab})</f><v>{contagem.get(chave(t), 0)}</v></c>')
    # reordena o ranking: mais tocada primeiro; empates em ordem alfabética; posições em sequência (1, 2, 3...)
    nomes_rank = [valor(celulas(x).get('J', '')) for x in range(5, fim_tab + 1)]
    nomes_rank = [n for n in nomes_rank if n]
    alfa = lambda n: unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    nomes_rank.sort(key=lambda n: (-contagem.get(chave(n), 0), alfa(n)))
    for i, nome in enumerate(nomes_rank):
        x = 5 + i
        si = re.search(r' s="(\d+)"', celulas(x).get('J', '')) or None
        sj = si.group(1) if si else '20'
        definir(x, 'I', re.sub(r'<v>[^<]*</v>', f'<v>{i + 1}</v>', celulas(x)['I']) if 'I' in celulas(x) and '<v>' in celulas(x)['I'] else f'<c r="I{x}" s="2"><v>{i + 1}</v></c>')
        definir(x, 'J', f'<c r="J{x}" s="{sj}" t="inlineStr"><is><t>{esc(nome)}</t></is></c>')
        k = celulas(x).get('K', '')
        if '<f' in k and '<v>' in k:
            definir(x, 'K', re.sub(r'<v>[^<]*</v>', f'<v>{contagem.get(chave(nome), 0)}</v>', k))
        else:
            sk = (re.search(r' s="(\d+)"', k) or re.search(r'(20)', '20')).group(1)
            definir(x, 'K', f'<c r="K{x}" s="{sk}"><f>COUNTIF($C$3:$C$582,J{x})</f><v>{contagem.get(chave(nome), 0)}</v></c>')
    tab = re.sub(r'ref="J4:K\d+"', f'ref="J4:K{fim_tab}"', tab)
    tab = re.sub(r'ref="J5:K\d+"', f'ref="J5:K{fim_tab}"', tab)
    tab = re.sub(r'ref="K4:K\d+"', f'ref="K4:K{fim_tab}"', tab)
    open(tp, 'w', encoding='utf8').write(tab)

    # monta o XML da aba de novo, linha por linha, em ordem
    corpo_linhas = ''.join(f'<row r="{r}">{linhas[r]}</row>' for r in sorted(linhas))
    s = re.sub(r'<sheetData>.*?</sheetData>|<sheetData/>', '<sheetData>' + corpo_linhas + '</sheetData>', s, count=1, flags=re.S)
    maior = max(sorted(linhas))
    s = re.sub(r'<dimension ref="([A-Z]+)\d+:([A-Z]+)\d+"/>', lambda m: f'<dimension ref="{m.group(1)}1:{m.group(2)}{maior}"/>', s, count=1)
    open(sp, 'w', encoding='utf8').write(s)

    tons_feitos, tons_div = editar_tons(tmp, strings, mudancas_tons or [], base) if mudancas_tons else ([], [])

    # pede ao Excel para recalcular ao abrir
    wp = os.path.join(tmp, 'xl', 'workbook.xml')
    w = open(wp, encoding='utf8').read()
    if '<calcPr' in w and 'fullCalcOnLoad' not in w:
        w = w.replace('<calcPr', '<calcPr fullCalcOnLoad="1"', 1)
    open(wp, 'w', encoding='utf8').write(w)
    calc = os.path.join(tmp, 'xl', 'calcChain.xml')

    saida = caminho + '.novo'
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in nomes:
            if n.endswith('/'):
                continue
            z.write(os.path.join(tmp, n), n)
    os.replace(saida, caminho)
    shutil.rmtree(tmp)
    return {'linhas_registros_ate': ultima_nova, 'novas_no_ranking': acrescentadas, 'tons_alterados': tons_feitos, 'tons_divergentes': tons_div}


def garantir_em_tons(tmp, musica):
    """Regra do Neto: a música teste (e toda música do repertório base) aparece na aba Tons, mesmo sem tons ainda.
    Se ela não tiver linha na aba Tons, cria uma em ordem alfabética. Devolve True se criou."""
    ss = open(os.path.join(tmp, 'xl', 'sharedStrings.xml'), encoding='utf8').read()
    strings = [html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))) for si in re.findall(r'<si>(.*?)</si>', ss, re.S)]
    aba = Aba(tmp, 'sheet2.xml', strings)
    if any(chave(aba.valor(aba.celulas(r).get('A', ''))) == chave(musica) for r in aba.linhas if r > 1):
        return False
    inserir_linha_ordenada(tmp, aba, 'A', letras('B', 'L'), 'table2.xml', musica)
    aba.salvar()
    return True


def incluir_teste(caminho, teste):
    """Acrescenta a música teste do mês na aba Repertório Base (categoria Teste), com o botão de link igual aos outros."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        z.extractall(tmp)
    sp = os.path.join(tmp, 'xl', 'worksheets', 'sheet1.xml')
    s = open(sp, encoding='utf8').read()
    ultima = max(int(r) for r in re.findall(r'<row r="(\d+)"', s))
    nova = ultima + 1
    m = re.search(r'<c r="A%d"[^>]*><v>(\d+)</v>' % ultima, s)
    num = int(m.group(1)) + 1 if m else nova - 1
    row = (f'<row r="{nova}" spans="1:9" ht="15.75" x14ac:dyDescent="0.25">'
           f'<c r="A{nova}" s="60"><v>{num}</v></c>'
           f'<c r="B{nova}" s="60" t="inlineStr"><is><t>{esc(teste["musica"])}</t></is></c>'
           f'<c r="C{nova}" s="60" t="inlineStr"><is><t>{esc(teste.get("artista", ""))}</t></is></c>'
           + (f'<c r="D{nova}" s="60" t="inlineStr"><is><t>{esc(teste["tom"])}</t></is></c>' if teste.get('tom') else f'<c r="D{nova}" s="60"/>')
           + (f'<c r="E{nova}" s="60"><v>{teste["bpm"]}</v></c>' if str(teste.get('bpm') or '').replace('.', '').isdigit() else f'<c r="E{nova}" s="60"/>')
           + (f'<c r="F{nova}" s="93" t="inlineStr"><is><t>{esc(teste["compasso"])}</t></is></c>' if teste.get('compasso') else f'<c r="F{nova}" s="93"/>')
           + f'<c r="G{nova}" s="60"><v>0</v></c>'
           f'<c r="H{nova}" s="60" t="inlineStr"><is><t>Teste</t></is></c><c r="I{nova}" s="77"/></row>')
    i = s.index('</row>', s.index(f'<row r="{ultima}"')) + len('</row>')
    s = s[:i] + row + s[i:]
    s = re.sub(r'<dimension ref="A1:([A-Z]+)\d+"/>', lambda x: f'<dimension ref="A1:{x.group(1)}{nova}"/>', s, count=1)
    open(sp, 'w', encoding='utf8').write(s)
    for f in os.listdir(os.path.join(tmp, 'xl', 'tables')):
        tp = os.path.join(tmp, 'xl', 'tables', f)
        t = open(tp, encoding='utf8').read()
        if 'Tabela3' in t:
            t = re.sub(r'ref="B1:I\d+"', f'ref="B1:I{nova}"', t)
            open(tp, 'w', encoding='utf8').write(t)
    link = teste.get('link', '')
    if link.startswith('https://'):
        rp = os.path.join(tmp, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
        r = open(rp, encoding='utf8').read()
        nid = max(int(x) for x in re.findall(r'Id="rId(\d+)"', r)) + 1
        r = r.replace('</Relationships>', f'<Relationship Id="rId{nid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{esc(link)}" TargetMode="External"/></Relationships>')
        open(rp, 'w', encoding='utf8').write(r)
        dp = os.path.join(tmp, 'xl', 'drawings', 'drawing1.xml')
        d = open(dp, encoding='utf8').read()
        anchors = re.findall(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', d, re.S)
        lin = lambda a: int(re.search(r'<xdr:from>.*?<xdr:row>(\d+)</xdr:row>', a, re.S).group(1))
        base_row = max(lin(a) for a in anchors)
        modelo = [a for a in anchors if lin(a) == base_row]
        mx = max(int(x) for x in re.findall(r'cNvPr id="(\d+)"', d))
        novos = ''
        for k, a in enumerate(modelo):
            b = a.replace(f'<xdr:row>{base_row}</xdr:row>', f'<xdr:row>{nova - 1}</xdr:row>')
            b = re.sub(r'<a:extLst>.*?</a:extLst>', '', b, count=1, flags=re.S)
            b = re.sub(r'cNvPr id="\d+" name="([^"]*?) \d+"', lambda x: f'cNvPr id="{mx + 1 + k}" name="{x.group(1)} {mx + k}"', b)
            b = re.sub(r'r:id="rId\d+"', f'r:id="rId{nid}"', b)
            novos += b
        d = d.replace('</xdr:wsDr>', novos + '</xdr:wsDr>')
        open(dp, 'w', encoding='utf8').write(d)
    garantir_em_tons(tmp, teste['musica'])
    saida = caminho + '.novo'
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in nomes:
            if not n.endswith('/'):
                z.write(os.path.join(tmp, n), n)
    os.replace(saida, caminho)
    shutil.rmtree(tmp)
    return {'linha': nova}


FIM_DA_LISTA = ('Stand By',)  # Stand By = agora não entrou, mas deve ser testada de novo em breve; só o Neto põe música nela. Fica sempre no fim da aba Repertório Base (regra do Neto)


def mover_para_fim(caminho, categorias=FIM_DA_LISTA, definir=None):
    """Põe no fim da aba Repertório Base as linhas cuja categoria (coluna H) está em `categorias`,
    renumerando a coluna A e levando junto os botões de link (desenhos ancorados na linha).
    `definir` = {nome da música: categoria}: troca a categoria dessas músicas antes de mover
    (coluna G recebe 4 para Stand By, a ordem usada no fim da lista)."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        z.extractall(tmp)
    sp = os.path.join(tmp, 'xl', 'worksheets', 'sheet1.xml')
    s = open(sp, encoding='utf8').read()
    ss = os.path.join(tmp, 'xl', 'sharedStrings.xml')
    si = re.findall(r'<si>(.*?)</si>', open(ss, encoding='utf8').read(), re.S) if os.path.exists(ss) else []
    def val(c):
        if not c or '<v>' not in c and '<t' not in c:
            return ''
        if 't="s"' in c.split('>')[0]:
            return html.unescape(re.sub('<[^>]+>', '', si[int(re.search(r'<v>(\d+)</v>', c).group(1))]))
        t = re.search(r'<t[^>]*>(.*?)</t>', c, re.S)
        return html.unescape(t.group(1)) if t else re.search(r'<v>(.*?)</v>', c).group(1)
    linhas = {int(m.group(1)): m.group(0) for m in re.finditer(r'<row r="(\d+)"[^>]*>.*?</row>', s, re.S)}
    def cel(xml, col, r):
        m = re.search(r'<c r="%s%d"[^>]*?(?:/>|>.*?</c>)' % (col, r), xml, re.S)
        return m.group(0) if m else ''
    orig = dict(linhas)
    definir = {chave(k): v for k, v in (definir or {}).items()}
    for r, xml in list(linhas.items()):
        if r == 1:
            continue
        nova_cat = definir.get(chave(val(cel(xml, 'B', r))))
        if nova_cat:
            h = cel(xml, 'H', r)
            st = re.search(r's="(\d+)"', h)
            novo_h = f'<c r="H{r}"{" s=" + chr(34) + st.group(1) + chr(34) if st else ""} t="inlineStr"><is><t>{esc(nova_cat)}</t></is></c>'
            xml = xml.replace(h, novo_h) if h else xml
            g = cel(xml, 'G', r)
            if g and nova_cat in categorias:
                stg = re.search(r's="(\d+)"', g)
                xml = xml.replace(g, f'<c r="G{r}"{" s=" + chr(34) + stg.group(1) + chr(34) if stg else ""}><v>4</v></c>')
            linhas[r] = xml
    dados = sorted(r for r in linhas if r > 1)
    fim = [r for r in dados if val(cel(linhas[r], 'H', r)).strip() in categorias]
    ordem = [r for r in dados if r not in fim] + fim
    mapa = {velho: dados[i] for i, velho in enumerate(ordem)}  # linha antiga -> linha nova
    if all(k == v for k, v in mapa.items()) and not definir:
        shutil.rmtree(tmp)
        return {'movidas': []}
    base_num = 1
    novas = []
    for i, velho in enumerate(ordem):
        novo = mapa[velho]
        xml = linhas[velho]
        xml = re.sub(r'<row r="%d"' % velho, f'<row r="{novo}"', xml, count=1)
        xml = re.sub(r'(<c r="[A-Z]+)%d"' % velho, lambda m: f'{m.group(1)}{novo}"', xml)
        xml = re.sub(r'(<c r="A%d"[^>]*><v>)\d+(</v>)' % novo, lambda m: f'{m.group(1)}{base_num + i}{m.group(2)}', xml)
        novas.append(xml)
    ini = s.index(orig[dados[0]])
    fim_txt = s.index(orig[dados[-1]]) + len(orig[dados[-1]])
    s = s[:ini] + ''.join(novas) + s[fim_txt:]
    open(sp, 'w', encoding='utf8').write(s)
    dp = os.path.join(tmp, 'xl', 'drawings', 'drawing1.xml')
    if os.path.exists(dp):
        d = open(dp, encoding='utf8').read()
        def troca(m):
            a = m.group(0)
            def r0(x):
                velho = int(x.group(2)) + 1
                return f'{x.group(1)}{mapa.get(velho, velho) - 1}{x.group(3)}'
            return re.sub(r'(<xdr:(?:from|to)>.*?<xdr:row>)(\d+)(</xdr:row>)', r0, a, flags=re.S)
        d = re.sub(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', troca, d, flags=re.S)
        open(dp, 'w', encoding='utf8').write(d)
    saida = caminho + '.novo'
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in nomes:
            if not n.endswith('/'):
                z.write(os.path.join(tmp, n), n)
    os.replace(saida, caminho)
    shutil.rmtree(tmp)
    return {'movidas': [val(cel(linhas[r], 'B', r)) for r in fim]}


def marcar_pendentes(caminho, nomes):
    """Muda a categoria das músicas indicadas de Teste para Pendente na aba Repertório Base (mês de teste já acabou, sem definição)."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        lista = z.namelist()
        z.extractall(tmp)
    ss = open(os.path.join(tmp, 'xl', 'sharedStrings.xml'), encoding='utf8').read()
    strings = [html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))) for si in re.findall(r'<si>(.*?)</si>', ss, re.S)]
    aba = Aba(tmp, 'sheet1.xml', strings)
    alvo = {chave(n) for n in nomes}
    feitos = []
    for r in sorted(aba.linhas):
        if r < 2:
            continue
        nome = aba.valor(aba.celulas(r).get('B', ''))
        if chave(nome) in alvo and aba.valor(aba.celulas(r).get('H', '')).strip() == 'Teste':
            aba.texto(r, 'H', 'Pendente')
            g = aba.celulas(r).get('G')
            if g:
                aba.definir(r, 'G', re.sub(r'<v>[^<]*</v>', '<v>0.5</v>', g) if '<v>' in g else g.replace('/>', '><v>0.5</v></c>'))
            feitos.append(nome)
    if feitos:
        aba.salvar()
        saida = caminho + '.novo'
        with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
            for n in lista:
                if not n.endswith('/'):
                    z.write(os.path.join(tmp, n), n)
        os.replace(saida, caminho)
    shutil.rmtree(tmp)
    return feitos


def gerar_linhas(repo):
    """dados/proximo_linhas.json para o dashboard: uma linha por pessoa da equipe, por música e por pessoa da escala do mês."""
    d = os.path.join(repo, 'dados')
    p = carregar(os.path.join(d, 'proximo.json'), None) or {}
    esc = carregar(os.path.join(d, 'escala.json'), None) or {}
    vazio = {'funcao': '', 'nomes': '', 'titulo': '', 'cantor': '', 'tom': '', 'tom_origem': '', 'link': '', 'letra': '',
             'esc_mes': '', 'esc_data': '', 'esc_culto': '', 'esc_evento': '', 'esc_extra': ''}
    base = dict(vazio, data=p.get('data', ''), culto=p.get('culto', ''), evento=p.get('evento', ''), atualizado=p.get('atualizado', ''))
    mus = lambda m: {'titulo': m.get('titulo', ''), 'cantor': m.get('cantor', ''), 'tom': m.get('tom', ''),
                     'tom_origem': m.get('tom_origem', ''), 'link': m.get('link', ''), 'letra': m.get('letra', '')}
    linhas = [dict(base, parte='equipe', ordem=i + 1, funcao=e.get('funcao', ''), nomes=e.get('nomes', ''))
              for i, e in enumerate(p.get('equipe', []))]
    # músicas numeradas primeiro; as de momento especial (ex.: Ceia) por último, com o momento no título
    normais = [m for m in p.get('musicas', []) if not m.get('momento')]
    especiais = [m for m in p.get('musicas', []) if m.get('momento')]
    rot = lambda m: ('🍷 ' if m['momento'].lower() == 'ceia' else '⭐ ') + m['momento'] + ': ' + m['titulo']
    linhas += [dict(base, parte='musica', ordem=i + 1, **mus(m)) for i, m in enumerate(normais)]
    if especiais:  # a música da Ceia é a nº 5: as vagas 3 e 4 ainda sem música aparecem como "A definir"
        linhas += [dict(base, parte='musica', ordem=i + 1, titulo='❓ A definir') for i in range(len(normais), 4)]
        n0 = max(4, len(normais))
        linhas += [dict(base, parte='musica', ordem=n0 + i + 1, **dict(mus(m), titulo=rot(m))) for i, m in enumerate(especiais)]
    # escala do mês (botão "Ver escala de <mês>")
    k = 0
    for c in esc.get('cultos', []):
        cab = dict(base, parte='escala', esc_mes=esc.get('mes', ''), esc_data=c.get('data', ''), esc_culto=c.get('culto', ''),
                   esc_evento=c.get('evento', ''), esc_extra=c.get('extra', ''))
        for e in c.get('equipe', []) or [{}]:
            k += 1
            linhas.append(dict(cab, ordem=1000 + k, funcao=e.get('funcao', ''), nomes=e.get('nomes', '')))
    if not linhas:
        linhas = [dict(base, parte='info', ordem=0)]
    salvar(os.path.join(d, 'proximo_linhas.json'), linhas)


def gerar_html(repo):
    gerar_linhas(repo)
    d = os.path.join(repo, 'dados')
    t = open(os.path.join(repo, 'automacao', 'template.html'), encoding='utf8').read()
    rep = carregar(os.path.join(d, 'repertorio.json'), [])
    tons = carregar(os.path.join(d, 'tons.json'), [])
    reg = [{k: x.get(k, '') for k in ('data', 'musica', 'tipo', 'evento')} for x in carregar(os.path.join(d, 'registros.json'), [])]
    prox = carregar(os.path.join(d, 'proximo.json'), None)
    esc = carregar(os.path.join(d, 'escala.json'), None)
    j = lambda o: json.dumps(o, ensure_ascii=False).replace('</', '<\\/')
    hoje = datetime.date.today().strftime('%d/%m/%Y')
    logo = open(os.path.join(repo, 'automacao', 'logo.b64')).read().strip()
    t = t.replace('__LOGO__', logo).replace('__REP__', j(rep)).replace('__TONS__', j(tons)).replace('__REG__', j(reg)).replace('__PROX__', j(prox)).replace('__ESC__', j(esc)).replace('__ATUALIZADO__', hoje)
    open(os.path.join(repo, 'index.html'), 'w', encoding='utf8').write(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--novos', required=True)
    ap.add_argument('--xlsx')
    ap.add_argument('--ajustes', help='correções de tom: lista de {musica, cantor, tom}')
    ap.add_argument('--teste', help='música teste do mês para incluir no repertório base: {musica, artista, link, aliases: [...]}')
    a = ap.parse_args()
    d = os.path.join(a.repo, 'dados')
    rep = carregar(os.path.join(d, 'repertorio.json'), [])
    reg = carregar(os.path.join(d, 'registros.json'), [])
    aliases = carregar(os.path.join(d, 'aliases.json'), {})
    canon = {chave(x['musica']): x['musica'] for x in rep}
    for x in reg:
        canon.setdefault(chave(x['musica']), x['musica'])
    alias_k = {chave(k): v for k, v in aliases.items()}
    base = {x['musica'] for x in rep}
    teste_set = {x['musica'] for x in rep if x.get('categoria') in ('Teste', 'Pendente') + FIM_DA_LISTA}
    datas = {x['data'] for x in reg}

    # músicas teste de meses que já acabaram e ainda sem definição viram "Pendente"
    mes_atual = datetime.date.today().strftime('%Y-%m')
    meses = {chave(x['musica']): x.get('mes', '') for x in carregar(os.path.join(d, 'testes.json'), [])}
    def venceu(nome):
        m = meses.get(chave(nome), '') or ''
        return not re.fullmatch(r'\d{4}-\d{2}', m) or m < mes_atual
    vencidas = [x['musica'] for x in rep if x.get('categoria') == 'Teste' and venceu(x['musica'])]
    pendentes_novas = []
    if vencidas:
        for x in rep:
            if x['musica'] in vencidas:
                x['categoria'] = 'Pendente'
        salvar(os.path.join(d, 'repertorio.json'), rep)
        pendentes_novas = vencidas
        if a.xlsx:
            marcar_pendentes(a.xlsx, vencidas)

    teste_incluido = None
    if a.teste:
        t = json.load(open(a.teste, encoding='utf8'))
        t['musica'] = corrige_deus(t['musica'].strip())
        ja = any(chave(x['musica']) == chave(t['musica']) for x in rep) or any(chave(al) in canon for al in t.get('aliases', []) if canon.get(chave(al)) in base)
        if not ja:
            rep.append({'musica': t['musica'], 'artista': t.get('artista', ''), 'tom': t.get('tom', ''), 'bpm': t.get('bpm', ''), 'compasso': t.get('compasso', ''), 'categoria': 'Teste', 'link': t.get('link', '')})
            rep.sort(key=lambda x: x.get('categoria') in FIM_DA_LISTA)  # Stand By no fim
            salvar(os.path.join(d, 'repertorio.json'), rep)
            for al in t.get('aliases', []):
                aliases[al] = t['musica']
            salvar(os.path.join(d, 'aliases.json'), aliases)
            alias_k.update({chave(al): t['musica'] for al in t.get('aliases', [])})
            canon[chave(t['musica'])] = t['musica']
            base.add(t['musica'])
            for x in reg:
                if chave(x['musica']) in {chave(al) for al in t.get('aliases', [])}:
                    x['musica'] = t['musica']; x['no_repertorio'] = 'Não'
            teste_incluido = t['musica']
            testes = carregar(os.path.join(d, 'testes.json'), [])
            testes.append({'musica': t['musica'], 'mes': datetime.date.today().strftime('%Y-%m')})
            salvar(os.path.join(d, 'testes.json'), testes)
            if a.xlsx:
                incluir_teste(a.xlsx, t)
                mover_para_fim(a.xlsx)  # Stand By continua no fim, abaixo da música teste

    base_fixo = base - teste_set - ({teste_incluido} if teste_incluido else set())  # música em teste ainda conta como fora do repertório base
    novos = json.load(open(a.novos, encoding='utf8'))
    adicionados, ignorados, padronizados, fora = [], [], [], set()
    cultos_ok = []
    mudancas_tons, cantores_desconhecidos = [], []
    for c in sorted(novos, key=lambda c: c['data']):
        if c['data'] in datas:
            ignorados.append(c['data'])
            continue
        musicas = []
        for item in c['musicas']:
            m = (item.get('titulo') or item.get('musica') or '') if isinstance(item, dict) else item
            m = m.strip()
            n = corrige_deus(alias_k.get(chave(m)) or canon.get(chave(m)) or m)
            if n != m:
                padronizados.append({'grupo': m, 'planilha': n})
            musicas.append(n)
            if isinstance(item, dict) and str(item.get('tom') or '').strip():
                for cantor in separar_cantores(item.get('cantor')):
                    mudancas_tons.append({'musica': n, 'cantor': cantor, 'tom': str(item['tom']).strip()})
                if item.get('cantor') and not separar_cantores(item.get('cantor')):
                    cantores_desconhecidos.append(item.get('cantor'))
            if n not in base:
                fora.add(n)
            canon.setdefault(chave(n), n)
        c2 = {'data': c['data'], 'tipo': c.get('tipo', ''), 'evento': c.get('evento', ''), 'musicas': musicas}
        cultos_ok.append(c2)
        for m in musicas:
            reg.append({'data': c['data'], 'musica': m, 'tipo': c2['tipo'], 'evento': c2['evento'], 'no_repertorio': 'Sim' if m in base_fixo else 'Não'})
        datas.add(c['data'])
        adicionados.append(c2)
    salvar(os.path.join(d, 'registros.json'), reg)

    # correções manuais de tom (valem por cima do repertório do grupo)
    if a.ajustes:
        for aj in carregar(a.ajustes, []):
            n = corrige_deus(alias_k.get(chave(aj['musica'])) or canon.get(chave(aj['musica'])) or aj['musica'].strip())
            for cantor in separar_cantores(aj['cantor']):
                mudancas_tons = [x for x in mudancas_tons if not (x['musica'] == n and x['cantor'] == cantor)]
                mudancas_tons.append({'musica': n, 'cantor': cantor, 'tom': str(aj['tom']).strip(), 'forcar': True})

    # tons.json: do grupo só entra tom que ainda não existe para o cantor; divergência só é avisada
    tons_divergentes = []
    tons = carregar(os.path.join(d, 'tons.json'), [])
    tons_alterados = []
    for mu in mudancas_tons:
        atual = next((x for x in tons if chave(x['musica']) == chave(mu['musica']) and x['cantor'] == mu['cantor']), None)
        if atual and str(atual.get('tom', '')).strip() == mu['tom']:
            continue
        if atual and str(atual.get('tom', '')).strip() and not mu.get('forcar'):
            tons_divergentes.append({'musica': mu['musica'], 'cantor': mu['cantor'], 'planilha': atual['tom'], 'grupo': mu['tom']})
            continue
        tons_alterados.append({'musica': mu['musica'], 'cantor': mu['cantor'], 'antes': (atual or {}).get('tom') or '—', 'depois': mu['tom']})
        if atual:
            atual['tom'] = mu['tom']
        else:
            tons.append({'musica': mu['musica'], 'cantor': mu['cantor'], 'tom': mu['tom'], 'origem': 'Repertório base' if mu['musica'] in base else 'Fora do repertório'})
    salvar(os.path.join(d, 'tons.json'), tons)
    divergentes_k = {(chave(x['musica']), x['cantor']) for x in tons_divergentes}
    mudancas_tons = [x for x in mudancas_tons if (chave(x['musica']), x['cantor']) not in divergentes_k]

    planilha = editar_xlsx(a.xlsx, cultos_ok, mudancas_tons, base) if a.xlsx and (cultos_ok or mudancas_tons) else None
    gerar_html(a.repo)
    print(json.dumps({'adicionados': adicionados, 'ignorados_ja_registrados': ignorados, 'nomes_padronizados': padronizados,
                      'fora_do_repertorio_base': sorted(fora), 'tons_incluidos': tons_alterados, 'tons_divergentes_nao_alterados': tons_divergentes, 'musica_teste_incluida': teste_incluido, 'viraram_pendentes': pendentes_novas,
                      'cantores_nao_reconhecidos': cantores_desconhecidos, 'planilha': planilha}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
