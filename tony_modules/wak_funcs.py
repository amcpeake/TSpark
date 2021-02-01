# A file containing all of wak's functions for tony spark
# Might be broken into a bunch of files if the bot gets bloated
import discord
from discord.ext import commands
import requests
import random
import re
import discord
import asyncio
from .storage import \
    JSONStore  # relative import means this wak_funcs.py can only be used as part of the tony_modules package now
import os
from pathlib import Path
import io
import json

ROOTPATH = os.environ['TONYROOT']  # Bot's root path
STORAGE_FILE = os.path.join(ROOTPATH, 'storage', 'wak_storage.json')


class WakStore(JSONStore):
    def __init__(self):
        super().__init__(STORAGE_FILE)
        if self['playables'] is None:  # init playables so I don't have to keep checking if they're None
            self['playables'] = []
        if self['lambdas'] is None: # init lambdas
            self['lambdas'] = {}


class WakFuncs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="eval", description = "<code> ~ Execute arbitary code")
    async def execute(self, ctx, *, cmd):  # if cmd arg is keyword only it lets discordpy know to pass in args as one string
        import random  # import locally because I don't want eval to have global namespace
        import math
        import re
        try:
            return_val = str(eval(cmd, locals()))  # only executes expressions, not statements.
            # ALSO: FOR SOME UNGODLY REASON eval WILL NOT CONSERVE locals IF YOU HAVE NESTED SCOPE
            # ie, eval("[math.sin(x) for x in range(10)]", None, locals()) WILL FAIL BECAUSE WHEN YOU DO LIST COMPREHENSION YOU CREATE A NESTED SCOPE, AND FOR SOME REASON THAT NESTED SCOPE IS EMPTY. IT DOESN'T CONTAIN locals
            # BUT NOTICE THAT THIS WILL ONLY BREAK FOR LOCAL SCOPE. SO ALL YOUR VARIABLES HAVE TO BE DEFINED IN GLOBAL SCOPE
            # THAT'S WHY IM PASSING IN locals() WHERE IM SUPPOSED TO BE PASSING IN globals()!!!!!!
            # ALSO BE AWARE THAT WHEN YOU USE eval OUTSIDE OF A FUNCTION AND DON'T SPECIFY ANY SCOPE PARAMS IT'LL USE THE CORRECT LOCAL AND GLOBAL SCOPES BY DEFAULT, AND LOCAL SCOPE WILL BE EQUAL TO GLOBAL SCOPE SO IT'LL ALL WORK OUT
            # THIS MEANS THAT I ALSO COULD HAVE IMPORTED THE MODULES OUTSIDE OF THE FUNCTION AND PASSED NO PARAMS INTO eval, HOWEVER THEN ALL MY GLOBALS WOULD BE AVAILABLE IN THE CALL TO eval WHICH WOULD BE A BIT OF A MESS
        except BaseException as e:
            return_val = "{}: {}".format(e.__class__.__name__, e)
        if len(return_val) > 2000:
            await ctx.send("Sorry, the return value's too long to send")
        else:
            await ctx.send(return_val)

    @commands.command(aliases=['image'], description = "<search term> ~ Search Google images")
    async def img(self, ctx, *args):
        await self.send_image(ctx, args)

    async def send_image(self, ctx, words):
        query = '+'.join(words) + '&source=lnms&tbm=isch'
        url = 'https://www.google.ca/search?q=' + query
        data = requests.get(url).content.decode(errors='ignore')
        imgs = re.findall(r'src="(https?://(?:encrypted-tbn0|t0)\.gstatic\.com/images.+?)"', data)
        if len(imgs) == 0:
            await ctx.send('No images found')
        else:
            embed = discord.Embed()
            embed.set_image(url=random.choice(imgs))
            await ctx.send(embed=embed)

    @commands.command(description = "<game> ~ Add a game for tony to play")
    async def play(self, ctx, *, game):
        if len(game) <= 128:
            playables = self.bot.wstorage.read('playables')
            playables.append(game)
            self.bot.wstorage.write('playables', playables)
            await self.bot.change_presence(activity=discord.Game(name=game))
            await ctx.send('added playable')
        else:
            await ctx.send("Playable wasn't added because it was > 128 chars long")

    @commands.command(description = "~ Get all messages from current channel")
    async def history(self, ctx, *args):
        await ctx.send("Reading all messages in this channel (might take a while)...")
        all_msgs = []
        async for msg in ctx.history(
                limit=None):  # reverse = True doesn't reverse message order properly so I have reverse the order myself
            new_bytes = msg.author.display_name.encode() + b': ' + msg.content.encode()  # also the reason I'm building a list is because I don't think there's any way to use an async generator as a regular generator (ie, do something like (b'\n'.join(all_msgs) )
            all_msgs.insert(0, new_bytes)  # USE insert() TO PREPEND TO LISTS EFFICIENTLY
        pseudo_file = io.BytesIO(b'\n'.join(
            all_msgs))  # WOULD BE NICE TO JUST DO pseuo_file.write() INSTEAD OF all_msgs.insert BUT MESSAGES HAVE TO BE REVERSED SO THIS IS PROBABLY THE BEST I CAN DO
        message = "Found {} messages".format(len(all_msgs))  # len apparently constant time for lists
        await ctx.send(message, file=discord.File(pseudo_file, filename="dump.txt"))

    @commands.command(description = "<game> ~ Remove a game from Tony's list")
    async def unplay(self, ctx, *, cmd):
        playables = self.bot.wstorage['playables']
        if cmd in playables:
            playables.remove(cmd)
            self.bot.wstorage.write('playables', playables)
            if ctx.guild is not None and ctx.guild.me.activity.name not in playables:  # ctx.guild is None if in DMs
                await play_random_playable(self.bot)
            await ctx.send("removed playable")
        else:
            await ctx.send("Couldn't find playable: " + cmd)
    
    @commands.command(aliases=['jif'], description = "<search terms> ~ Search Tenor for gifs")
    async def gif(self, ctx, *args):
        await self.send_gif(ctx, args)
    
    async def send_gif(self, ctx, words):
        endpoint = "https://api.tenor.com/v1/search?q={search}&key={api_key}&limit=5" # limit search to 5 gifs
        msg = ' '.join(words) # join the words together before parsing out punctuation so that empty words don't count as a word (unless there are no words at all)
        msg = re.sub('[.;,!]', '', msg) # remove punctuation from msg (EVEN IF MSG IS 100% PUNCTUATION EVERYTHING WORKS, this is because ''.split(' ') will become [''] which will then search tenor for nothing, which just gets back trending gifs or something so it's fine)
        words = msg.split(' ')
        num_search_terms = len(words)
        if num_search_terms > 3: # max 3 search terms
            num_search_terms = 3
        words.sort(key=len, reverse=True) # sort words from longest to shortest
        for num_words in range(num_search_terms, 0, -1):
            search_words = words[0: num_words]
            search_term = ' '.join(search_words)
            api_key = self.bot.config['API_KEYS']['TENOR']
            res = requests.get(endpoint.format(search=search_term, api_key=api_key)).json()
            results = res['results']
            if len(results) > 0:
                gif = random.choice(results)
                await ctx.send(gif['url'])
                break
            print("no results for '{}'".format(search_term))


    @commands.Cog.listener()
    async def on_message(self, mess):
        if mess.author.id != self.bot.user.id:

            # godworld spam
            if mess.channel.id == self.bot.config['CHANNEL_IDS']['GOD_WORLD'] and not mess.content.startswith('http'):
                spam_func = random.choice([self.send_image, self.send_gif])
                await spam_func(mess.channel, mess.content.split(' '))

            else:
                roll = random.randint(1, self.bot.config['TENOR_CHANCE'])
                if roll == 1:
                    await self.send_gif(mess.channel, mess.content.split(' '))


    @commands.command(description = "<search terms> ~ Search Wikipedia")
    async def wiki(self, ctx, *, query):
        query = query.replace(' ', '_')
        response = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}")
        if response.ok:
                data = json.loads(response.content)
                data_type = data['type']
                if data_type == "standard":
                    msg = discord.Embed(
                        title=data['title'] if 'title' in data else None,
                        description=data['description'] if 'description' in data else None,
                        url=data['content_urls']['desktop']['page'] if 'content_urls' in data else None,
                        color=16777215
                    )
                    if 'extract' in data:
                        msg.set_footer(text=data['extract'])
                    if "thumbnail" in data:
                        msg.set_image(url=data["thumbnail"]["source"])
                    await ctx.send(embed=msg)
                elif data_type == "disambiguation":
                    await ctx.send("you'll have to be more specific")
                else:
                    await ctx.send(f"weird error: got the following data_type: {data_type}")
        else:
            await ctx.send("no results found")
    

    @commands.command(description = "~ Display Ontario COVID-19 data")
    async def covid(self, ctx, *args):
        api_url = "https://api.ontario.ca/api/drupal/page%2F2019-novel-coronavirus?fields=nid,field_body_beta,body"
        response = requests.get(api_url)
        if not response.ok:
            await ctx.send(f"error: ontario api returned a {response.status_code} status code")
            return
        data = response.content.decode()

        base_regex = ".+?(\d+)</t"
        fields = {
            "Infected": re.search(f"Confirmed positive{base_regex}", data),
            "Dead": re.search(f"Deceased{base_regex}", data),
            "Under Investigation": re.search(f"Currently under investigation{base_regex}", data),
            "Negative Tests": re.search(f"Negative{base_regex}", data)
        }

        msg = discord.Embed(title="Ontario Covid Stats")
        for name, match in fields.items():
            value = match[1] if match is not None else "PARSING ERROR"
            msg.add_field(name=name, value=value, inline=False)

        await ctx.send(embed=msg)
    

    @commands.command(
        name="lambda",
        description="[action] [lambda name] [code] [input] ~ Create and run python scripts",
        usage = "\n\t<lambda name> <code> : Create a new lambda\n\t<lambda name> [input] : Execute a lambda with input\n\tdelete <lambda name> : Deletes the lambda\n\tsource <lambda name> : Prints a lambda's source code\n\tlist : Lists all existing lambdas\n\tInside a lambda the following variables are available:\n\t\tprint: A function to print to discord\n\t\targs: The input passed to this lambda\n\t\tfiles: A list of files attached to the message that called the lambda\n\t\tmessage: The discord message that called the lambda"
    )
    async def user_command(self, ctx, *, text):
        split = re.split(r'[ \n]+', text, 1) # command and args are seperated by at least one space or newline or both
        command = split[0]
        args = '' if len(split) == 1 else split[1]
        lambdas = self.bot.wstorage['lambdas']

        # check if command is valid (useful for if you accidently do !lambda ```code``` or something)
        if not command.isidentifier():
            await ctx.send(f'"{command}" is not a valid lambda name (must be a valid Python identifier)')

        # delete lambda
        elif command == 'delete':
            lambda_name = args
            if lambda_name in lambdas:
                del lambdas[lambda_name]
                self.bot.wstorage.write('lambdas', lambdas)
                await ctx.send(f"deleted {lambda_name}")
            else:
                await ctx.send(f"can't delete {lambda_name} (no lambda with that name found)")
        
        # get source code for lambda
        elif command == 'source':
            lambda_name = args
            if lambda_name in lambdas:
                code = lambdas[lambda_name]
                await ctx.send(f"```py\n{code}```")
            else:
                await ctx.send(f"can't get source code for {lambda_name} (no lambda with that name found)")
        
        # list all lambdas
        elif command == 'list':
            lambda_list = ', '.join(lambdas.keys())
            await ctx.send(lambda_list if lambda_list else "there are currently no lambdas")
        
        # execute a lambda
        elif command in lambdas:

            send_calls = [] # need to keep track of calls to ctx.send so pipes work (basically piping works by checking what was sent to ctx.send after awaiting user_command. BUT asyncio.ensure_future only *schedules* the corutine, it has no way of waiting for its completion like await does. And scheduled corutines cannot run until we hand program exectution back to asyncio (via returning from an awaited corutine or awaiting a corutine). and so, since the rest of this code (including exec) is synchronous, if we used asyncio.ensure_future there would actually be no way for ctx.send calls to run until we return from user_command. This would result in a race condition in asyncio where either it has to choose between running the rest of the pipe code (that's currently awaiting user_command) or running the scheduled ctx.sends (and the pipe code seems to win the race every time). Luckily there is an easy solution: instead of scheduling the ctx.send calls, keep track of all of them and then await them all before exiting this function)
            def send(*args, **kwargs):
                call = ctx.send(*args, **kwargs)
                send_calls.append(call) # don't actually schedule ctx.send calls yet (wait until we can await them all)

            files = [
                await attachment.to_file() 
                for attachment in ctx.message.attachments
            ]
            environment = {'print': send, 'args': args, 
                'files': files, 'message': ctx.message}

            exec(lambdas[command], environment)
            for coro in send_calls: # run all ctx.send calls and wait for them all to finish before returning (so pipes work)
                await coro # using a for loop instead of asyncio.wait because asyncio.wait doesn't maintain order of execution
        
        # lambda doesn't exist yet
        else:
            matched_code = re.match(
                r"^```(?:py)?(?P<code>.+)```$", 
                args,
                re.DOTALL
            )

            # create a new lambda if user sent code
            if matched_code is not None:
                lambdas[command] = matched_code.group('code')
                self.bot.wstorage.write('lambdas', lambdas)
                await ctx.send(f"new lambda `{command}` created")

            # don't know what to do, assume user was trying to execute a lambda
            else:
                await ctx.send(f"can't run {command} (no lambda with that name found)")



async def play_random_playable(bot):
    playables = bot.wstorage['playables']
    if len(playables) > 0:
        new_game = discord.Game(name=random.choice(playables))
        await bot.change_presence(activity=new_game)
    else:
        await bot.change_presence(activity=None)


async def background(bot):
    print('wak background process started')
    while bot.ws is None:  # wait until ws connection is made (there is a short period of time after bot.run is called during which the event loop has started but a discord websocket hasn't been established)
        await asyncio.sleep(1)
    while True:
        await play_random_playable(bot)
        await asyncio.sleep(int((random.random() + 0.2) * 30 * 60))  # add 0.2 so minimal time isn't 0


def setup(bot):
    bot.add_cog(WakFuncs(bot))
    bot.wstorage = WakStore()
    bot.loop.create_task(background(bot))
