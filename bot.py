import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv 

import CONFIG

from datetime import datetime, timedelta
import pandas
from pandas_datareader import data as pdr
import yfinance as yfin
yfin.pdr_override()

import matplotlib.pyplot as plt
import asyncio

from newsapi import NewsApiClient
from bs4 import BeautifulSoup
import requests

DISCORD_TOKEN = CONFIG.VARIABLES['DISCORD_TOKEN']

NEWSAPI_TOKEN = CONFIG.VARIABLES['NEWSAPI_TOKEN']
newsapi = NewsApiClient(api_key=NEWSAPI_TOKEN)

bot = commands.Bot(command_prefix='!')
daily_news_dict = set()

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    
@bot.command(name="graph", help="Returns a trading view link of a given stock")
async def graph(ctx, quo="msft"):
    response = "https://www.tradingview.com/symbols/" + quo
    await ctx.send(response)

def get_news(source="bbc-news"):
    top_headlines = newsapi.get_top_headlines(sources=source)
    news_articles = top_headlines['articles']
    print(news_articles)
    embed = discord.Embed(
        title = 'News',
        colour = discord.Colour.green()
    )
    embed.set_footer(text="News from " + source)
    for l in news_articles:
        embed.add_field(name=l["title"], value=l["description"], inline=False)
        embed.add_field(name=l["url"], value=l["publishedAt"], inline=False)
    return embed


@tasks.loop(hours=24)
async def called_once_a_day():
    URL = "https://finance.yahoo.com/quote/^QMI"
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, "html.parser")
    premarket = ""
    try:
        current_price = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[0]
        change = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[1]
        premarket = "NASDAQ 100 Pre Market\t" + current_price.text + "\t" + change.text
    except:
        premarket = "No data found"

    for guild in bot.guilds:
        for channel in guild.channels:
            unique_id = str(guild) + '$' + str(channel)
            if unique_id in daily_news_dict:
                print(unique_id in daily_news_dict)
                try:
                    embed = get_news()
                    await channel.send(embed = embed)
                    await channel.send(premarket = premarket)
                except Exception:
                    continue


@called_once_a_day.before_loop
async def before():
    tomorrow = datetime.now() + timedelta(1)
    tomorrow_morning = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=6, minute=0, second=0)
    time_left = (tomorrow_morning - datetime.now()).seconds

    await asyncio.sleep(time_left)
    await bot.wait_until_ready()

def write_to_file(filename, text):
    file = open(filename, 'w')
    file.write(text)
    file.write("\n")
    file.close()

@bot.command(name="set_daily_news", help="Sets the current channel to receive daily news update")
async def set_daily_news(ctx):
    unique_id = str(ctx.guild) + '$' + str(ctx.channel)
    daily_news_dict.add(unique_id)
    embed = discord.Embed(title="comfirmation", description="Your daily news update is confirmed for the current channel.", color=discord.Color.blue())
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

    write_to_file("daily_news_ids.txt", unique_id)

    await ctx.send(embed = embed)

def get_data(stock, start_date, end_date):
    for retries in range(0, 5):
        try:
            df = pdr.get_data_yahoo(stock, start=start_date, end=end_date)
            return df['Adj Close']
        except:
            print("[ERROR")
            print('yfinance JSONDecodeError, retrying: ' + str(retries))
            print('ticker: ' + stock + 'start: ' + str(start_date) + ';end: ' + str(end_date) + ';')
    return []


@bot.command(name='chart', help='Returns the stock performance of a given stock symbol over a period of 2 years.')
async def chart(ctx, quo="msft"):

    print("[HERE]")
    now = datetime.now()

    old_year = now.year - 2
    current_date = datetime.today().strftime('%Y-%m-%d')
    current_date_arr = current_date.split('-')
    old_date = str(old_year) + '-' + current_date_arr[1] + '-' + current_date_arr[2]

    data = get_data(quo, old_date, current_date)
    # Clears the graoh before creating a new one
    plt.clf()

    # Plots the graph and stores it in a variable
    plot = data.plot(title='Stock Price over 2 years')
    fig = plot.get_figure()
    filename = 'output.png'
    fig.savefig(filename)
    await ctx.send(file=discord.File(filename))

