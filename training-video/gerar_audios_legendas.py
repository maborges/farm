import os
import re
import datetime

try:
    import asyncio
    import edge_tts
    import mutagen.mp3
except ImportError:
    print("Por favor, instale as dependências executando:")
    print("pip install edge-tts mutagen")
    exit(1)

# Escolha a voz aqui!
# Opções em português do Brasil (pt-BR):
# "pt-BR-AntonioNeural"   (Voz Masculina)
# "pt-BR-FranciscaNeural" (Voz Feminina)
# "pt-BR-ThalitaNeural"   (Voz Feminina)
VOZ_ESCOLHIDA = "pt-BR-AntonioNeural"

async def gerar_audio_tts(texto, arquivo_saida):
    communicate = edge_tts.Communicate(texto, VOZ_ESCOLHIDA)
    await communicate.save(arquivo_saida)

def format_timedelta(ms):
    td = datetime.timedelta(milliseconds=ms)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def process_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(filepath)
    base_name = os.path.splitext(filename)[0]

    # Divide o arquivo nas cenas
    scenes = re.split(r'##\s+CENA', content)[1:]
    
    if not scenes:
        return
        
    srt_content = ""
    current_ms = 0
    srt_index = 1
    
    full_audio_data = b""

    for scene in scenes:
        # Extrai a narração até o final da cena (marcado por --- ou fim da string)
        narration_match = re.search(r'###\s+NARRAÇÃO(.*?)(?:---|$)', scene, re.DOTALL | re.IGNORECASE)
        if not narration_match:
            continue
        
        narration_text = narration_match.group(1).strip()
        # Remove as aspas
        narration_text = narration_text.replace('“', '').replace('”', '').replace('"', '').strip()
        
        if not narration_text:
            continue
            
        print(f"  Gerando áudio da cena {srt_index}...")
        
        # Gera o áudio com edge-tts
        temp_mp3 = f"temp_{base_name}_{srt_index}.mp3"
        asyncio.run(gerar_audio_tts(narration_text, temp_mp3))
        
        # Pega a duração para a legenda
        audio = mutagen.mp3.MP3(temp_mp3)
        duration_ms = int(audio.info.length * 1000)
        
        # Concatena o áudio (simples apêndice de arquivo mp3 funciona na maioria dos players)
        with open(temp_mp3, 'rb') as f:
            full_audio_data += f.read()
            
        os.remove(temp_mp3)
        
        # Define o tempo da legenda
        start_time_str = format_timedelta(current_ms)
        end_time_str = format_timedelta(current_ms + duration_ms)
        
        srt_content += f"{srt_index}\n{start_time_str} --> {end_time_str}\n{narration_text}\n\n"
        
        current_ms += duration_ms
        srt_index += 1

    if srt_content:
        # Salva o arquivo .srt
        srt_path = os.path.join(os.path.dirname(filepath), f"{base_name}.srt")
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        print(f"  Salvo: {srt_path}")
            
        # Salva o arquivo .mp3 consolidado
        mp3_path = os.path.join(os.path.dirname(filepath), f"{base_name}.mp3")
        with open(mp3_path, 'wb') as f:
            f.write(full_audio_data)
        print(f"  Salvo: {mp3_path}\n")


def main():
    directory = "/opt/lampp/htdocs/farm/training-video"
    print(f"Procurando roteiros em {directory}...")
    
    for filename in os.listdir(directory):
        if filename.endswith(".md") and filename.startswith("DF-"):
            filepath = os.path.join(directory, filename)
            print(f"Processando {filename}...")
            process_markdown(filepath)

if __name__ == "__main__":
    main()
