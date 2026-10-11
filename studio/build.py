#!/usr/bin/env python3
"""Studio Optimuscle : fabrique une video animee « Opti coach » (1080x1920, 30 i/s).

Usage :
  python3 build.py script.json sortie.mp4 [--voix voix1.mp3 voix2.mp3 ...] [--test 1.0,5.0]

- script.json : scenes + gestes du coach (voir exemple_courbatures.json).
- --voix : un fichier audio PAR SCENE (dans l'ordre). La duree de chaque scene = duree de sa voix + 0,5 s.
  Sans --voix : musique seule, duree de chaque scene = "duree" du JSON, sinon calculee sur le temps de lecture.
- Si le JSON contient deja "s"/"e" pour chaque scene et une seule voix globale ("voix_globale"), les temps sont gardes.
- --test : ne rend que des captures PNG aux instants donnes (verification visuelle rapide).

Besoins : python3, numpy, playwright (Chromium), ffmpeg/ffprobe.
"""
import json, os, re, subprocess, sys, shutil, tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
FPS = 30


def duree(f):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def lecture(scene):
    mots = 0
    for it in scene['items']:
        mots += len(re.sub(r'\*\*|\|', ' ', str(it.get('txt', ''))).split())
    return max(3.0, round(1.0 + mots / 3.2, 1))


