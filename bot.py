import yfinance as yf
import mplfinance as mpf
import pandas as pd
import discord
import datetime
import config
import asyncio
from PIL import Image
import matplotlib.pyplot as plt
class StockBot:
    def __init__(self):
        self.stock_symbols = config.STOCK_SYMBOLS
        self.support_levels = {}
        self.resistance_levels = {}
        self.current_time = datetime.datetime.now().isoformat()

    def get_stock_data(self, stock_symbol, period="1mo"):
        stock_data = yf.download(stock_symbol, period=period, interval="1h")
        return stock_data

    def calculate_relative_volume(self, stock_data):
        average_volume = stock_data["Volume"].mean()
        relative_volume = stock_data["Volume"] / average_volume
        return relative_volume

    def calculate_support_resistance(self, stock_data, lookback_period=30):
        historical_data = stock_data.tail(lookback_period)
        support_level = historical_data["Low"].min()
        resistance_level = historical_data["High"].max()
        return support_level, resistance_level

    def is_breakout_or_breakdown(self, stock_data, support, resistance):
        latest_close = stock_data['Close'].iloc[-1]
        momentum = abs(((stock_data["Adj Close"].iloc[-1] - stock_data["Adj Close"].iloc[-16]) / stock_data["Adj Close"].iloc[-16])) * 100
        volume = self.calculate_relative_volume(stock_data).iloc[-1]
        if latest_close > resistance:
            color = 0x00ff00
            return True, "Breakout", color, momentum, volume, "Resistance", resistance
        elif latest_close < support:
            color = 0xff0000
            return True, "Breakdown", color, momentum, volume, "Support", support
        else:
            color = 0x4d5d53
            return False, "No potential breakout or breakdown", color, momentum, volume, "Support & Resistance", support # It's for test if the bot work.

    def plot_stock(self, stock_data, breakdown_or_breakout):
        relative_volume = self.calculate_relative_volume(stock_data)
        relative_volume_series = pd.Series(relative_volume, index=stock_data.index)

        STYLE_DICT = {
            "xtick.color": "w",
            "ytick.color": "w",
            "xtick.labelcolor": "w",
            "ytick.labelcolor": "w",
            "axes.labelcolor": "w",
            "axes.labelsize": 15,
            "axes.titlesize": 15,
            "xtick.labelsize": 16,
            "ytick.labelsize": 16
        }

        mc = mpf.make_marketcolors(up='#06d881', down='#f74565', inherit=True)
        custom_style = mpf.make_mpf_style(base_mpf_style='nightclouds', gridstyle="", edgecolor="#2f3137", facecolor="#2f3137", figcolor="#2f3137", marketcolors=mc, rc=STYLE_DICT)

        addplot_volume = mpf.make_addplot(relative_volume_series, panel=1, type='bar', color="#5c616a", ylabel="Volume (M)", width=0.2)

        fig, axlist = mpf.plot(stock_data, type='candle', style=custom_style, addplot=[addplot_volume], returnfig=True, xrotation=0, mav=(9, 20), figratio=(48, 24))

        watermark_img = Image.open(config.icon)
        watermark_width = int(watermark_img.width * 0.2)
        watermark_height = int(watermark_img.height * 0.2)
        watermark_img = watermark_img.resize((watermark_width, watermark_height))
        watermark_pos_x = int(fig.bbox.width * 0.1)
        watermark_pos_y = int(fig.bbox.height * 0.1)
        fig.figimage(watermark_img, xo=watermark_pos_x, yo=watermark_pos_y, origin='upper', alpha=0.8)

        support, resistance = self.calculate_support_resistance(stock_data)
        if breakdown_or_breakout == "Breakout":
            axlist[0].axhline(resistance, color="w", linestyle="--")
        elif breakdown_or_breakout == "Breakdown":
            axlist[0].axhline(support, color="w", linestyle="--")
        else:
            axlist[0].axhline(resistance, color="w", linestyle="--")
            axlist[0].axhline(support, color="w", linestyle="--")

        axlist[2].yaxis.set_major_locator(plt.MaxNLocator(nbins=3))

        newxticks = []
        newlabels = []
        format = '%b %d'

        for xt in axlist[0].get_xticks():
            p = int(xt)
            if p >= 0 and p < len(stock_data):
                ts = stock_data.index[p]
                newxticks.append(p)
                newlabels.append(ts.strftime(format))

        newxticks.append(len(stock_data)-1)
        newlabels.append(stock_data.index[len(stock_data)-1].strftime(format))
        axlist[0].set_xticks(newxticks)
        axlist[0].set_xticklabels(newlabels)
        axlist[0].yaxis.tick_left()
        axlist[0].yaxis.set_label_position("left")

        axlist[0].get_lines()[0].set_color('#6d7077')
        axlist[0].get_lines()[1].set_color('#3f4349')

        plt.gcf().set_size_inches(20, 10)
        plt.savefig('chart.png', bbox_inches='tight', pad_inches=0.5)

    async def start_stock_analysis(self, client):
        while True:
            for symbol in self.stock_symbols:
                stock_data = self.get_stock_data(symbol)
                if symbol not in self.support_levels or symbol not in self.resistance_levels:
                    support, resistance = self.calculate_support_resistance(stock_data)
                    self.support_levels[symbol] = support
                    self.resistance_levels[symbol] = resistance

                response, breakdown_or_breakout, color, momentum, relative, resistance_or_support, level = self.is_breakout_or_breakdown(stock_data, self.support_levels[symbol], self.resistance_levels[symbol])

                if response:
                    support, resistance = self.calculate_support_resistance(stock_data)
                    self.plot_stock(stock_data, breakdown_or_breakout)

                    chart_path = config.icon
                    thumbnail_path = config.icon

                    embed = discord.Embed(description=f'Potential **{symbol}** {breakdown_or_breakout} on **Hourly chart**', color=color)
                    embed.set_author(name=f'{symbol} Stock {breakdown_or_breakout}')
                    if momentum >= 5:
                        embed.add_field(name='Momentum :bulb:', value=f'{round(momentum, 2)}')
                    else:
                        embed.add_field(name='Momentum', value=f'{round(momentum, 2)}')

                    if relative >= 2:
                        embed.add_field(name='Relative Volume :medal:', value=f'{round(relative, 2)}')
                    else:
                        embed.add_field(name='Relative Volume', value=f'{round(relative, 2)}')

                    embed.add_field(name=f"{resistance_or_support} Level", value=f'{round(level, 2)}')

                    chart_file = discord.File(chart_path, filename='chart.png')
                    embed.set_image(url=f'attachment://chart.png')

                    thumbnail_file = discord.File(thumbnail_path, filename=config.icon)
                    embed.set_thumbnail(url=f'attachment://{config.icon}')

                    channel = client.get_channel(config.CHANNEL_ID)
                    await channel.send(embed=embed, files=[chart_file, thumbnail_file])

                    self.support_levels[symbol] = support
                    self.resistance_levels[symbol] = resistance

            await asyncio.sleep(900)
