#!/usr/bin/env python3
"""Aplica a decisão sobre uma música teste (ou Pendente) no repertório do Louvor CCT.

Uso:
  python3 -I automacao/decidir_teste.py --repo <clone> --xlsx <planilha.xlsx> --musica "<nome>" \
      --decisao entrou --categoria Contemplação
  python3 -I automacao/decidir_teste.py ... --decisao outras     # não entrou: sai do repertório base e vai para a aba Outras
  python3 -I automacao/decidir_teste.py ... --decisao standby    # testar de novo depois: categoria Stand By (fim da lista)

O que faz (regra do Neto):
  - entrou:  muda a categoria na aba Repertório Base (coluna H e a ordem na coluna G), põe a linha junto das
             outras da mesma categoria (em ordem alfabética), e se os tons dela estiverem na aba Outras, passa para a aba Tons.
  - outras:  tira a linha da aba Repertório Base (com o botão de link) e passa os tons da aba Tons para a aba Outras.
  - standby: categoria Stand By, no fim da aba Repertório Base.
  Atualiza também dados/repertorio.json e dados/tons.json e gera de novo o index.html.
  Imprime um resumo em JSON.
"""
import argparse, json, os, re, shutil, sys, tempfile, zipfile, html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atualizar import (Aba, chave, carregar, salvar, esc, editar_tons, letras, mover_para_fim, gerar_html,
                       CANTORES, FIM_DA_LISTA)

ORDEM = {'Teste': 0, 'Pendente': 0.5, 'Celebração': 1, 'Transição': 2, 'Contemplação': 3, 'Stand By': 4}


def _abrir(caminho):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        z.extractall(tmp)
    ss = open(os.path.join(tmp, 'xl', 'sharedStrings.xml'), encoding='utf8').read()
    strings = [html.unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))) for si in re.findall(r'<si>(.*?)</si>', ss, re.S)]
    return tmp, nomes, strings


def _fechar(caminho, tmp, nomes):
    saida = caminho + '.novo'
    with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in nomes:
            if not n.endswith('/'):
                z.write(os.path.join(tmp, n), n)
    os.replace(saida, caminho)
    shutil.rmtree(tmp)


def _renumerar_linha(xml, velho, novo):
    xml = re.sub(r'<row r="%d"' % velho, f'<row r="{novo}"', xml, count=1)
    return re.sub(r'(<c r="[A-Z]+)%d"' % velho, lambda m: f'{m.group(1)}{novo}"', xml)


