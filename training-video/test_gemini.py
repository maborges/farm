from google import genai
from google.genai import types
import traceback

try:
    client = genai.Client(api_key="AQ.Ab8RN6LXTlA-YzVxaTislVQoVOnXwJg7AHLTdWHfFghHA8LnGg")
    response = client.models.generate_content(
        model='gemini-3.8-flash-tts',
        contents='Testando a voz da Nika',
        config=types.GenerateContentConfig(
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Nika"
                    )
                )
            )
        )
    )

    if response.candidates and response.candidates[0].content.parts:
        data = response.candidates[0].content.parts[0].inline_data
        if data:
            print("AUDIO GENERATED! length:", len(data.data))
            with open("test.wav", "wb") as f:
                f.write(data.data)
        else:
            print("Still no audio")
            print(response.candidates[0].content.parts[0])
    else:
        print("Empty response")
except Exception as e:
    traceback.print_exc()
