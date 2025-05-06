import speech_recognition as sr
from langgraph.checkpoint.mongodb import MongoDBSaver

from graph import create_chat_graph

# for Text to Speech - OpenAI
import asyncio
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

openai = AsyncOpenAI()

MONGODB_URI = "mongodb://admin:admin@localhost:27017/"
config = {"configurable": {"thread_id": "10"}} # thread_id is to uniquely identify each flow of state

def main():
    # for each init(); storing messages in mongodb, so that when it execute again it will load from that state
    with MongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:
        graph_with_mongo = create_chat_graph(checkpointer=checkpointer)
        
        # obtain audio from the microphone
        r = sr.Recognizer()

        with sr.Microphone() as source:
            # To remove the bg noise
            r.adjust_for_ambient_noise(source)
            
            # wait till 2 sec
            r.pause_threshold = 2
            
            while True:
                print("Say something!")
                
                audio = r.listen(source)
                
                try:
                    print("Processing audio...")
                    
                    speech_to_text = r.recognize_google(audio)
                    
                    print(f"You said: {speech_to_text}")
                    
                    for event in graph_with_mongo.stream({"messages": [{"role": "user", "content": speech_to_text}]}, config, stream_mode="values"):
                        if "messages" in event:
                            event["messages"][-1].pretty_print()
                        
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")

main()

async def speak() -> None:
    async with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input="Today is a wonderful day to build something people love!",
        instructions="Speak in a cheerful and positive tone.",
        response_format="pcm",
    ) as response:
        await LocalAudioPlayer().play(response)

if __name__ == "__main__":
    asyncio.run(speak())