def reorganizar_base(tmp, strings, nome, nova_cat=None, remover=False):
    """Aba Repertório Base (sheet1): troca a categoria da música e a põe no lugar certo, ou remove a linha.
    Leva junto os botões de link (desenhos ancorados na linha) e renumera a coluna A."""
    sp = os.path.join(tmp, 'xl', 'worksheets', 'sheet1.xml')
    s = open(sp, encoding='utf8').read()
    aba = Aba(tmp, 'sheet1.xml', strings)
    linhas = {int(m.group(1)): m.group(0) for m in re.finditer(r'<row r="(\d+)"[^>]*>.*?</row>', s, re.S)}
    dados = sorted(r for r in linhas if r > 1)
    nomes = {r: aba.valor(aba.celulas(r).get('B', '')) for r in dados}
    cats = {r: aba.valor(aba.celulas(r).get('H', '')).strip() for r in dados}
    alvo = [r for r in dados if chave(nomes[r]) == chave(nome)]
    if not alvo:
        raise SystemExit(f'Música não encontrada na aba Repertório Base: {nome}')
    alvo = alvo[0]
    cat_antes = cats[alvo]
    xml_alvo = linhas[alvo]
    if nova_cat:
        h = re.search(r'<c r="H%d"[^>]*?(?:/>|>.*?</c>)' % alvo, xml_alvo, re.S)
        st = re.search(r' s="(\d+)"', h.group(0)) if h else None
        novo_h = f'<c r="H{alvo}"' + (f' s="{st.group(1)}"' if st else '') + f' t="inlineStr"><is><t>{esc(nova_cat)}</t></is></c>'
        xml_alvo = xml_alvo.replace(h.group(0), novo_h) if h else xml_alvo.replace('</row>', novo_h + '</row>')
        g = re.search(r'<c r="G%d"[^>]*?(?:/>|>.*?</c>)' % alvo, xml_alvo, re.S)
        stg = re.search(r' s="(\d+)"', g.group(0)) if g else None
        num = ORDEM[nova_cat]
        novo_g = f'<c r="G{alvo}"' + (f' s="{stg.group(1)}"' if stg else '') + f'><v>{int(num) if num == int(num) else num}</v></c>'
        xml_alvo = xml_alvo.replace(g.group(0), novo_g) if g else xml_alvo
        linhas[alvo] = xml_alvo
        cats[alvo] = nova_cat
    outros = [r for r in dados if r != alvo]
    if remover:
        ordem = outros
    else:
        ordem = list(outros)
        if nova_cat in FIM_DA_LISTA:
            pos = len(ordem)
        else:
            mesma = [i for i, r in enumerate(ordem) if cats[r] == nova_cat]
            if mesma:
                pos = mesma[-1] + 1
                for i in mesma:
                    if chave(nomes[ordem[i]]) > chave(nome):
                        pos = i
                        break
            else:
                pos = next((i for i, r in enumerate(ordem) if ORDEM.get(cats[r], 9) > ORDEM[nova_cat]), len(ordem))
        ordem.insert(pos, alvo)
    mapa = {velho: dados[i] for i, velho in enumerate(ordem)}  # linha antiga -> linha nova
    novas = []
    for i, velho in enumerate(ordem):
        novo = mapa[velho]
        xml = _renumerar_linha(linhas[velho], velho, novo)
        xml = re.sub(r'(<c r="A%d"[^>]*><v>)\d+(</v>)' % novo, lambda m: f'{m.group(1)}{i + 1}{m.group(2)}', xml)
        novas.append(xml)
    ini = s.index(re.search(r'<row r="%d"[^>]*>' % dados[0], s).group(0))
    ult = re.search(r'<row r="%d"[^>]*>.*?</row>' % dados[-1], s, re.S)
    s = s[:ini] + ''.join(novas) + s[ult.end():]
    fim = dados[-1] - (1 if remover else 0)
    if remover:
        s = re.sub(r'<dimension ref="A1:([A-Z]+)\d+"/>', lambda m: f'<dimension ref="A1:{m.group(1)}{fim}"/>', s, count=1)
        s = re.sub(r'(sqref="[A-Z]+\d+:[A-Z]+)(\d+)"', lambda m: f'{m.group(1)}{int(m.group(2)) - 1 if int(m.group(2)) >= alvo else m.group(2)}"', s)
    open(sp, 'w', encoding='utf8').write(s)
    # botões de link
    dp = os.path.join(tmp, 'xl', 'drawings', 'drawing1.xml')
    if os.path.exists(dp):
        d = open(dp, encoding='utf8').read()
        def troca(m):
            a = m.group(0)
            de = int(re.search(r'<xdr:from>.*?<xdr:row>(\d+)</xdr:row>', a, re.S).group(1)) + 1
            if remover and de == alvo:
                return ''
            def r0(x):
                velho = int(x.group(2)) + 1
                return f'{x.group(1)}{mapa.get(velho, velho) - 1}{x.group(3)}'
            return re.sub(r'(<xdr:(?:from|to)>.*?<xdr:row>)(\d+)(</xdr:row>)', r0, a, flags=re.S)
        d = re.sub(r'<xdr:twoCellAnchor.*?</xdr:twoCellAnchor>', troca, d, flags=re.S)
        open(dp, 'w', encoding='utf8').write(d)
    if remover:
        for f in os.listdir(os.path.join(tmp, 'xl', 'tables')):
            tp = os.path.join(tmp, 'xl', 'tables', f)
            t = open(tp, encoding='utf8').read()
            if 'Tabela3' in t:
                t = re.sub(r'ref="([A-Z]+\d+):([A-Z]+)(\d+)"', lambda m: f'ref="{m.group(1)}:{m.group(2)}{int(m.group(3)) - 1 if int(m.group(3)) >= alvo else m.group(3)}"', t)
                open(tp, 'w', encoding='utf8').write(t)
    return {'categoria_antes': cat_antes, 'linha_antes': alvo, 'linha_depois': None if remover else mapa[alvo]}


ABAS_TONS = {'Tons': ('sheet2.xml', 'A', letras('B', 'L'), 'Tabela4'), 'Outras': ('sheet4.xml', 'B', letras('C', 'M'), 'Tabela9')}


