import os
import json
from urllib.request import Request, urlopen
import openai
import pprint
import discord
import time
import re
import asyncio

# Initialize OpenAI settings
openai.api_key = os.environ.get("OPENAI_API_KEY", "dummy")  # Fallback to "dummy" if not set
openai.api_base = "http://10.10.0.140:8000/v1"
#openai.api_version = "2023-05-15"

TOKEN = os.environ.get("DISCORD_TOKEN", "dummy")
GUILD = 'placeholder'

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def interact_with_indigo(content_json=None):
    start_time = time.time()

    print("Interacting with indigo")
    REFLECTORNAME = os.environ.get("REFLECTOR_NAME", "dummy")
    APIKEY = os.environ.get("INDIGO_API_KEY", "dummy")  # Fallback to hardcoded key if not set

    print(f"Initialization Time: {time.time() - start_time:.6f} seconds")

    if content_json:
        action_time = time.time()

        if content_json.get('action', {}).get('update', False):
            changeset = content_json.get('changeset', [{}])[0]
            print(f"Changeset: {changeset}")

            device_id = changeset.get('id')
            states = changeset.get('futureStates', changeset.get('states', {}))

            if 'brightnessLevel' in states:
                req_time = time.time()
                brightness = states['brightnessLevel']
                message = json.dumps({
                    "id": "id1",
                    "message": "indigo.dimmer.setBrightness",
                    "objectId": device_id,
                    "parameters": {
                        "value": brightness,
                        "delay": 0
                    }
                }).encode("utf8")
                print(message)

                req = Request(f"https://{REFLECTORNAME}.indigodomo.net/v2/api/command", data=message)
                req.add_header('Authorization', f"Bearer {APIKEY}")
                with urlopen(req) as request:
                    reply = json.load(request)
                    print(reply)
                print(f"Request Brightness Time: {time.time() - req_time:.6f} seconds")
                # Indigo needs a pause between commands
                time.sleep(1)

            if 'onOffState' in states:
                req_time = time.time()
                onOffState = states['onOffState']
                command = "indigo.device.turnOff" if not onOffState else "indigo.device.turnOn"
                message = json.dumps({
                    "id": "id2",
                    "message": command,
                    "objectId": device_id
                }).encode("utf8")

                req = Request(f"https://{REFLECTORNAME}.indigodomo.net/v2/api/command", data=message)
                req.add_header('Authorization', f"Bearer {APIKEY}")
                with urlopen(req) as request:
                    reply = json.load(request)
                    print(reply)
                print(f"Request On/Off Time: {time.time() - req_time:.6f} seconds")

        print(f"Total Action Time: {time.time() - action_time:.6f} seconds")

    else:
        req_time = time.time()
        req = Request(f"https://{REFLECTORNAME}.indigodomo.net/v2/api/indigo.devices")
        req.add_header('Authorization', f"Bearer {APIKEY}")
        with urlopen(req) as request:
            devices = json.load(request)
            filtered_data = []
            for device in devices:
                filtered_data.append({
                    'name': device['name'],
                    'id': device['id'],
                    'states': device['states']
                })
        print(f"Request Devices Time: {time.time() - req_time:.6f} seconds")

        return json.dumps(filtered_data)

    print(f"Total Execution Time: {time.time() - start_time:.6f} seconds")

async def create_openai_completion(combined_data):
    chat_completion = openai.ChatCompletion.create(
        #deployment_id="deployment-name",
        temperature=0.5,
        max_tokens=451,
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": combined_data}]
    )

    content = chat_completion.choices[0].message.content
    print("printing content")
    print(chat_completion.choices[0].message.content)
    print("/printing content")

    return content

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message):
        async with message.channel.typing():
            query = re.sub('<.*?>', '', message.content).strip()
            filtered_json_str = await interact_with_indigo()

            # Combine the query and the filtered_json_str into one JSON object
            combined_data_dict = {
                "question": query,
                "devices": json.loads(filtered_json_str)
            }
            combined_data_str = json.dumps(combined_data_dict)

            # Add instruction and response markers
            combined_data = f"\n\n### Instructions:\n{combined_data_str}\n### Response:\n"

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    content = await create_openai_completion(combined_data)

                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                        json_str = content[start_idx:end_idx + 1]
                        pprint.pprint(json_str)
                        content_json = json.loads(json_str)
                        answer = content_json.get('answer', 'Answer not found')

                        if "sorry" in answer.lower():
                            print("Detected 'sorry' in the answer. Retrying...")
                            await asyncio.sleep(2 ** attempt)
                            continue

                        if content_json.get('action', {}).get('update', False):
                            changeset = content_json.get('changeset', [])
                            if changeset:
                                await interact_with_indigo(content_json)

                        print(f"Full JSON response: {content_json}")
                        await message.reply(answer, mention_author=False)
                        return
                    else:
                        await message.reply("Couldn't extract JSON object", mention_author=False)
                        return

                except Exception as err:
                    print(f"Attempt {attempt + 1} failed: {err}")
                    await asyncio.sleep(2 ** attempt)

        await message.reply("An error occurred after multiple attempts", mention_author=False)

client.run(TOKEN)
