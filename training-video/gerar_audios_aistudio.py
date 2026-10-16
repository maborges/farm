"""
SCRIPT PARA GERAÇÃO DE ÁUDIOS (Google AI Studio - Gemini TTS)
-------------------------------------------------------------
Este script utiliza a API oficial do Google AI Studio (modelo gemini-3.8-flash-tts)
para gerar narrações ultra-realistas com a voz Nika.

COMO EXECUTAR:
1. Abra o seu terminal.
2. Navegue até a pasta: cd /opt/lampp/htdocs/farm/training-video
3. Instale as dependências: pip3 install google-genai

Para rodar todos os roteiros:
   python3 gerar_audios_aistudio.py
Para rodar um roteiro específico:
   python3 gerar_audios_aistudio.py DF-00.01-CONHECA-A-DEEPFARMS.md
Para rodar apenas uma cena:
   python3 gerar_audios_aistudio.py DF-00.01-CONHECA-A-DEEPFARMS.md 3
"""

import os
import re
import datetime
import argparse
import sys
import wave
import shutil
import subprocess
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Instale a biblioteca do Google executando:")
    print("pip install google-genai")
    exit(1)

# ==========================================
# CONFIGURAÇÃO DO GOOGLE AI STUDIO
# ==========================================
# Lê da variável de ambiente GEMINI_API_KEY / GOOGLE_API_KEY ou usa a padrão
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "AQ.Ab8RN6LXTlA-YzVxaTislVQoVOnXwJg7AHLTdWHfFghHA8LnGg"
VOZ_ESCOLHIDA = "Nika"

def format_timedelta(ms):
    td = datetime.timedelta(milliseconds=ms)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

import time
from google.genai import errors

def gerar_audio_aistudio(texto, arquivo_saida):
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # O modelo correto para TTS direto da API do Gemini é o gemini-3.8-flash-tts
            response = client.models.generate_content(
                model='gemini-3.8-flash-tts',
                contents=texto,
                config=types.GenerateContentConfig(
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=VOZ_ESCOLHIDA
                            )
                        )
                    )
                )
            )
            
            # Extrai o arquivo WAV
            audio_bytes = response.candidates[0].content.parts[0].inline_data.data
            with open(arquivo_saida, 'wb') as f:
                f.write(audio_bytes)
            break # Sucesso
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 20 if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) else 5
                print(f"    [!] Servidor do Google instável/ocupado. Aguardando {wait_time}s para retentar (tentativa {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e

def obter_duracao_wav(filepath):
    with wave.open(filepath, 'r') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duracao_segundos = frames / float(rate)
        return int(duracao_segundos * 1000)

def gerar_srt_em_blocos(texto, duracao_ms):
    palavras = texto.split()
    blocos = []
    bloco_atual = []
    tamanho_atual = 0
    max_chars = 50 # Limite de caracteres por legenda na tela

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
            print(f"  ✓ Cena {srt_index:02d} já foi gerada com sucesso. Pulando...")
            srt_index += 1
            continue

        print(f"  Gerando Cena {srt_index:02d} com a voz '{VOZ_ESCOLHIDA}' (Google Gemini TTS)...")
        
        # Gera o áudio
        gerar_audio_aistudio(narration_text, wav_path)
        
        # Pega a duração
        duration_ms = obter_duracao_wav(wav_path)
        
        # Cria a legenda em blocos fracionados para o CapCut
        srt_content = gerar_srt_em_blocos(narration_text, duration_ms)
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
# MP3 conversion skipped per user request – only .wav files are kept

        srt_index += 1
        
        # Pausa de 10s para respeitar limites de taxa por minuto (RPM)
        if target_scene is None:
            time.sleep(10)
        
    if target_scene is None:
        print(f"  ✓ Todos os arquivos gerados com sucesso na pasta: {output_dir}")
    else:
        print(f"  ✓ Cena {target_scene:02d} gerada com sucesso na pasta: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Gera áudios e legendas a partir de roteiros em Markdown.")
    parser.add_argument("arquivo", nargs="?", help="Nome do arquivo específico para processar. Se não informado, processa todos.")
    parser.add_argument("cena", type=int, nargs="?", help="Número da cena específica para processar.")
    
    args = parser.parse_args()
    directory = "/opt/lampp/htdocs/farm/training-video"
    
    if args.arquivo:
        filepath = os.path.join(directory, args.arquivo)
        if not os.path.exists(filepath):
            print(f"Erro: O arquivo '{args.arquivo}' não existe.")
            sys.exit(1)
            
        print(f"Processando roteiro específico: {args.arquivo}")
        process_markdown(filepath, target_scene=args.cena)
    else:
        print(f"Procurando roteiros em {directory}...\n")
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".md") and filename.startswith("DF-"):
                filepath = os.path.join(directory, filename)
                print(f"Processando roteiro: {filename}")
                process_markdown(filepath)

if __name__ == "__main__":
    main()
