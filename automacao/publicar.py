"""Publica no site a atualização do bloco "Próximo culto" e prepara o arquivo do dashboard.

Uso: python3 -I automacao/publicar.py --repo <clone> --msg "Próximo culto DD/MM: repertório"

Rode DEPOIS do proximo.py. O script:
1. Vê se mudou algo além da data de atualização. Se não mudou, descarta (git checkout .) e imprime
   {"status": "sem_mudancas"} — nesse caso NÃO mexa no dashboard.
2. Faz commit e push para o GitHub (com git fetch + rebase e até 3 tentativas).
3. Confere que o GitHub (origin/main) ficou com exatamente o mesmo dados/proximo_linhas.json.
4. Copia dados/proximo_linhas.json para /mnt/user-data/outputs/ds/proximo_<AAAAMMDDHHMMSS>.json.
5. Imprime {"status": "publicado", "commit": ..., "arquivo_dashboard": ..., "sha256": ...}.
Se algo falhar, imprime {"status": "erro", "etapa": ..., "detalhe": ...} e sai com código 1.
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, time

ARQS = ['dados/proximo.json', 'dados/proximo_linhas.json', 'dados/letras.json', 'dados/escala.json', 'index.html']


def git(repo, *args, check=True):
    r = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def sai(obj, codigo=0):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(codigo)


def so_data_mudou(repo):
    """True se a única diferença em relação ao último commit é o campo "atualizado"."""
    def antes(caminho):
        r = subprocess.run(['git', '-C', repo, 'show', 'HEAD:' + caminho], capture_output=True, text=True)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

    def agora(caminho):
        p = os.path.join(repo, caminho)
        return json.load(open(p, encoding='utf8')) if os.path.exists(p) else None

    def sem_data(x):
        if isinstance(x, dict):
            return {k: sem_data(v) for k, v in x.items() if k != 'atualizado'}
        if isinstance(x, list):
            return [sem_data(v) for v in x]
        return x

    # index.html é gerado a partir desses dados: basta comparar os JSON sem o campo "atualizado"
    return all(sem_data(antes(c)) == sem_data(agora(c)) for c in ('dados/proximo.json', 'dados/letras.json', 'dados/escala.json'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--msg', required=True)
    a = ap.parse_args()
    repo = a.repo
    etapa = 'verificar mudanças'
    try:
        if git(repo, 'status', '--porcelain') == '' or so_data_mudou(repo):
            git(repo, 'checkout', '--', '.')
            sai({'status': 'sem_mudancas'})
        etapa = 'commit'
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', a.msg + '\n\nTarefa automática do louvor CCT (Claude).')
        etapa = 'push'
        ultimo = ''
        for tentativa in range(3):
            git(repo, 'fetch', '-q', 'origin', 'main', check=False)
            r = subprocess.run(['git', '-C', repo, 'rebase', '-q', 'origin/main'], capture_output=True, text=True)
            if r.returncode != 0:
                git(repo, 'rebase', '--abort', check=False)
                raise RuntimeError('rebase falhou (conflito com outra atualização): ' + r.stderr.strip())
            r = subprocess.run(['git', '-C', repo, 'push', '-q', 'origin', 'HEAD:main'], capture_output=True, text=True)
            if r.returncode == 0:
                break
            ultimo = r.stderr.strip()
            time.sleep(5)
        else:
            raise RuntimeError('push recusado 3 vezes: ' + ultimo)
        etapa = 'conferir GitHub'
        git(repo, 'fetch', '-q', 'origin', 'main')
        local = open(os.path.join(repo, 'dados/proximo_linhas.json'), 'rb').read()
        remoto = subprocess.run(['git', '-C', repo, 'show', 'origin/main:dados/proximo_linhas.json'], capture_output=True).stdout
        if local != remoto:
            raise RuntimeError('o GitHub não ficou com o mesmo dados/proximo_linhas.json depois do push')
        etapa = 'arquivo do dashboard'
        json.loads(local)
        pasta = '/mnt/user-data/outputs/ds'
        os.makedirs(pasta, exist_ok=True)
        destino = os.path.join(pasta, 'proximo_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.json')
        shutil.copyfile(os.path.join(repo, 'dados/proximo_linhas.json'), destino)
        sai({'status': 'publicado', 'commit': git(repo, 'rev-parse', '--short', 'HEAD'),
             'arquivo_dashboard': destino, 'sha256': hashlib.sha256(local).hexdigest()})
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        sai({'status': 'erro', 'etapa': etapa, 'detalhe': str(e)}, 1)


if __name__ == '__main__':
    main()
