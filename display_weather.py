import requests
import json
import pandas as pd
from epd2in13_V4 import EPD
from PIL import Image, ImageDraw, ImageFont

print('loading weather')

weather_url = "https://api.open-meteo.com/v1/forecast?latitude=39.7392&longitude=-104.9847&hourly=temperature_2m,precipitation,precipitation_probability,wind_speed_10m,wind_direction_10m&timezone=America%2FDenver&wind_speed_unit=mph&temperature_unit=fahrenheit&precipitation_unit=inch"

def get_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON")
        return None
    
weather_json = get_json_from_url(weather_url)
weather_df = pd.DataFrame.from_dict(weather_json['hourly'])
print('loaded weather dataframe, processing...')

weather_df['time'] = pd.to_datetime(weather_df['time'])
weather_df['day_name'] = weather_df['time'].dt.strftime('%a')
weather_df['hour'] = weather_df['time'].dt.hour
weather_df.loc[weather_df['hour'] < 25, 'day_part'] = 'night'
weather_df.loc[weather_df['hour'] < 19, 'day_part'] = 'after work'
weather_df.loc[weather_df['hour'] < 15, 'day_part'] = 'early afternoon'
weather_df.loc[weather_df['hour'] < 12, 'day_part'] = 'morning'
weather_df.loc[weather_df['hour'] < 9, 'day_part'] = 'night'

day_part_df = weather_df.groupby(['day_name', 'day_part']).agg(
    day_start = ('time', 'min'),
    temp_high = ('temperature_2m', 'max'),
    temp_low = ('temperature_2m', 'min'),
    hourly_precip = ('precipitation', 'mean'),
    precip_prob_peak = ('precipitation_probability', 'max'),
    wind_speed_peak = ('wind_speed_10m', 'max'),
    wind_spead_avg = ('wind_speed_10m', 'mean'),
    wind_direction_avg = ('wind_direction_10m', 'mean')
).reset_index().sort_values('day_start').drop('day_start', axis=1)

after_work_df = day_part_df[day_part_df['day_part'] == 'after work']

print('done. creating image...')

x_size = 250
y_size = 122
out = Image.new("RGB", (x_size, y_size), (255, 255, 255))
fnt = ImageFont.truetype("/usr/share/fonts/liberation/LiberationMono-Regular.ttf", 12)
title = ImageFont.truetype("/usr/share/fonts/liberation/LiberationMono-Bold.ttf", 15)
d = ImageDraw.Draw(out)

n_days = 5

for i, row in enumerate(after_work_df.head(n_days).iterrows()):
    row = row[1]
    x_pos = i * x_size / n_days
    d.line(xy=[(x_pos, 0), (x_pos, y_size)], fill=(0,0,0), width=1)

    to_print = ['day_name', 'temp_high', 'temp_low', 'precip_prob_peak', 'wind_spead_avg']
    current_y_pos = 15
    for col in to_print:
        val = row[col]

        if col == 'day_name':
            d.text(xy=(x_pos + (x_size/n_days/2), current_y_pos), text=val, anchor='mt', font=title, fill=(0,0,0))
            current_y_pos += title.size + 5
        else:
            val = str(round(val, 2))
            d.text(xy=(x_pos + (x_size/n_days/2), current_y_pos), text=val, anchor='mt', font=fnt, fill=(0,0,0))
            current_y_pos += fnt.size + 2

out.save('test.png')

print('done. initializing EPD')

epd = EPD()