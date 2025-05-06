import speech_recognition as sr
from langgraph.checkpoint.mongodb import MongoDBSaver

from graph import create_chat_graph

# for Text to Speech - OpenAI
import asyncio
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

openai = AsyncOpenAI()

MONGODB_URI = "mongodb://admin:admin@localhost:27017/"
config = {"configurable": {"thread_id": "200"}} # thread_id is to uniquely identify each flow of state

async def speak(text) -> None:
    async with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=text,
        instructions="Speak in a cheerful and positive tone.",
        response_format="pcm",
    ) as response:
        await LocalAudioPlayer().play(response)
        
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
                    
                    latest_message = None
                    # Process the conversation with tool handling
                    for event in graph_with_mongo.stream({"messages": [{"role": "user", "content": speech_to_text}]}, config, stream_mode="values"):
                        if "messages" in event:
                            # Print the latest message
                            latest_message = event["messages"][-1]
                            # latest_message.pretty_print()
                            print(latest_message.content)

                    print("Latest message:", latest_message.content)
                    if latest_message.content is not None:
                        # Speak the latest message
                        asyncio.run(speak(latest_message.content))
                        
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")

main()



