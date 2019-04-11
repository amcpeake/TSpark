import discord
from discord.ext import commands
import requests
import random
import re
import asyncio
from tony_modules.util import \
    JSONStore  # relative import means this wak_funcs.py can only be used as part of the tony_modules package now
import os
import io
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# GLOBAL DEFINITIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ROOTPATH = os.path.join(os.environ['TONYROOT'])   #Bot's root path
STORAGE_FILE = os.path.join(ROOTPATH, 'storage', 'lego_storage.json')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class LegoStore(JSONStore):
    def __init__(self):
        super().__init__(STORAGE_FILE)
        if self['reminders'] is None:
            self['reminders'] = {}


class LegoFuncs:
    def __init__(self, bot, store):
        self.bot = bot
        self.storage = store

    async def on_message(self, message, ):
        if message.guild.id == self.bot.config['SERVER_ID'] and message.channel.id not in self.bot.config['BANNED_CHANNELS'] and message.author.id != self.bot.user.id:
            cur_channel = self.bot.get_channel(message.channel.id)

            if message.channel.id == self.bot.config['VIDEO_ID'] and "http" in message.content:
                await message.add_reaction("👀")

            elif message.channel.id == self.bot.config['MUSIC_ID'] and "http" in message.content:
                await message.add_reaction("👂")

            if 'ai' in re.findall(r'\bai\b', message.content.lower()):
                async with cur_channel.typing():
                    await cur_channel.send('AI...?')
                    await asyncio.sleep(random.randint(30, 50))
                    await cur_channel.send('Just uhhhh...\nhttps://www.youtube.com/watch?v=fUkq2sArNl0&t=57s')

    async def on_reaction_add(self, reaction, user):
        emb = discord.Embed(title=reaction.message.content, colour=reaction.message.author.colour)  # Create embed
        emb.set_author(name=reaction.message.author.display_name + ':', icon_url=reaction.message.author.avatar_url)

        try:
            name = reaction.emoji.name
        except AttributeError:
            pass
        else:
            if reaction.message.attachments:  # If the original message has attachments, add them to the embed
                emb.set_image(url=list(reaction.message.attachments)[0].url)

            if name == 'downvote' and reaction.message.author.id != self.bot.user.id:
                chnl = self.bot.get_channel(513822540464914432)
                await chnl.send(
                    f"**{user.name} has declared the following to be rude, or otherwise offensive content:**",
                    embed=emb)

            elif name == 'upvote' and reaction.message.author.id != self.bot.user.id:
                chnl = self.bot.get_channel(376539985412620289)
                await chnl.send(f"\n\n**{user.name} declared the following to be highly esteemed content:**",
                                embed=emb)

    @commands.command()
    async def joke(self, ctx):  # Tell a joke using the official Chuck Norris Joke API©
        resp = requests.get('https://api.chucknorris.io/jokes/random').json()  # Get the response in JSON
        emb = discord.Embed(title=resp['value'])  # Prepare the embed
        emb.set_author(name='', icon_url=resp['icon_url'].replace('\\', ''))  # Attach icon
        await ctx.send(embed=emb)

    @commands.command()
    async def regedit(self, ctx, *args):
        if len(args) == 0:
            await ctx.send(f'Error: Must provide options or key')

        elif '-l' in args:
            if len(args) == 1:
                await ctx.send(f'Valid registries are: {", ".join(self.bot.config.keys())}')
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
                        if isinstance(self.bot.config[key], list):
                            if isinstance(self.bot.config[key][0], int) and is_num(value):
                                value = is_num(value)
                            self.bot.config[key].append(value)
                            await ctx.send(f'Added {value} to registry {key}')
                        else:
                            await ctx.send(f'Registry must be of type list to add')
                else:
                    await ctx.send(f'Registry {key} is locked. Cannot add {value}')

            else:
                await ctx.send(f'Error: Must provide key to add to and value to add')

        elif args[0] in self.bot.config:
            key = args[0]
            value = args[1]
            if key in self.bot.config['LOCKED']:
                await ctx.send(f'Registry {key} is locked, cannot edit')
            else:
                if isinstance(self.bot.config[key], int) and is_num(value):
                    value = is_num(value)
                await ctx.send(f"Changed {key} from {self.bot.config[key]} to {value}")
                self.bot.config[key] = value

        else:
            await ctx.send(f'Invalid registry "{args[0]}"\nValid registries are: {", ".join(self.bot.config.keys())}')

    @commands.command()
    async def download(self, ctx, *links):
        sesh = requests.Session()
        headerdata = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/64.0.3282.140 Chrome/64.0.3282.140 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7}'
        }
        validsites = ["bandcamp.com", "soundcloud.com"]

        async def get(sesh, url, headerData, parameters=None, maxNumTries = 3):
            if parameters is None:
                parameters = {}
            numTries = 0
            while (numTries < maxNumTries):
                try:
                    return sesh.get(url, params=parameters, headers=headerData)
                except:
                    numTries += 1
            await ctx.send("Failed to get data")
            return

        async def soundcloud(sesh, page, headerdata):
            songs = []
            trackParams = {"client_id": "R05HJlT1Pq49aYbJl7VfKJ587r2blpL1"}
            ids = set(re.findall(r'"id":[0-9]{5,}', page))
            for id in ids:
                trackURL = f"https://api.soundcloud.com/i1/tracks/{str(id)[5:]}/streams"
                infoURL = f"https://api.soundcloud.com/tracks/{str(id)[5:]}?client_id=R05HJlT1Pq49aYbJl7VfKJ587r2blpL1"
                try:
                    mp3URL = await get(sesh, trackURL, headerdata, trackParams)
                    if mp3URL and mp3URL.status_code == 200:
                        mp3 = await get(sesh, mp3URL.json()["http_mp3_128_url"], headerdata)
                        trackinfo = await get(sesh, infoURL, headerdata)
                        songs.append({'title': f'{trackinfo.json()["title"]}.mp3', 'file': mp3.content})
                except KeyError:
                    continue
            return songs

        async def bandcamp(sesh, albumpage, headerdata): # {"album name": "", "album art": f, "files": []}
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
            if not any(site in plink.netloc for site in validsites):
                await ctx.send(f"Error: Invalid site, skipping...\nValid sites:{', '.join(validsites)}")
                continue

            page = await get(sesh, link, headerdata)

            if 'bandcamp' in plink.netloc:
                album = await bandcamp(sesh, page.content.decode('utf-8'), headerdata)
                songs = album['songs']
                await ctx.send(file=discord.File(album['art'], 'albumart.png'))

            elif 'soundcloud' in plink.netloc:
                songs = await soundcloud(sesh, page.content.decode('utf-8'), headerdata)

            else:
                continue

            for song in songs:
                try:
                    await ctx.send(file=discord.File(song['file'], song['title']))
                except discord.errors.HTTPException:
                    await ctx.send("Error, file too large to send...")

        await ctx.send("All done")

    @commands.command()
    async def roll(self, ctx):  # Outputs the message id of the message sent ("roll")
        await ctx.send(f"{ctx.author.display_name} rolled a {ctx.message.id}")

    @commands.command()
    async def nab(self, ctx, *cmds):  # Gets all messages between last two instances of messages with given reaction(s)
        #  DEFAULT VALUES
        cmds = list(cmds)
        emojis = []
        num = 1000
        channel = self.bot.get_channel(ctx.channel.id)
        FLAGS = ['-c', '-n']
        #  FLAG HANDLING
        for cmd in cmds:
            if cmd is '-c':  # Specify the channel to nab from
                channel = self.bot.get_channel(cmd.pop(cmd.index('-c') + 1))
                continue

            if cmd is '-n':  # Specify number of messages to look through
                num = cmd.pop(cmd.index('-n') + 1)
                if is_num(num):  # If
                    num = is_num(num)
                elif num is 'all':
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
            if num_found is 2:
                break
        else:
            await channel.send(f'Error: Two instances of {emojis} not found in last {num} messages')
            return

        await channel.send(file=discord.File(io.BytesIO(msgs), filename='nab.txt'))

    @commands.command()
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
                    users.append(self.bot.get_user(int(re.sub('[<@>]', '', user))))
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
                    num = is_num(num)
                else:
                    await ctx.send('Error: Num value must be "all" or int')
                    return
                cmd.remove('-n')

        if not channels:
            channels.append(ctx.channel)
        if not users:
            users.append(ctx.author)
        await ctx.send(f"```Searching through last {num} messages, in channel(s) {', '.join(x.name for x in channels)} by user(s) {'/'.join(x.display_name for x in users)} with reaction(s) '{'/'.join(reactions)}' for string(s) '{'/'.join(cmd)}'```")
        for channel in ctx.guild.text_channels:
            if channel.id in (x.id for x in channels):
                try:
                    async for msg in channel.history(limit=num):
                        if msg.author.id not in (o.id for o in users):
                            continue
                        if reactions and not set(reactions).intersection((o.emoji for o in msg.reactions)):
                            continue
                        if not cmd or any(x.lower() in msg.content.lower() for x in cmd):
                            msgs.insert(0, f"{msg.author.display_name} ({str(msg.created_at.replace(microsecond=0) - timedelta(hours=5))}): {msg.content}")
                except discord.Forbidden:
                    pass
                msgs.insert(0, f"~~~~ {channel.name.upper()} ~~~~")
        try:
            await ctx.send(content=f"{len(msgs) - len(channels)} messages found.", file=discord.File(io.BytesIO('\n'.join(msgs).encode()), filename=f"{str(ctx.message.created_at.replace(microsecond=0) - timedelta(hours=5))}-dump.txt'"))
        except discord.HTTPException:
            await ctx.send('Error: Dump file too large')

    @commands.command()
    async def moji(self, ctx, opts = '-l', name = '', link = ''):
        mojis = self.storage['mojis']
        if opts == '-l':
            await ctx.send('```Available mojis:\n' + '\n'.join(self.storage['mojis']) + '```')

        elif opts == '-a':
            mojis[name] = link
            self.storage.update()
            await ctx.send(f"Moji {name} successfully added")

        elif opts == '-r':
            del mojis[name]
            self.storage.update()
            await ctx.send(f"Moji {name} successfully removed")

        elif opts in mojis:
            await ctx.send(mojis[opts])

        else:
            await ctx.send(f"Moji '{opts}' not found")
        await ctx.message.delete()

    @commands.command()
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
                rem_date += timedelta(days=is_num(cmd.pop(cmd.index('days') - 1)))
                cmd.remove('days')
            except ValueError:
                pass
            try:
                rem_date += timedelta(hours=is_num(cmd.pop(cmd.index('hours') - 1)))
                cmd.remove('hours')
            except ValueError:
                pass
            try:
                rem_date += timedelta(minutes=is_num(cmd.pop(cmd.index('minutes') - 1)))
                cmd.remove('minutes')
            except ValueError:
                pass
        else:
            await ctx.send('Error: Must include time formatting')

        for x in self.storage['reminders']:
            if int(x) + 1 not in self.storage['reminders']:
                rem_index = int(x) + 1
                break

        self.storage['reminders'][rem_index] = {}
        self.storage['reminders'][rem_index]['user'] = rem_user
        self.storage['reminders'][rem_index]['date'] = str(rem_date)
        self.storage['reminders'][rem_index]['reminder'] = ' '.join(cmd)
        self.storage['reminders'][rem_index]['channel'] = ctx.message.channel.id
        self.storage.update()
        await ctx.send(f"Reminder '{' '.join(cmd)}' added for {rem_date}")

    @commands.command()
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
                    data = is_num(data) - 1
                    files.append(discord.File(open(os.path.join(path, os.listdir(path)[data]), 'rb'), filename=os.listdir(path)[data]))
                try:
                    message = await ctx.send(content='```Warning, file(s) will be deleted in 5 minutes.```', files=files)
                    await asyncio.sleep(300)
                    await message.delete()
                except IndexError:
                    await ctx.send('Error: Index not found')


async def check_reminder(bot, storage):
    reminders = storage['reminders']
    for x in list(reminders):
        if str(datetime.now().replace(second=0, microsecond=0)) >= reminders[x]['date']:
            await bot.get_channel(reminders[x]['channel']).send(reminders[x]['user'] + ' - ' + reminders[x]['reminder'])
            del reminders[x]
            storage.update()


def is_num(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return int(s)


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

