"""
SCRIPT PARA GERAÇÃO DE ÁUDIOS E LEGENDAS (Edge TTS)
---------------------------------------------------
Este script lê os roteiros Markdown (DF-*.md) e gera narrações (MP3) e legendas (SRT).
Ele organiza tudo automaticamente em pastas individuais para cada roteiro.

COMO EXECUTAR:
1. Abra o seu terminal.
2. Navegue até a pasta onde este script e os roteiros estão localizados:
   cd /opt/lampp/htdocs/farm/training-video

3. Para processar TODOS os roteiros e cenas:
   python3 gerar_audios_edge_pastas.py

4. Para processar APENAS UM roteiro específico (tudo dele):
   python3 gerar_audios_edge_pastas.py DF-00.01-CONHECA-A-DEEPFARMS.md

5. Para processar APENAS UMA CENA de um roteiro específico (Ex: Cena 3):
   python3 gerar_audios_edge_pastas.py DF-00.01-CONHECA-A-DEEPFARMS.md 3

(Observação: caso não tenha as bibliotecas instaladas, rode antes: pip3 install edge-tts mutagen)
"""

import os
import re
import datetime
import asyncio
import edge_tts
import mutagen.mp3
import argparse
import subprocess  # Added for WAV conversion
import sys

# ==========================================
# CONFIGURAÇÃO DE VOZ - EDGE TTS (Gratuito)
# ==========================================
# Opções no Brasil: "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"
VOZ_ESCOLHIDA = "pt-BR-FranciscaNeural"

# Ajuste a velocidade da voz (Exemplos: "-10%" para mais lenta, "+15%" para mais rápida, ou "+0%" para original)
VELOCIDADE_DA_VOZ = "-15%"

async def gerar_audio_tts(texto, arquivo_saida):
    communicate = edge_tts.Communicate(texto, VOZ_ESCOLHIDA, rate=VELOCIDADE_DA_VOZ)
    await communicate.save(arquivo_saida)

def format_timedelta(ms):
    td = datetime.timedelta(milliseconds=ms)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def gerar_srt_em_blocos(texto, duracao_ms):
    palavras = texto.split()
    blocos = []
    bloco_atual = []
    tamanho_atual = 0
    max_chars = 50

    for palavra in palavras:
        if tamanho_atual + len(palavra) + 1 > max_chars and bloco_atual:
            blocos.append(" ".join(bloco_atual))
            bloco_atual = [palavra]
            tamanho_atual = len(palavra)
        else:
            bloco_atual.append(palavra)
            tamanho_atual += len(palavra) + 1
            
    if bloco_atual:
        blocos.append(" ".join(bloco_atual))
        
    total_chars = sum(len(b) for b in blocos)
    srt_linhas = []
    tempo_atual_ms = 0
    
    for i, bloco in enumerate(blocos):
        duracao_bloco_ms = int((len(bloco) / total_chars) * duracao_ms) if total_chars > 0 else duracao_ms
        start_time_str = format_timedelta(tempo_atual_ms)
        tempo_atual_ms += duracao_bloco_ms
        end_time_str = format_timedelta(tempo_atual_ms)
        srt_linhas.append(f"{i+1}\n{start_time_str} --> {end_time_str}\n{bloco}\n")
        
    return "\n".join(srt_linhas)

def process_markdown(filepath, target_scene=None):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(filepath)
    base_name = os.path.splitext(filename)[0]

    scenes = re.split(r'##\s+CENA', content)[1:]
    
    if not scenes:
        return
        
    output_dir = os.path.join(os.path.dirname(filepath), base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    srt_index = 1

    for scene in scenes:
        if target_scene is not None and srt_index != target_scene:
            srt_index += 1
            continue
            
        narration_match = re.search(r'###\s+NARRAÇÃO(.*?)(?:---|$)', scene, re.DOTALL | re.IGNORECASE)
        if not narration_match:
            srt_index += 1
            continue
        
        narration_text = narration_match.group(1).strip()
        narration_text = narration_text.replace('“', '').replace('”', '').replace('"', '').strip()
        
        if not narration_text:
            srt_index += 1
            continue
            
        wav_filename = f"Cena_{srt_index:02d}.wav"
        srt_filename = f"Cena_{srt_index:02d}.srt"
        wav_path = os.path.join(output_dir, wav_filename)
        srt_path = os.path.join(output_dir, srt_filename)

        if target_scene is None and os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000 and os.path.exists(srt_path):
            print(f"  ✓ Cena {srt_index:02d} já existe (.wav). Pulando...")
            srt_index += 1
            continue
            
        print(f"  Gerando Cena {srt_index:02d} (Áudio WAV e Legenda) na pasta {base_name}...")
        
        # Gera áudio temporário para calcular duração e converter em WAV puro
        temp_mp3_path = os.path.join(output_dir, f".temp_cena_{srt_index:02d}.mp3")
        asyncio.run(gerar_audio_tts(narration_text, temp_mp3_path))
        
        audio = mutagen.mp3.MP3(temp_mp3_path)
        duration_ms = int(audio.info.length * 1000)
        
        srt_content = gerar_srt_em_blocos(narration_text, duration_ms)
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # Converte para WAV
        try:
            subprocess.run(['ffmpeg', '-y', '-i', temp_mp3_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ Falha ao converter para WAV: {e}")
        finally:
            # Garante que nenhum arquivo .mp3 seja mantido na pasta
            if os.path.exists(temp_mp3_path):
                os.remove(temp_mp3_path)
        
        srt_index += 1
        
    if target_scene is None:
        print(f"  ✓ Todos os arquivos organizados com sucesso na pasta: {output_dir}")
    else:
        print(f"  ✓ Cena {target_scene:02d} gerada com sucesso na pasta: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Gera áudios e legendas a partir de roteiros em Markdown.")
    parser.add_argument("arquivo", nargs="?", help="Nome do arquivo específico para processar (Ex: DF-00.01-CONHECA-A-DEEPFARMS.md). Se não informado, processa todos.")
    parser.add_argument("cena", type=int, nargs="?", help="Número da cena específica para processar (Ex: 3). Requer que o arquivo também seja informado.")
    
    args = parser.parse_args()
    directory = "/opt/lampp/htdocs/farm/training-video"
    
    if args.arquivo:
        filepath = os.path.join(directory, args.arquivo)
        if not os.path.exists(filepath):
            print(f"Erro: O arquivo '{args.arquivo}' não foi encontrado na pasta.")
            sys.exit(1)
            
        print(f"Processando roteiro específico: {args.arquivo}")
        if args.cena:
            print(f"Filtro ativo: Gerando APENAS a Cena {args.cena:02d}\n")
        else:
            print("Gerando todas as cenas do roteiro...\n")
            
        process_markdown(filepath, target_scene=args.cena)
    else:
        print(f"Procurando todos os roteiros em {directory}...\n")
        
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".md") and filename.startswith("DF-"):
                filepath = os.path.join(directory, filename)
                print(f"Processando roteiro: {filename}")
                process_markdown(filepath)

if __name__ == "__main__":
    main()
