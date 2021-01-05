#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6

import re

ANSI_ROUND = [0, 95, 135, 175, 215, 255]
ANSI_FOREGROUND = re.compile("(?P<begin>%x<#)(?P<hex>[a-fA-F0-9]{6})(?P<end>>)")
ANSI_BACKGROUND = re.compile("(?P<begin>%X<#)(?P<hex>[a-fA-F0-9]{6})(?P<end>>)")
ANSI_CODES = re.compile(r"(?P<ansi>\\033\[[0-9]{2};2;[0-9]{1,3};[0-9]{1,3};[0-9]{1,3}m)")
ANSI_CLEAR_MUSH = re.compile("%xn")
ANSI_CLEAR = '\033[0m'

def hex_parser(hex):
  rgb_hex = [hex[:2], hex[2:4], hex[4:]]
  
  return tuple([int(f"0x{c}", 0) for c in rgb_hex])


def ansi(hex, text, background=False):
  rgb = hex_parser(hex)

  return f'\033[{48 if background else 38};2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}'


def strip_ansi(text):
  return ANSI_CODES.sub("", text)

def re_ansi(match_object):
  if 'x' in match_object.group('begin'):
    return ansi(match_object.group('hex'), '')

  else:
    return ansi(match_object.group('hex'), '', True)


def hex_round(hex):
  rgb_hex = hex_parser(hex)
  rounded_hex = []

  for sub_hex in rgb_hex:
    if sub_hex == 0 or sub_hex == 255:
      rounded_hex.append(sub_hex)
      continue

    value_list = sorted(ANSI_ROUND.copy() + [sub_hex])
    value_index = value_list.index(sub_hex)
    triplet = value_list[value_index - 1:value_index + 2]

    if triplet[1] - triplet[0] >= triplet[2] - triplet[1]:
      rounded_hex.append(triplet[2])

    else:
      rounded_hex.append(triplet[0])

  return "{:02X}{:02X}{:02X}".format(*rounded_hex)


def parse_code(text):
  temp_text = re.sub(ANSI_FOREGROUND, re_ansi, text)
  temp_text = re.sub(ANSI_BACKGROUND, re_ansi, temp_text)

  return re.sub(ANSI_CLEAR_MUSH, ANSI_CLEAR, temp_text)

def colour_gradient(hex_1, hex_2, steps):
  rgb_hex_1 = hex_parser(hex_1)
  rgb_hex_2 = hex_parser(hex_2)
  diffs = [(y - x) / steps for x, y in zip(rgb_hex_1, rgb_hex_2)]
  gradient = []

  for i in range(steps):
    gradient.append("{:02X}{:02X}{:02X}".format(
                       round(rgb_hex_1[0] + diffs[0] * i),
                       round(rgb_hex_1[1] + diffs[1] * i),
                       round(rgb_hex_1[2] + diffs[2] * i)))

  return gradient + [hex_2]


def multi_gradient(colour_scheme, size, smooth=True):
  gradient = []
  i = 0
  hexes = []

  for colour, letters in colour_scheme:
    hexes.extend([colour for _ in range(letters)])

  sub_gradients = len(hexes)
  total_steps = size - 1 if smooth else size
  sub_gradients = sub_gradients - 1 if smooth else sub_gradients

  while total_steps > 0:
    steps = round(total_steps / sub_gradients)

    if smooth:
      gradient.extend(colour_gradient(hexes[i], hexes[i + 1], steps)[:-1])

    else:
      gradient.extend([hexes[i]] * steps)

    total_steps -= steps
    sub_gradients -= 1
    i += 1

  gradient = gradient + [hexes[-1]] if smooth else gradient

  return gradient

def parse_moniker(moniker):
  colour_scheme = []
  name = ""
  temp = moniker[1:].split('%')

  for i in temp:
    raw_fragment = i.split('>', 1)
    hex = raw_fragment[0][3:]
    letters = len(raw_fragment[1])
    name += raw_fragment[1]
    colour_scheme.append((hex, letters))

  return name, colour_scheme

def validate_hex(hex):
  try:
    if len(hex) != 6:
      raise ValueError

    test_hex = hex_parser(hex)

  except ValueError:
    return False

  return True

def title(colour_scheme, text, width, smooth=True):
  gradient = multi_gradient(colour_scheme, width, smooth=smooth)
  buffer = width - len(text)
  title_text = (" " * (buffer // 2)
                + text
                + " " * (buffer - (buffer // 2))
                )

  return (ansi("000000", '')
    + ''.join([ansi(colour, letter, True)
               for colour, letter in zip(gradient, title_text)])
    + ANSI_CLEAR
    + "\n"
    )