def tirar_tons(tmp, strings, nome_aba, musica):
    """Remove a linha da música da aba de tons indicada (subindo as de baixo) e devolve {cantor: tom}."""
    arq, col_m, cols, tabela = ABAS_TONS[nome_aba]
    aba = Aba(tmp, arq, strings)
    cab = {c: CANTORES.get(chave(aba.valor(aba.celulas(1).get(c, ''))), aba.valor(aba.celulas(1).get(c, ''))) for c in cols}
    alvo = next((r for r in sorted(aba.linhas) if r > 1 and chave(aba.valor(aba.celulas(r).get(col_m, ''))) == chave(musica)), None)
    if alvo is None:
        return {}
    tons = {}
    for c in cols:
        v = aba.valor(aba.celulas(alvo).get(c, '')).strip()
        if v:
            tons[cab[c]] = v
    novas, attrs = {}, {}
    for r in sorted(aba.linhas):
        if r == alvo:
            continue
        n = r - 1 if r > alvo else r
        novas[n] = re.sub(r'(<c r="[A-Z]+)%d"' % r, lambda m: f'{m.group(1)}{n}"', aba.linhas[r])
        attrs[n] = aba.attrs.get(r, '')
    aba.linhas, aba.attrs = novas, attrs
    aba.salvar()
    for f in os.listdir(os.path.join(tmp, 'xl', 'tables')):
        tp = os.path.join(tmp, 'xl', 'tables', f)
        t = open(tp, encoding='utf8').read()
        if f'displayName="{tabela}"' in t:
            t = re.sub(r'ref="([A-Z]+\d+):([A-Z]+)(\d+)"', lambda m: f'ref="{m.group(1)}:{m.group(2)}{int(m.group(3)) - 1 if int(m.group(3)) >= alvo else m.group(3)}"', t)
            open(tp, 'w', encoding='utf8').write(t)
    return tons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--xlsx', required=True)
    ap.add_argument('--musica', required=True)
    ap.add_argument('--decisao', required=True, choices=['entrou', 'outras', 'standby'])
    ap.add_argument('--categoria', choices=['Celebração', 'Transição', 'Contemplação'])
    a = ap.parse_args()
    if a.decisao == 'entrou' and not a.categoria:
        raise SystemExit('--categoria é obrigatória quando --decisao entrou')
    d = os.path.join(a.repo, 'dados')
    rep = carregar(os.path.join(d, 'repertorio.json'), [])
    item = next((x for x in rep if chave(x['musica']) == chave(a.musica)), None)
    if not item:
        raise SystemExit(f'Música não encontrada em dados/repertorio.json: {a.musica}')
    nome = item['musica']
    if item.get('categoria') not in ('Teste', 'Pendente', 'Stand By'):
        raise SystemExit(f'"{nome}" já está no repertório base como {item.get("categoria")}; nada a decidir.')
    cat_antes = item['categoria']
    resumo = {'musica': nome, 'decisao': a.decisao, 'categoria_antes': cat_antes}

    if a.decisao == 'standby':
        r = mover_para_fim(a.xlsx, definir={nome: 'Stand By'})
        item['categoria'] = 'Stand By'
        rep.sort(key=lambda x: x.get('categoria') in FIM_DA_LISTA)
        resumo['categoria_depois'] = 'Stand By'
    else:
        tmp, nomes, strings = _abrir(a.xlsx)
        if a.decisao == 'entrou':
            resumo['planilha'] = reorganizar_base(tmp, strings, nome, nova_cat=a.categoria)
            tons = tirar_tons(tmp, strings, 'Outras', nome)  # se os tons estavam na aba Outras, passam para a aba Tons
            if tons:
                editar_tons(tmp, strings, [{'musica': nome, 'cantor': c, 'tom': t, 'forcar': True} for c, t in tons.items()], {nome})
            item['categoria'] = a.categoria
            resumo['categoria_depois'] = a.categoria
            resumo['tons_movidos_para_Tons'] = tons
        else:
            resumo['planilha'] = reorganizar_base(tmp, strings, nome, remover=True)
            tons = tirar_tons(tmp, strings, 'Tons', nome)
            if tons:
                editar_tons(tmp, strings, [{'musica': nome, 'cantor': c, 'tom': t, 'forcar': True} for c, t in tons.items()], set())
            rep = [x for x in rep if x is not item]
            resumo['categoria_depois'] = 'fora do repertório base (aba Outras)'
            resumo['tons_movidos_para_Outras'] = tons
        _fechar(a.xlsx, tmp, nomes)
        # ordem do repertorio.json igual à da planilha: categoria e, dentro dela, a ordem que já existia
        if a.decisao == 'entrou':
            rep = [x for x in rep if x is not item]
            mesma = [i for i, x in enumerate(rep) if x.get('categoria') == a.categoria]
            pos = (mesma[-1] + 1) if mesma else next((i for i, x in enumerate(rep) if ORDEM.get(x.get('categoria'), 9) > ORDEM[a.categoria]), len(rep))
            for i in mesma:
                if chave(rep[i]['musica']) > chave(nome):
                    pos = i
                    break
            rep.insert(pos, item)
    salvar(os.path.join(d, 'repertorio.json'), rep)
    tons_j = carregar(os.path.join(d, 'tons.json'), [])
    for t in tons_j:
        if chave(t['musica']) == chave(nome):
            t['origem'] = 'Fora do repertório' if a.decisao == 'outras' else ('Repertório base' if a.decisao == 'entrou' else t.get('origem', ''))
    salvar(os.path.join(d, 'tons.json'), tons_j)
    gerar_html(a.repo)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
