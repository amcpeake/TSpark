import discord
from discord.ext import commands
import requests
import random
import traceback
import re
import asyncio
import wave
import numpy as np
import subprocess
from .storage import \
    JSONStore  # relative import means this wak_funcs.py can only be used as part of the tony_modules package now
import os
import io
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# GLOBAL DEFINITIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ROOTPATH = os.environ['TONYROOT']  # Bot's root path
STORAGE_FILE = os.path.join(ROOTPATH, 'storage', 'lego_storage.json')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class LegoStore(JSONStore):
    def __init__(self):
        super().__init__(STORAGE_FILE)
        if self['reminders'] is None:
            self['reminders'] = {}
        if self['watchlist'] is None:
            self['watchlist'] = {}


class LegoFuncs(commands.Cog):
    def __init__(self, bot, store):
        self.bot = bot
        self.storage = store

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.filter(message, False):
            cur_channel = self.bot.get_channel(message.channel.id)

            if message.channel.id in self.bot.config['CHANNEL_IDS']['VIDEO_IDS'] and "http" in message.content:
                await message.add_reaction("👀")
                await message.add_reaction("🕔")

            elif message.channel.id == self.bot.config['CHANNEL_IDS']['MUSIC'] and "http" in message.content:
                await message.add_reaction("👂")
                await message.add_reaction("🕔")

            if 'ai' in re.findall(r'\bai\b', message.content.lower()):
                async with cur_channel.typing():
                    await cur_channel.send('AI...?')
                    await asyncio.sleep(random.randint(30, 50))
                    await cur_channel.send('bum to the boo to the bum to the bass https://www.youtube.com/watch?v=bawDe5jag68')


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        channel = self.bot.get_channel(reaction.channel_id)
        user = self.bot.get_user(reaction.user_id)
        msg = await channel.fetch_message(reaction.message_id)
    
        try:
            name = reaction.emoji.name
        except AttributeError:
            return
        else:
            if name == 'upvote' or name == 'downvote': # Add to best/worstof
                emb = discord.Embed(title=msg.content, colour=msg.author.colour)  # Create embed
                emb.set_author(name=msg.author.display_name + ':', icon_url=msg.author.avatar_url)
                emb.add_field(name="l4tl:", value=msg.jump_url, inline=True)
                
                if msg.attachments:
                    emb.set_image(url=list(msg.attachments)[0].url)

                if name == 'downvote':
                    chnl = self.bot.get_channel(self.bot.config['CHANNEL_IDS']['WORST_OF'])
                    await chnl.send(
                        f"**{user.name} has declared the following to be rude, or otherwise offensive content:**",
                        embed=emb)
                elif name == 'upvote':
                    chnl = self.bot.get_channel(self.bot.config['CHANNEL_IDS']['BEST_OF'])
                    await chnl.send(
                        f"**{user.name} declared the following to be highly esteemed content:**",
                        embed=emb)

            elif name == '🕔': # Add to watchlist
                wl = self.storage.read('watchlist')
                uid = str(user.id)
                if uid not in self.storage['watchlist']:
                    wl[uid] = {}
                    self.storage.write('watchlist', wl)
                for url in re.findall(r'http\S+', msg.content):
                    if url not in wl[uid]:
                        wl[uid][url] = msg.jump_url
                self.storage.write('watchlist', wl)

            elif name == '👀' or name == '👂': # Remove from watchlist
                wl = self.storage.read('watchlist')
                uid = str(user.id)
                for url in re.findall(r'http\S+', msg.content):
                    if uid in wl and url in wl[uid]:
                        del wl[uid][url]
                        self.storage.write('watchlist', wl)

    @commands.command(description = "<str> ~ Echo input as output, useful for testing pipes")
    async def echo(self, ctx, *args):
        await ctx.send(' '.join(args))

    @commands.command(description = "~ Find AI-generated anime scrots", 
            usage = "\n\t-r : Random creativity level\n\t-c <creativity> : Set creativity level\n\t-s <seed> : Set seed")
    async def anime(self, ctx, *args):
        args = list(args)
        creativity = "2.0"
        seed = str(random.randint(0, 49999)).zfill(4)

        if '-r' in args:
            creativity = round(random.uniform(0.3, 2.0), 1)

        elif '-c' in args:
            try:
                c = float(args[args.index('-c') + 1])
                if c >= 0.3 and c <= 2.0:
                    creativity = str(c)
            except:
                pass
        
        if '-s' in args:
            try:
                s = int(args[args.index('-s') + 1])
                if s >= 0 and s <= 49999:
                    seed = str(s).zfill(4)
            except:
                pass
        
        await ctx.send(f"https://thisanimedoesnotexist.ai/results/psi-{creativity}/seed{seed}.png")

    @commands.command(aliases=['temp'], description = "~ Get current temperature at the gamer house")
    async def temperature(self, ctx):
        for url in self.bot.config['URLS']['TEMP_URLS']:
            try:
                await ctx.send(f"{url['name']}: {requests.get(url['url'], timeout=2).text}")
            except:
                await ctx.send(f"Failed to reach {url['name']}")

    @commands.command(description = "~ Generate spoiler'd files on mobile",
            usage = "-m <message ID> : Specify message to pull files from")
    async def spoiler(self, ctx, *args):
        args = list(args)
        files = []
        channel = self.bot.get_channel(self.bot.config['CHANNEL_IDS']['SPOILER'])
        
        if '-m' in args:
            while '-m' in args:
                msg = await ctx.channel.fetch_message(args.pop(args.index('-m') + 1))
                args.remove('-m')
                files += [await attachment.to_file() for attachment in msg.attachments]
        else:
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
        
        if not files:
            await ctx.send("Error: No attachments found")
            return
        
        for f in files:
            f.filename = f"SPOILER_{f.filename}"
        await ctx.send(' '.join(args), files=files)

    
    @commands.command(description = "~ View your watchlist")
    async def watchlist(self, ctx):
        uid = str(ctx.author.id)
        if uid in self.storage['watchlist'] and self.storage['watchlist'][uid]:
            if ctx.author.dm_channel is None:
                await ctx.author.create_dm()
            channel = ctx.author.dm_channel

            for url, msgURL in self.storage['watchlist'][uid].items():
                try: # User might not accept DMs
                    msg = await channel.send(f"{url} ({msgURL})")
                except:
                    msg = await ctx.send(f"{url} ({msgURL})")
                await msg.add_reaction("👀")
        else:
            await ctx.send("You have no videos in your watch list")

    @commands.command(description = "~ Output Tony's public IP")
    async def ip(self, ctx):
        await ctx.send(requests.get("https://ifconfig.me").text)

    @commands.command(description = "<str> ~ Converts a string to speech",
            usage = "\n\t[config] : Object in form {<speed>, <pitch>}")
    async def speak(self, ctx, *args):
        word_map = {}
        words = list(args)

        params_set = False
        config = {"speed": 1, "pitch": 1}
        sentence_file = io.BytesIO() # Full sentence
        with wave.open(sentence_file, 'wb') as sf:
            for word in words:
                if re.match(r'\{[0-9\.,-]+\}', word):
                    con = re.sub('[\{\}]', '', word)
                    try:
                        config["speed"] = float(con.split(',')[0])
                        config["pitch"] = float(con.split(',')[1])
                    except:
                        pass
                    continue
                 
                word = re.sub(r'[^a-zA-Z0-9\']', '', word)
                # Easy to generate and change pitch/speed using espeak, less so with MW
                # Therefore we should note which type a file is in word_map as well as its config
                if word not in word_map:
                    try:
                        resp = requests.get(
                                f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={self.bot.config['API_KEYS']['MERRIAM_WEBSTER']}"
                                ).json()
                        
                        audio = resp[0]["hwi"]["prs"][0]["sound"]["audio"]
                        if audio[0:3] == "bix":
                            sub = "bix"
                        elif audio[0:2] == "gg":
                            sub = "gg"
                        elif not audio[0].isalpha():
                            sub = "number"
                        else:
                            sub = audio[0]
                        
                        word_map[word] = io.BytesIO(requests.get(
                            f"https://media.merriam-webster.com/soundc11/{sub}/{audio}.wav",
                            stream=True).content)
                        #word_file = io.BytesIO()
                        #with wave.open(word_file, 'wb') as wf:
                        #    with wave.open(content_file, 'rb') as cf:
                        #        wf.setparams(cf.getparams())
                        #        pos = float(0)
                        #        while pos < cf.getnframes():
                        #            cf.setpos(int(pos))
                        #            wf.writeframes(cf.readframes(1))
                        #            pos += speed
                        #word_file.seek(0)
                        
                    except:
                        proc = subprocess.Popen(['espeak', word, '-z', '--stdout'], stdout=subprocess.PIPE)
                        word_map[word] = io.BytesIO(proc.communicate()[0])
               
                alt_file = word_map[word] # File to be altered
                alt_file.seek(0)
                if config["speed"] != 1 or config["pitch"] != 1: # Must alter file
                    alt_file = io.BytesIO()
                    with wave.open(alt_file, 'wb') as tf:
                        with wave.open(word_map[word], 'rb') as cf:
                            params = list(cf.getparams())
                            params[3] = 0
                            tf.setparams(tuple(params))
                            tf.setframerate(int(cf.getframerate() * config["speed"]))
                            
                            if config["pitch"] == 1:
                                continue

                            nframes = (word_map[word].getbuffer().nbytes - 44) // (cf.getnchannels() * cf.getsampwidth())
                            fr = 20 # Number of iterations per second of audio
                            sz = cf.getframerate()//fr # Number of frames per iteration
                            c = int(nframes/sz) # Number of iterations
                            shift = int((100*config["pitch"])//fr)
                            for _ in range(c):
                                if cf.getsampwidth() == 1:
                                    typ = np.int8
                                elif cf.getsampwidth() == 2:
                                    typ = np.int16
                                
                                da = np.fromstring(cf.readframes(sz), dtype=typ)
                                if cf.getnchannels() == 1:
                                    f = np.fft.rfft(da)
                                    f = np.roll(f, shift)
                                    if shift >= 0:
                                        f[0:shift] = 0
                                    else:
                                        f[shift:] = 0
                                    n = np.fft.irfft(f)
                                    ns = np.column_stack((n)).ravel().astype(typ)
                                elif cf.getnchannels() == 2:
                                    left, right = da[0::2], da[1::2]
                                    lf, rf = np.fft.rfft(left), np.fft.rfft(right)
                                    lf, rf = np.roll(lf, shift), np.roll(rf, shift)
                                    if shift >= 0:
                                        lf[0:shift], rf[0:shift] = 0, 0
                                    else:
                                        lf[shift:], rf[shift:] = 0, 0
                                    nl, nr = np.fft.irfft(lf), np.fft.irfft(rf)
                                    ns = np.column_stack((nl, nr)).ravel().astype(typ)
                                tf.writeframes(ns.tostring())
                
                alt_file.seek(0)
                with wave.open(alt_file, 'rb') as wf:
                    if not params_set:
                        sf.setparams(wf.getparams())
                        params_set = True
                    sf.writeframes(wf.readframes(wf.getnframes()))
                    
        sentence_file.seek(0)
        await ctx.send(file=discord.File(io.BytesIO(sentence_file.read()), filename="speak.wav"))

    @commands.command(description = "<word> ~ Define a given word", usage = "\n\t-n <#> : Number of defintions to provide")
    async def define(self, ctx, *args):
        if '-n' in args:
            limit = args[args.index('-n') + 1]
        else:
            limit = 1
        
        word = re.sub(r'[^a-zA-Z0-9\']', '', args[-1])
        url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={self.bot.config['API_KEYS']['MERRIAM_WEBSTER']}"

        try:
            resp = requests.get(url).json()
        except:
            await ctx.send(f"Error: {word} has no definition")
            return

        for i in range(0, int(limit)):
            try:
                emb = discord.Embed(title=f"{word} - {resp[i]['fl']}:", description=f"{resp[i]['shortdef'][0]}")
            except:
                await ctx.send(f"{word} has no more definitions")
                break

            await ctx.send(embed=emb)

        try:
            audio = resp[0]["hwi"]["prs"][0]["sound"]["audio"]
            # Arbitary api rules (found here https://dictionaryapi.com/products/json#sec-2.prs)
            if audio[0:3] == "bix":
                sub = "bix"
            elif audio[0:2] == "gg":
                sub = "gg"
            elif not audio[0].isalpha():
                sub = "number"
            else:
                sub = audio[0]
            alink = f"https://media.merriam-webster.com/soundc11/{sub}/{audio}.wav"
            await ctx.send(file=discord.File(io.BytesIO(requests.get(alink, stream=True).content), filename=f"{word}.wav"))
        except:
            await ctx.send("No pronunciation found")

    @commands.command(description = "<options> ~ Execute code in various languages", 
            usage = "\n\t-m <message ID> : Message to read the code from\n\t-l <language>\n\t-c <code>\n\t-i <input> : Input is a JSON list of lists, i.e. [[0]]\n\tCode should take input from stdin and output to stdout")
    async def pyde(self, ctx, *args):
        request = {}
        if '-m' in args:
            try:
                msg = await ctx.channel.fetch_message(args[args.index('-m') + 1])
                msg = msg.content
            except discord.errors.NotFound:
                await ctx.send("Error: Message not found")
                return
            else:
                if re.match(r"^```[a-zA-Z0-9]+", msg): # Language included
                    request['language'] = msg.split('\n')[0].replace('```', '')
                    msg = msg[len(request['language']) + 3:-3]
                request['code'] = msg

        if '-l' in args:
            request['language'] = args[args.index('-l') + 1]

        if '-c' in args:
            request['code'] = args[args.index('-c') + 1]

        if '-i' in args:
            try:
                request['input'] = json.loads(args[args.index('-i') + 1])
            except json.decoder.JSONDecodeError:
                await ctx.send("Error: Input must be valid JSON string")
                return

        for key in ('code', 'language'):
            if key not in request.keys() or not request[key]:
                await ctx.send(f"Error: No {key} value provided")
                return

        response = requests.post(self.bot.config['URLS']['PYDE'], '', request)

        rJSON = response.json()
        rString = f"**Exit Status:** {rJSON['status']}"

        if rJSON['status'] == 'pass':
            color = 65280
        else:
            color = 16711680

        if 'input' in request.keys():
            rString += "\n**Input:**"
            for case in request['input']:
                rString += f"\n\tCase {request['input'].index(case) + 1}:"
                rString += f"\n\t\t{str(case)}"

        if 'output' in rJSON.keys():
            rString += "\n**Output:**"
            for case in rJSON['output']:
                rString += f"\n\tCase {rJSON['output'].index(case) + 1}:"
                rString += f"\n\t\t{str(case)}"

        if 'error' in rJSON.keys():
            rString += "\n**Errors:**\n" + ' '.join(rJSON['error'])

        if '-f' in args:
            await ctx.send(content="Here's your results, sir",
                           file=discord.File(io.BytesIO(rString.encode()),
                                             filename="results.txt")
                           )
        else:
            await ctx.send(embed=discord.Embed(
                title=f"PyDE Compilation Results",
                description=rString,
                color=color
            ))


    @commands.command(description = "~ Tells a joke")
    async def joke(self, ctx):
        resp = requests.get('https://api.chucknorris.io/jokes/random').json()  # Get the response in JSON
        emb = discord.Embed(title=resp['value'])  # Prepare the embed
        emb.set_author(name='​', icon_url=resp['icon_url'])  # Attach icon
        
        await ctx.send(embed=emb)

    @commands.command(description = "<options> ~ Read or edit Tony's config aka registries",
            usage = "\n\t-l [registry]: List all registries or value of specific registry\n\t-a <registry> <value>: Add a value to a list-based registry\n\t<registry> <value> : Edit a registry")
    async def regedit(self, ctx, *args):
        if len(args) == 0:
            await ctx.send(f'Error: Must provide options or key')

        elif '-l' in args:
            if len(args) == 1:
                await ctx.send(f'Valid registries are: {", ".join(self.bot.config.read().keys())}')
            else:
                key = args[args.index('-l') + 1]
                if key not in self.bot.config['LOCKED']:
                    await ctx.send(f'{key} is {self.bot.config[key]}')
                else:
                    await ctx.send(f'Registry {key} is locked. Cannot display value')

        elif '-a' in args:
            if len(args) == 3:
                key = args[1]
                value = args[2]

                if key not in self.bot.config['LOCKED']:
                    all_values = self.bot.config[key]
                    if isinstance(all_values, list):
                        if isinstance(all_values[0], int) and is_num(value):
                            value = int(value)
                        all_values.append(value)
                        self.bot.config.write(key, all_values)
                        await ctx.send(f'Added {value} to registry {key}')
                    else:
                        await ctx.send(f'Registry must be of type list to add')
                else:
                    await ctx.send(f'Registry {key} is locked. Cannot add {value}')

            else:
                await ctx.send(f'Error: Must provide key to add to and value to add')

        elif args[0] in self.bot.config.read():
            key = args[0]
            value = args[1]
            if key in self.bot.config['LOCKED']:
                await ctx.send(f'Registry {key} is locked, cannot edit')
            else:
                if isinstance(self.bot.config[key], int) and is_num(value):
                    value = int(value)
                self.bot.config[key] = value
                await ctx.send(f"Changed {key} from {self.bot.config[key]} to {value}")

        else:
            await ctx.send(f'Invalid registry "{args[0]}"\nValid registries are: {", ".join(self.bot.config.keys())}')

    @commands.command(description = "<link> ~ Download a link from BandCamp or SoundCloud")
    async def download(self, ctx, *links):
        sesh = requests.Session()
        headerdata = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/64.0.3282.140 Chrome/64.0.3282.140 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7}'
        }

        async def get(sesh, url, headerData, parameters={}, maxNumTries=3):
            for _ in range(1, maxNumTries):
                try:
                    return sesh.get(url, params=parameters, headers=headerData)
                except:
                    continue
            await ctx.send("Failed to get data")

        async def soundcloud(sesh, page, headerdata):
            songs = []
            trackParams = {"client_id": self.bot.config['API_KEYS']['SOUNDCLOUD']}
            ids = set(re.findall(r'"id":[0-9]{5,}', page))
            
            for i in ids:
                try:
                    i = str(i)[5:]
                    infoURL = f"https://api-v2.soundcloud.com/tracks/{i}?client_id={self.bot.config['API_KEYS']['SOUNDCLOUD']}"
                    info = await get(sesh, infoURL, headerdata, trackParams)
                    dlurl = list(filter(lambda u: u["format"]["protocol"] == "progressive", info.json()["media"]["transcodings"]))[0]["url"]
                    mp3URL = await get(sesh, dlurl, headerdata, trackParams)
                    mp3 = await get(sesh, mp3URL.json()["url"], headerdata)
                    songs.append({'title': f'{info.json()["title"]}.mp3', 'file': io.BytesIO(mp3.content)})
                except:
                    continue
            return songs

        async def bandcamp(sesh, albumpage, headerdata):  # {"album name": "", "album art": f, "files": []}
            infostart = albumpage.find('trackinfo: ') + len('trackinfo: ')
            infoend = albumpage.find('\n', infostart) - 1
            info = json.loads(albumpage[infostart:infoend])

            imagestart = albumpage.find('<link rel="image_src" href="') + len('<link rel="image_src" href="')
            imagelink = imagestart[:imagestart.find('">')]

            namestart = albumpage.find('<title>') + len('<title>')
            nameend = albumpage.find('</title>')
            albumname = albumpage[namestart:nameend]
            await ctx.send(f'Downloading {albumname}....')
            songs = []
            trackNum = 1
            for track in info:
                if track['file'] is not None:
                    title = f'{str(trackNum)}.{track["title"]}.mp3'.replace('/', '\\\\')
                    dlLink = track['file']['mp3-128']
                    mp3 = await get(sesh, dlLink, headerdata)
                    songs.append({"title": title, "file": mp3.content})
                    trackNum += 1

            data = await get(sesh, imagelink, headerdata)
            return {"name": albumname, "art": data.content, "songs": songs}

        for link in links:
            plink = urlparse(link)
            page = await get(sesh, link, headerdata)

            if 'bandcamp' in plink.netloc:
                album = await bandcamp(sesh, page.content.decode('utf-8'), headerdata)
                songs = album['songs']
                await ctx.send(file=discord.File(album['art'], 'albumart.png'))

            elif 'soundcloud' in plink.netloc:
                songs = await soundcloud(sesh, page.content.decode('utf-8'), headerdata)

            else:
                await ctx.send(f"{link} is not a supported site, skipping...")
                continue

            for song in songs:
                try:
                    await ctx.send(file=discord.File(song['file'], filename=song['title']))
                except discord.errors.HTTPException:
                    await ctx.send("Error, file too large to send...")
                except:
                    await ctx.send("Failed to send file")

        await ctx.send("All done")

    @commands.command(description = "~ Roll a number")
    async def roll(self, ctx):  # Outputs the message id of the message sent ("roll")
        await ctx.send(f"{ctx.message.id}")

    @commands.command(description = "<emoji> ~ Get all messages between last two instance of messages with given reaction(s)",
            usage = "\n\t-c <#channel>\n\t-n <#> : Number of messages to search through")
    async def nab(self, ctx, *cmds):  # Gets all messages between last two instances of messages with given reaction(s)
        #  DEFAULT VALUES
        cmds = list(cmds)
        emojis = []
        num = 1000
        channel = self.bot.get_channel(ctx.channel.id)
        FLAGS = ['-c', '-n']
        #  FLAG HANDLING
        for cmd in cmds:
            if cmd == '-c':  # Specify the channel to nab from
                channel = self.bot.get_channel(cmd.pop(cmd.index('-c') + 1))
                continue

            if cmd == '-n':  # Specify number of messages to look through
                num = cmd.pop(cmd.index('-n') + 1)
                if is_num(num):  # If
                    num = int(num)
                elif num == 'all':
                    num = 'None'  # None means all messages
                continue

            if cmds[cmds.index(cmd) - 1] not in FLAGS:
                emojis.append(cmd)

        if not emojis:
            await ctx.send('Error: an emoji is required')
            return

        msgs = b''
        num_found = 0
        async for msg in ctx.history(limit=num):
            if all(x in (o.emoji for o in msg.reactions) for x in emojis):
                num_found += 1
            if num_found:
                msgs = msg.author.display_name.encode() + b': ' + msg.content.encode() + b'\n' + msgs
            if num_found == 2:
                break
        else:
            await channel.send(f'Error: Two instances of {emojis} not found in last {num} messages')
            return

        await channel.send(file=discord.File(io.BytesIO(msgs), filename='nab.txt'))

    @commands.command(description = "<str> ~ Search for a given string",
            usage = "\n\t-u <@user... (self)>\n\t-r <emoji...> : Find messages with given reaction\n\t-c <#channel...>\n\t-n <#> : Number of messages to search")
    async def search(self, ctx, *cmd):
        cmd = list(cmd)
        users = []
        reactions = []
        channels = []
        msgs = []
        num = 1000
        while any(x in cmd for x in ['-u', '-n', '-r', '-c']):
            if '-u' in cmd:
                user = cmd.pop(cmd.index('-u') + 1)
                if user.lower() == 'all':
                    users = ctx.guild.members
                else:
                    await ctx.send(user)
                    users.append(self.bot.get_user(int(re.sub('[!<@>]', '', user))))
                cmd.remove('-u')

            if '-r' in cmd:
                reactions.append(cmd.pop(cmd.index('-r') + 1))
                cmd.remove('-r')

            if '-c' in cmd:
                chan = cmd.pop(cmd.index('-c') + 1)
                if chan.lower() == 'all':
                    channels = ctx.guild.text_channels
                else:
                    channels.append(self.bot.get_channel(int(re.sub('[<#>]', '', chan))))
                cmd.remove('-c')

            if '-n' in cmd:
                num = cmd.pop(cmd.index('-n') + 1)
                if num.lower() == 'all':
                    num = None
                elif is_num(num):
                    num = int(num)
                else:
                    await ctx.send('Error: Num value must be "all" or int')
                    return
                cmd.remove('-n')

        if not channels:
            channels.append(ctx.channel)
        if not users:
            users.append(ctx.author)
        await ctx.send(f"```Searching through last {num} messages, in channel(s) "
                       f"{', '.join(x.name for x in channels)} by user(s) "
                       f"{'/'.join(x.display_name for x in users)} with reaction(s) '"
                       f"{'/'.join(reactions)}' for string(s) '{'/'.join(cmd)}'```")
        for channel in ctx.guild.text_channels:
            if channel.id in (x.id for x in channels):
                try:
                    async for msg in channel.history(limit=num):
                        if msg.author.id not in (o.id for o in users):
                            continue
                        if reactions and not set(reactions).intersection((o.emoji for o in msg.reactions)):
                            continue
                        if not cmd or any(x.lower() in msg.content.lower() for x in cmd):
                            msgs.insert(0, f"{msg.author.display_name} ("
                            f"{str(msg.created_at.replace(microsecond=0) - timedelta(hours=5))}): {msg.content}")
                except discord.Forbidden:
                    pass
                msgs.insert(0, f"~~~~ {channel.name.upper()} ~~~~")
        try:
            await ctx.send(content=f"{len(msgs) - len(channels)} messages found.",
                           file=discord.File(io.BytesIO('\n'.join(msgs).encode()),
                                             filename=f"{str(ctx.message.created_at.replace(microsecond=0) - timedelta(hours=5))}-dump.txt'"))
        except discord.HTTPException:
            await ctx.send('Error: Dump file too large')

    @commands.command(description = "<moji> ~ Play a moji",
            usage = "\n\t-l : List mojis\n\t-a <name> <link> : Add a moji\n\t-r <name> : Remove a moji")
    async def moji(self, ctx, *args):
        args = list(args)
        mojis = self.storage.read('mojis')
        
        if '-l' in args:
            await ctx.send('```Available mojis:\n' + '\n'.join(mojis) + '```')

        elif '-a' in args:
            name = args[args.index('-a') + 1]
            mojis[name] = args[args.index('-a') + 2]
            self.storage.write('mojis', mojis)
            await ctx.send(f"Moji {name} successfully added")

        elif '-r' in args:
            name = args[args.index('-r') + 1]
            del mojis[name]
            self.storage.write('mojis', mojis)
            await ctx.send(f"Moji {name} successfully removed")

        elif args: 
            if args[0] in mojis:
                await ctx.send(mojis[args[0]])
            else:
                await ctx.send(f"Moji '{args[0]}' not found")
        else:
            await ctx.send('```Available mojis:\n' + '\n'.join(mojis) + '```')

    @commands.command(description = "<# days|hours|minutes ...> ~ Set a reminder",
            usage = "\n\t-l : List reminders\n\t-u <@user (self)> : Specify user to be reminded")
    async def reminder(self, ctx, *cmd):
        cmd = list(cmd)
        rem_index = 1
        rem_date = datetime.now().replace(second=0, microsecond=0)
        if '-l' in cmd:
            printlist = 'Reminders:\n'
            for x in self.storage['reminders']:
                printlist += f"{x}:\n"
                for y in self.storage['reminders'][x]:
                    printlist += f"\t{y} : {str(self.storage['reminders'][x][y])}\n"
            await ctx.send(f"```{printlist}```")
            return
        if '-u' in cmd:
            rem_user = cmd.pop(cmd.index('-u') + 1)
            cmd.remove('-u')
        else:
            rem_user = ctx.author.mention
        if 'days' or 'hours' or 'minutes' in cmd:
            try:
                rem_date += timedelta(days=int(cmd.pop(cmd.index('days') - 1)))
                cmd.remove('days')
            except ValueError:
                pass
            try:
                rem_date += timedelta(hours=int(cmd.pop(cmd.index('hours') - 1)))
                cmd.remove('hours')
            except ValueError:
                pass
            try:
                rem_date += timedelta(minutes=int(cmd.pop(cmd.index('minutes') - 1)))
                cmd.remove('minutes')
            except ValueError:
                pass
        else:
            await ctx.send('Error: Must include time formatting')

        for x in self.storage['reminders']:
            if int(x) + 1 not in self.storage['reminders']:
                rem_index = int(x) + 1
                break
        
        new_reminder = {
            'user': rem_user,
            'date': str(rem_date),
            'reminder': ' '.join(cmd),
            'channel': ctx.message.channel.id
        }
        reminders = self.storage.read('reminders')
        reminders[rem_index] = new_reminder
        self.storage.write('reminders', reminders)
        await ctx.send(f"Reminder '{' '.join(cmd)}' added for {rem_date}")

    @commands.command(description = "<options> ~ Store and retrieve files from TonyCloud",
            usage = "\n\t-l : List files\n\t-s [messageID (current) ...] : Specify message(s) to pull files from\n\t-g <#> : Get file at specified index")
    async def discloud(self, ctx, *cmd):
        cmd = list(cmd)
        path = os.path.join(ROOTPATH, 'discloud')
        if '-l' in cmd:
            liststring = ""
            for num, val in enumerate(os.listdir(path)):
                liststring += f"{num + 1} - {val}\n"
            await ctx.send(f"```{liststring}```")
            return

        if '-s' in cmd:
            cmd.remove('-s')
            msgs = []
            if not cmd:
                msgs.append(ctx.message)
            else:
                for mID in cmd:
                    msgs.append(await ctx.get_message(mID))
            for msg in msgs:
                for attachment in msg.attachments:
                    await attachment.save(os.path.join(path, attachment.filename))
                    await ctx.send(f'File "{attachment.filename}" stored')

        if '-g' in cmd:
            cmd.remove('-g')
            if not cmd:
                await ctx.send('Please specify file(s) by index (i.e. "1 2 4 5")')
            else:
                files = []
                for data in cmd:
                    data = int(data) - 1
                    files.append(discord.File(open(os.path.join(path, os.listdir(path)[data]), 'rb'),
                                              filename=os.listdir(path)[data]))
                try:
                    message = await ctx.send(content='```Warning, file(s) will be deleted in 5 minutes.```',
                                             files=files)
                    await asyncio.sleep(300)
                    await message.delete()
                except IndexError:
                    await ctx.send('Error: Index not found')


async def check_reminder(bot, storage):
    reminders = storage.read('reminders')
    for x in list(reminders):
        if str(datetime.now().replace(second=0, microsecond=0)) >= reminders[x]['date']:
            rem = reminders.pop(x)
            storage.write('reminders', reminders) #note: putting any awaits before this write could corrupt storage
            await bot.get_channel(rem['channel']).send(rem['user'] + ' - ' + rem['reminder'])


def is_num(s):
    try:
        int(s)
    except ValueError:
        return False
    return True


async def lego_background(bot, storage):
    print('lego background process started')
    while bot.ws is None:
        await asyncio.sleep(1)
    while True:
        await check_reminder(bot, storage)
        await asyncio.sleep(15)



def setup(bot):
    storage = LegoStore()
    bot.add_cog(LegoFuncs(bot, storage))
    bot.loop.create_task(lego_background(bot, storage))
