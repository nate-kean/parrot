import re


markdown = re.compile(r"[*_`~]")
discord_string_start = re.compile(r"[<@:]")
# Matches a mention or a URL
do_not_text_modify = re.compile(r"(^<.*>$)|(^.+:\/\/.+$)")
snowflake = re.compile(r"[^0-9]")