def read_and_update_daily_news_dictionary():
    try:
        file = open("daily_news_ids.txt", "r")
        lines = file.readlines()

        for line in lines:
            stripped_line = line.rstrip()
            daily_news_dict.add(stripped_line)
    except Exception:
        print("No such file exists at the moment")
    return 

'''
(The blocks of codes below do not work) 

@bot.command(name='price', help='Returns the current price and percent change of a given stock.')
async def price(ctx, quo="msft"):
    URL = "https://finance.yahoo.com/quote/" + str(quo)
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, "html.parser")
    try:
        current_price = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[0]
        change = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[1]
        await ctx.send(quo.upper() + "\t" + current_price.text + "\t" + change.text)
    except:
        await ctx.send("No data found")


@bot.command(name='profile', help='Returns the profile/about info of a given stock.')
async def profile(ctx, quo="msft"):
    URL = "https://finance.yahoo.com/quote/" + quo.lower() + "/profile"
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, "html.parser")
    try:
        profile = soup.find_all("section", {"class": "quote-sub-section Mt(30px)"})[0].find_all("p")[0].text
        await ctx.send(profile)
    except:
        await ctx.send("No data found")

@bot.command(name='triple', help='Returns the current price and percent change of the three major index (NASDAQ, DJI, and S&P 500).')
async def triple(ctx):
    channel = ctx.message.channel
    embed = discord.Embed(
        title = 'Triple Index',
        colour = discord.Colour.blue()
    )

    embed.set_footer(text="Data from Yahoo Finance")
    await ctx.send("Searching for data...")

    three = [["NASDAQ", "^ixic"], ["DJI", "^dji"], ["S&P 500", "^gspc"]]
    indexname = ""
    indexprice = ""
    indexchange = ""
    for i in range(3):
        URL = "https://finance.yahoo.com/quote/" + three[i][1]
        page = requests.get(URL)
        soup = BeautifulSoup(page.text, "html.parser")
        try:
            current_price = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[0]
            change = soup.find_all("div", {"class":"My(6px) Pos(r) smartphone_Mt(6px)"})[0].find_all("span")[1]
            indexname += three[i][0] + "\n"
            indexprice += current_price.text + "\n"
            indexchange += change.text + "\n"
        except:
            indexname += three[i][0] + "\n"
            indexprice += "No data found\n"
            indexchange += "No data found\n"

    embed.add_field(name="Index", value=indexname, inline=True)
    embed.add_field(name="Price", value=indexprice, inline=True)
    embed.add_field(name="Change", value=indexchange, inline=True)
        
    await ctx.send(embed=embed)
'''

@bot.command(name="news", help="Returns (usually 10) headline news from a given source. Default is bbc-news.")
async def news(ctx, source="bbc-news"):
    await ctx.send("Searching for news...")
    embed = get_news(source)
    await ctx.send(embed=embed)

@bot.command(name="snews", help="Returns the headline news of a given stock symbol.")
async def snews(ctx, quo="msft"):
    top_headlines = newsapi.get_everything(q=quo)
    news_articles = top_headlines['articles']
    embed = discord.Embed(
        title = 'News',
        colour = discord.Colour.green()
    )
    await ctx.send("Searching for news...")

    embed.set_footer(text="News for " + quo.lower())
    for i in range(min(10, len(news_articles))):
        embed.add_field(name=news_articles[i]["title"], value="-", inline=False)
        embed.add_field(name=news_articles[i]["url"], value=news_articles[i]["publishedAt"], inline=False)
    await ctx.send(embed=embed)

read_and_update_daily_news_dictionary()
called_once_a_day.start()
bot.run(DISCORD_TOKEN)