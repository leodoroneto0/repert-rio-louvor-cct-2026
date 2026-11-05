"""Atualiza o bloco "Próximo culto" (dados/proximo.json) do site e do dashboard.

Uso: python3 -I automacao/proximo.py --repo <clone> --entrada <proximo_bruto.json>

Entrada (montada a partir do grupo do Telegram):
{"data": "AAAA-MM-DD", "culto": "Domingo", "evento": "",
 "equipe": [{"funcao": "Voz", "nomes": "Talita e Débora"}, {"funcao": "Bateria", "nomes": "Lucas"}],
 "musicas": [{"titulo": "Meu Lugar", "cantor": "Débora", "tom": "C", "link": "", "letra": ""}]}

- Aplica as correções de escala do Neto (dados/ajustes_escala.json: troca "de" por "para" na data indicada).
- Completa o link pelo repertório base quando faltar.
- Completa "letra" por dados/letras.json: página da música no MultiTracks ou no Letras.mus.br, da versão indicada no
  grupo para a letra (se houver) ou da versão do link do grupo; o site e o
  dashboard mostram um botão "Letra" que abre essa página. A letra NUNCA é copiada, só o link.
- Música de um momento especial (ex.: a do momento da Santa Ceia) leva "momento": "Ceia". Ela vem depois das
  músicas normais, sempre como nº 5 (ou depois da última, se houver mais de 4): "5. 🍷 Ceia: <música>". Se a entrada não trouxer o "momento", ele é mantido
  do proximo.json atual para a mesma data e música.
- Links de letra do MultiTracks sempre no site brasileiro (https://www.multitracks.com.br/...), que mostra a letra
  em português (regra do Neto).
- Regrava dados/proximo.json, dados/proximo_linhas.json (para o dashboard) e o index.html, e imprime o resultado.
"""
import argparse, datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atualizar import carregar, salvar, chave, gerar_html, corrige_deus  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--entrada', required=True)
    a = ap.parse_args()
    d = os.path.join(a.repo, 'dados')
    p = json.load(open(a.entrada, encoding='utf8'))
    rep = carregar(os.path.join(d, 'repertorio.json'), [])
    aliases = {chave(k): v for k, v in carregar(os.path.join(d, 'aliases.json'), {}).items()}
    por_nome = {chave(x['musica']): x for x in rep}
    letras = {chave(k): v for k, v in carregar(os.path.join(d, 'letras.json'), {}).items()}
    ajustes = [x for x in carregar(os.path.join(d, 'ajustes_escala.json'), []) if x.get('data') == p.get('data')]
    aplicados = []
    for e in p.get('equipe', []):
        for aj in ajustes:
            novo = re.sub(r'\b' + re.escape(aj['de']) + r'\b', aj['para'], e.get('nomes', ''))
            if novo != e.get('nomes', ''):
                aplicados.append({'funcao': e.get('funcao'), 'de': aj['de'], 'para': aj['para']})
                e['nomes'] = novo
    atual = carregar(os.path.join(d, 'proximo.json'), {}) or {}
    momentos = {chave(x.get('titulo', '')): x['momento'] for x in atual.get('musicas', [])
                if x.get('momento') and atual.get('data') == p.get('data')}
    for m in p.get('musicas', []):
        t = (m.get('titulo') or '').strip()
        if not (m.get('momento') or '').strip() and chave(t) in momentos:
            m['momento'] = momentos[chave(t)]
        n = aliases.get(chave(t))
        b = por_nome.get(chave(n or t))
        m['titulo'] = corrige_deus(t)
        if b and not m.get('link'):
            m['link'] = b.get('link', '')
        if not m.get('letra'):
            m['letra'] = letras.get(chave(n or t)) or letras.get(chave(t)) or ''
        # regra do Neto: letra do MultiTracks sempre pelo site brasileiro (multitracks.com.br), que mostra a letra em português
        if (m.get('letra') or '').startswith('https://www.multitracks.com/'):
            m['letra'] = 'https://www.multitracks.com.br/' + m['letra'][len('https://www.multitracks.com/'):]
        if not (m.get('letra') or '').startswith(('https://www.multitracks.com.br/', 'https://www.letras.mus.br/')):
            m['letra'] = ''
        for k in ('cantor', 'tom', 'link', 'letra'):
            m[k] = (m.get(k) or '').strip()
        if (m.get('momento') or '').strip():
            m['momento'] = m['momento'].strip()
        else:
            m.pop('momento', None)
    p['atualizado'] = datetime.date.today().isoformat()
    salvar(os.path.join(d, 'proximo.json'), p)
    # versão em linhas simples para o dashboard (uma linha por pessoa da equipe e por música)
    base = {'data': p.get('data', ''), 'culto': p.get('culto', ''), 'evento': p.get('evento', ''), 'atualizado': p['atualizado']}
    linhas = [dict(base, parte='equipe', ordem=i + 1, funcao=e.get('funcao', ''), nomes=e.get('nomes', ''), titulo='', cantor='', tom='', link='', letra='')
              for i, e in enumerate(p.get('equipe', []))]
    # músicas numeradas primeiro; as de momento especial (ex.: Ceia) por último, com o momento no título
    normais = [m for m in p.get('musicas', []) if not m.get('momento')]
    especiais = [m for m in p.get('musicas', []) if m.get('momento')]
    rot = lambda m: ('🍷 ' if m['momento'].lower() == 'ceia' else '⭐ ') + m['momento'] + ': ' + m['titulo']
    linhas += [dict(base, parte='musica', ordem=i + 1, funcao='', nomes='', titulo=m['titulo'],
                    cantor=m['cantor'], tom=m['tom'], link=m['link'], letra=m['letra']) for i, m in enumerate(normais)]
    if especiais:  # a música da Ceia é a nº 5: as vagas 3 e 4 ainda sem música aparecem como "A definir"
        linhas += [dict(base, parte='musica', ordem=i + 1, funcao='', nomes='', titulo='❓ A definir', cantor='', tom='', link='', letra='')
                   for i in range(len(normais), 4)]
        n0 = max(4, len(normais))
        linhas += [dict(base, parte='musica', ordem=n0 + i + 1, funcao='', nomes='', titulo=rot(m),
                        cantor=m['cantor'], tom=m['tom'], link=m['link'], letra=m['letra']) for i, m in enumerate(especiais)]
    if not linhas:
        linhas = [dict(base, parte='info', ordem=0, funcao='', nomes='', titulo='', cantor='', tom='', link='', letra='')]
    salvar(os.path.join(d, 'proximo_linhas.json'), linhas)
    gerar_html(a.repo)
    print(json.dumps({'proximo': p, 'ajustes_escala_aplicados': aplicados}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
