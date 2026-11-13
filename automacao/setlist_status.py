"""Diz se o repertório do bloco "Próximo culto" está pronto e se o setlist do MultiTracks precisa ser criado/corrigido.

Uso: python3 -I automacao/setlist_status.py --repo <clone>            -> imprime o status (JSON)
     python3 -I automacao/setlist_status.py --repo <clone> --marcar   -> grava dados/setlist_mt.json (depois de conferir o MultiTracks)
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument('--repo', required=True)
ap.add_argument('--marcar', action='store_true')
a = ap.parse_args()
d = os.path.join(a.repo, 'dados')
p = json.load(open(os.path.join(d, 'proximo.json'), encoding='utf8'))
ms = p.get('musicas', [])
normais = [m for m in ms if not m.get('momento')]
especiais = [m for m in ms if m.get('momento')]
lista = [{'titulo': m['titulo'], 'tom': m.get('tom', ''), 'momento': m.get('momento', '')} for m in normais + especiais]
vagas = [m for m in ms if not m.get('titulo') or m['titulo'].startswith('❓')]
sem_tom = [m['titulo'] for m in ms if m not in vagas and not m.get('tom')]
ceia_falta = 'ceia' in (p.get('evento') or '').lower() and not especiais
pronto = bool(ms) and len(normais) >= 4 and not vagas and not sem_tom and not ceia_falta
dt = p.get('data', '')
nome = 'Culto ' + dt[8:10] + '/' + dt[5:7] + '/' + dt[:4] if dt else ''
arq = os.path.join(d, 'setlist_mt.json')
feito = json.load(open(arq, encoding='utf8')) if os.path.exists(arq) else {}
atual = {'nome': nome, 'data': dt, 'musicas': lista}
if a.marcar:
    if not pronto:
        raise SystemExit('repertório não está pronto; nada marcado')
    json.dump(atual, open(arq, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(json.dumps({'marcado': nome}, ensure_ascii=False))
else:
    print(json.dumps({'pronto': pronto, 'precisa_mexer_no_multitracks': pronto and feito != atual,
                      'ja_criado_antes': feito.get('nome') == nome, 'nome': nome, 'musicas': lista,
                      'faltando': {'vagas': len(vagas), 'sem_tom': sem_tom, 'ceia': ceia_falta}}, ensure_ascii=False))