def enveloppe(audio, total):
    """Amplitude de la voix par image (0..1) pour animer la bouche du coach."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', audio, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    n = int(total * FPS) + 1
    pas = 16000 // FPS
    amp = []
    for i in range(n):
        seg = x[i * pas:(i + 1) * pas]
        amp.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    a = np.array(amp)
    ref = np.percentile(a[a > 0], 95) if (a > 0).any() else 1.0
    return [round(min(1.0, v / ref), 3) for v in a]


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    script_f, sortie = args[0], args[1]
    voix = []
    test = None
    if '--voix' in args:
        i = args.index('--voix') + 1
        while i < len(args) and not args[i].startswith('--'):
            voix.append(args[i]); i += 1
    if '--test' in args:
        test = [float(v) for v in args[args.index('--test') + 1].split(',')]

    S = json.load(open(script_f))
    tmp = tempfile.mkdtemp(prefix='studio_')
    voix_finale = None

    # 1. Temps des scenes
    if voix:
        if len(voix) != len(S['scenes']):
            sys.exit('Il faut exactement une voix par scene (%d scenes, %d voix).' % (len(S['scenes']), len(voix)))
        t = 0.0
        morceaux = []
        for k, (sc, v) in enumerate(zip(S['scenes'], voix)):
            d = duree(v) + 0.5
            sc['s'], sc['e'] = round(t, 2), round(t + d, 2)
            # chaque voix + 0,5 s de silence
            m = os.path.join(tmp, 'v%02d.wav' % k)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-af', 'apad=pad_dur=0.5', '-ar', '44100', '-ac', '2', m], check=True)
            morceaux.append(m)
            t += d
        S['total'] = round(t, 2)
        liste = os.path.join(tmp, 'liste.txt')
        open(liste, 'w').write(''.join("file '%s'\n" % m for m in morceaux))
        voix_finale = os.path.join(tmp, 'voix.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', liste, voix_finale], check=True)
    elif '--voix-unique' in args:
        # UNE seule voix pour toute la video (economise les credits vidIQ) : on coupe entre les scenes
        # au silence le plus proche de l'estimation proportionnelle au nombre de caracteres de chaque scene.
        v = args[args.index('--voix-unique') + 1]
        dv = duree(v)
        out = subprocess.run(['ffmpeg', '-v', 'info', '-i', v, '-af', 'silencedetect=noise=-35dB:d=0.18', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        debuts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
        fins = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
        silences = [(a + b) / 2 for a, b in zip(debuts, fins)]
        longueurs = [max(1, len(str(sc.get('voix', '')))) for sc in S['scenes']]
        tot = float(sum(longueurs))
        coupes, cumul = [], 0.0
        for L in longueurs[:-1]:
            cumul += L
            estime = dv * cumul / tot
            proches = [s for s in silences if abs(s - estime) <= 1.5 and (not coupes or s > coupes[-1] + 1.0)]
            coupes.append(min(proches, key=lambda s: abs(s - estime)) if proches else estime)
        bornes = [0.0] + coupes + [dv + 0.6]
        for k, sc in enumerate(S['scenes']):
            sc['s'], sc['e'] = round(bornes[k], 2), round(bornes[k + 1], 2)
        S['total'] = round(bornes[-1], 2)
        print('decoupe des scenes (s) :', [round(b, 1) for b in bornes])
        voix_finale = os.path.join(tmp, 'voix.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-af', 'apad=pad_dur=0.6', '-ar', '44100', '-ac', '2', voix_finale], check=True)
    elif S.get('voix_globale') and all('s' in sc for sc in S['scenes']):
        voix_finale = os.path.join(ICI, S['voix_globale']) if not os.path.isabs(S['voix_globale']) else S['voix_globale']
        S['total'] = S.get('total') or S['scenes'][-1]['e']
    else:
        t = 0.0
        for sc in S['scenes']:
            d = float(sc.get('duree') or lecture(sc))
            sc['s'], sc['e'] = round(t, 2), round(t + d, 2)
            t += d
        S['total'] = round(t, 2)

    # 2. Gestes du coach : si absents, un geste par scene (alternance), recales sur les debuts de scene
    if not S.get('coach'):
        poses = ['cross', 'explain', 'pointUL', 'count', 'thumbs', 'shrug', 'hips', 'wag', 'wave']
        S['coach'] = []
        for k, sc in enumerate(S['scenes']):
            p = sc.get('geste') or ('wave' if k == len(S['scenes']) - 1 else poses[k % 8])
            osc = {'wag': 'wag', 'wave': 'wave'}.get(p, 'bob' if p in ('explain', 'shrug', 'thumbs') else None)
            main_ = 'finger' if p in ('pointUL', 'count', 'wag') else ('thumb' if p == 'thumbs' else '')
            S['coach'].append([sc['s'], p, True, osc, main_, sc.get('bulle', '')])
    elif S.get('coach_relatif'):
        # gestes exprimes en [index_scene, decalage, pose, talk, osc, main, bulle]
        S['coach'] = [[S['scenes'][g[0]]['s'] + g[1]] + g[2:] for g in S['coach']]

    amp = enveloppe(voix_finale, S['total']) if voix_finale else []

    # 3. Rendu image par image
    from playwright.sync_api import sync_playwright
    images = os.path.join(tmp, 'img')
    os.makedirs(images)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        pg.goto('file://' + os.path.join(ICI, 'coach_template.html'))
        pg.wait_for_timeout(400)
        pg.evaluate('a => { window.AMP = a; }', amp)
        pg.evaluate('s => window.init(s)', S)
        if test:
            for t in test:
                pg.evaluate('t => render(t)', t)
                pg.screenshot(path='%s_%s.png' % (os.path.splitext(sortie)[0], t))
            b.close(); print('captures ok'); return
        n = int(S['total'] * FPS)
        for i in range(n):
            pg.evaluate('t => render(t)', i / FPS)
            pg.screenshot(path=os.path.join(images, 'f%05d.jpg' % i), type='jpeg', quality=92)
        b.close()

    muet = os.path.join(tmp, 'muet.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(images, 'f%05d.jpg'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium', muet], check=True)

    # 4. Son : voix + musique (0,13) ou musique seule (0,35), normalise
    musique = os.path.join(ICI, 'musique.mp3')
    if voix_finale:
        filtre = ('[1:a]volume=1.0[v];[2:a]volume=0.13,aloop=loop=-1:size=2e9[m];'
                  '[v][m]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', muet, '-i', voix_finale, '-i', musique,
               '-filter_complex', filtre, '-map', '0:v', '-map', '[a]', '-t', str(S['total'])]
    else:
        filtre = '[1:a]volume=0.35,aloop=loop=-1:size=2e9,afade=t=out:st=%s:d=1.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]' % max(0, S['total'] - 1.5)
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', muet, '-i', musique,
               '-filter_complex', filtre, '-map', '0:v', '-map', '[a]', '-t', str(S['total'])]
    cmd += ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', sortie]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print('ok', sortie, S['total'], 's', 'voix' if voix_finale else 'musique seule')


if __name__ == '__main__':
    main()
