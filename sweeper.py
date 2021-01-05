#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3.7

# The following sounds have been sampled for this game:
# happyband, "bomb detector.aif" https://freesound.org/people/happyband/sounds/69175/ (sampled into various bomb detector sounds)
# cognito perceptu, "static w lightning tickles" https://freesound.org/people/cognito%20perceptu/sounds/98006/ (used without modification)
# Iwiploppenisse, "Explosion" https://freesound.org/people/Iwiploppenisse/sounds/156031/ (used without modification)

# NOTE: REQUIRES A TERMINAL THAT CAN DO 24-BIT COLOUR, LIKE ITERM2



from shutil import get_terminal_size as spaces
from contextlib  import contextmanager
from random import randint, choice
from itertools import chain
from logging import basicConfig, INFO, WARNING, info, warning
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from ansi import ansi, ANSI_CLEAR


# I'll probably make this more sophisticated later
BOMB_COLOUR         = "AF0000"
FLAG_COLOUR         = "FFFFFF"
SPACE_COLOUR        = "000000"
FIELD_COLOUR        = "70483c"
PLAYER_COLOUR       = "AF5FAF"
PLAYER_FIELD_COLOUR = "4d1b29"
HIGHLIGHT_COLOUR    = "00FF00"

# colour schemes poached from matplotlib, but hardcoded because I'm not loading
# matplotlib just to dynamically generate colour schemes.

# also as the low ends of most of these schemes were very dark, the gradient was
# split into ninths and the extremes omitted.

# also also this only goes up to 7 because a space with 8 bombs around it is an
# enclosure and would be explicitly opened. 7 is the max possible around one space.
COLOUR_SCHEMES = {
  "viridis"   : ["482878",
                 "3e4989",
                 "31688e",
                 "26828e",
                 "1f9e89",
                 "35b779",
                 "6ece58"],

  "plasma"    : ["46039f",
                 "7201a8",
                 "9c179e",
                 "bd3786",
                 "d8576b",
                 "ed7953",
                 "fb9f3a"],

  "inferno"   : ["1b0c41",
                 "4a0c6b",
                 "781c6d",
                 "a52c60",
                 "cf4446",
                 "ed6925",
                 "fb9b06"],

  "magma"     : ["180f3d",
                 "440f76",
                 "721f81",
                 "9e2f7f",
                 "cd4071",
                 "f1605d",
                 "fd9668"],

  "gist_earth": ["133078",
                 "25677d",
                 "368770",
                 "43984d",
                 "7ca753",
                 "aab35c",
                 "c0a565"],

  "CMRmap"    : ["222270",
                 "4326b0",
                 "802f95",
                 "d13a4f",
                 "f35d15",
                 "e69508",
                 "e6c932"],

  "cubehelix" : ["1a1835",
                 "15464e",
                 "2b6f39",
                 "757b33",
                 "c17a70",
                 "d490c6",
                 "c3c1f2"],

  "gnuplot2"  : ["000070",
                 "0000e0",
                 "4200ff",
                 "9a0cf3",
                 "f546b9",
                 "ff7e81",
                 "ffb847"]}

# initialized now, loaded later from user input
COLOURS = []



# dynamically generate the help file in case I add more colour schemes later
colour_scheme_message = "Available colour schemes:\n\n"
schemes = []

for colour in COLOUR_SCHEMES:
  schemes.append(ANSI_CLEAR + colour + ":\n  " + " ".join([ansi(colour, str(i)) for i, colour in enumerate(COLOUR_SCHEMES[colour], 1)]))

colour_scheme_message += "\n\n".join(schemes) + ANSI_CLEAR

argparser = ArgumentParser(epilog=colour_scheme_message, formatter_class=RawDescriptionHelpFormatter)

argparser.add_argument("-m", "--mode", help="Selects a mode (default or soldier).", metavar="<mode>", default="default")
argparser.add_argument("-a", "--area", help="Defines the area of the field. Defaults to the largest size that will fit in the terminal window.", metavar="<int width>x<int height>", default=None)
argparser.add_argument("-c", "--colour", help="Sets the colour scheme of the minefield's numbers (default: gist_earth).", metavar="<name>", default="gist_earth")
BOMBS = argparser.add_mutually_exclusive_group()

BOMBS.add_argument("-b", "--bombs", help="Sets the number of bombs on the field per game. (mutually exclusive with -B)", metavar="<int>", default=0)
BOMBS.add_argument("-B", "--bomb_percent", help="Sets the number of bombs per game as a percentage of spaces on the field. (mutually exclusive with -b, default 0.2)", metavar="<float between 0-1>", default=0.2)



# various signalling exceptions -- throwing an exception is the easiest way
# to break out of multiple loops and/or function definitions quickly

class Lose_Condition(Exception):
  pass

class Win_Condition(Exception):
  pass

class Adjustment(Exception):
  pass

class Game_End(Exception):
  pass


# Minesweeper: Grimdark Edition
MELANCHOLY = [
  "You step over a body.",
  "Crows circle overhead, watching you with morbid curiosity.",
  "You think about your loved ones.",
  "The incessant beeping of the metal detector makes your ears ring.",
  "A crater marks the location of a mine you won't have to dig up.",
  "You wonder what was so important about this piece of land.",
  "You try to remember what this conflict is even about.",
  "You think back to the last time the idea of death bothered you.",
  "You don't want to be here. Then again, neither did most of the corpses.",
  "You squint in the glare of the sun.",
  "The crows settle in a tree, as if awaiting a show.",
  "It gets harder to reason about mine placements over time.",
  "How many mines are left? {mines}? {mines} too many.",
  "You wonder if the general of this theatre has ever had to do this.",
  "You hear a distant explosion, and pray that it wasn't the poor guy a field over.",
  "Are you sure these are all in the right place?",
  "You step over what you're pretty sure was a body.",
  "It's incredibly difficult to keep your concentration.",
  "You have to be right {mines} more times. You only have to be wrong once.",
  "The ground is soft and pliant under your boots.",
  "You stop to take a drink of water, and continue on.",
  "You freeze. Was that a click? ...No. You're still alive.",
  "You consider the kind of person who mines a field with no intention of cleaning them up.",
  "You decide you don't like that kind of person.",
  "..."]

YOU_DIED = [
  "At least you didn't suffer.",
  "",
  "...",
  "Click.",
  "Better luck in your next life.",
  "Your widow receives a $70,000 cheque.",
  "You don't feel a thing.",
  "You notice your mistake just as you're making it.",
  "Oops.",
  "On the plus side, this'll be the worst thing that'll happen to you today.",
  "The next one steps over your body as they search for the remaining {mines} mines.",
  "You never did find out what was so important about this place."]

YOU_WIN = ["You survive to minesweep another day."]



MAX_MELANCHOLY = max([len(s) for s in MELANCHOLY])

# purely arbitrary to make the messages sporadic enough that they come as
# somewhat of a surprise.
MELANCHOLY_LENGTH = (70, 120)



# done to suppress the pygame loading messages.
@contextmanager
def suppress_stdout():
  from os import devnull
  from sys import stdout

  with open(devnull, 'w') as d:
    old_stdout = stdout
    stdout = d

    try:
      yield

    finally:
      stdout = old_stdout


# yes, I know this is jank to have a floating window that controls a terminal
# window. This is the only way I know how to accept keyboard input at the
# moment.
with suppress_stdout():
  import pygame
  pygame.mixer.init(buffer=512)
  pygame.display.init()
  pygame.display.set_mode(size=(100, 100))
  pygame.key.set_repeat(250, 30)



# background ambience, so, quiet
pygame.mixer.music.load("static.wav")
pygame.mixer.music.set_volume(0.2)

NUMBER_SOUNDS = [
  pygame.mixer.Sound("1.wav"),
  pygame.mixer.Sound("2.wav"),
  pygame.mixer.Sound("3.wav"),
  pygame.mixer.Sound("4.wav"),
  pygame.mixer.Sound("5.wav"),
  pygame.mixer.Sound("6.wav"),
  pygame.mixer.Sound("7.wav")]

# This sound is just super loud compared to everything else, so I throttled it
# way down
EXPLOSION = pygame.mixer.Sound("explosion.wav")
EXPLOSION.set_volume(0.1)



BOMB   = "*"
SPACE  = ' '
FLAG   = "F"
HIDDEN = "█"

DEFAULT_BOMB_PERCENTAGE = 0.2

CARDINAL_NUDGE = [-1, 0, 1]
NESW_NUDGE     = [(-1, 0), (0, -1), (1, 0), (0, 1)]



class Minefield:
  def __init__(self, width=None, height=None, bombs=0,
                     bomb_percentage=DEFAULT_BOMB_PERCENTAGE, mode="standard"):
    columns, lines   = spaces(fallback=(30, 20))
    self.width       = width  or columns
    self.height      = height or lines - 2
    self.bombs       = bombs  or int((self.width * self.height) * bomb_percentage)
    self.mode        = mode


  def initialize_grid(self):
    self.grid        = [[    "" for _ in range(self.width)] for _ in range(self.height)]
    self.player_grid = [[HIDDEN for _ in range(self.width)] for _ in range(self.height)]

    info(f"Grid initialized. height: {len(self.grid)}. width: {len(self.grid[0])}.")


  @property
  def bomb_layer(self):
    return [[BOMB if self.grid[y][x] == BOMB else SPACE for x in range(self.width)] for y in range(self.height)]


  def place_bomb(self):
    while True:
      bomb_x = randint(1, self.width - 2)
      bomb_y = randint(1, self.height - 2)

      if self.grid[bomb_y][bomb_x] == BOMB:
        continue

      else:
        self.grid[bomb_y][bomb_x] = BOMB
        break


  def bomb_propagation(self):
    info("Placing bombs.")
    for i in range(self.bombs):
      self.place_bomb()


  def adjacencies(self, x, y, mode="cardinal"):
    if mode == "cardinal":
      nudges = [(x_nudge, y_nudge) for y_nudge in CARDINAL_NUDGE for x_nudge in CARDINAL_NUDGE]

    else:
      nudges = NESW_NUDGE

    adjacent_spaces = []

    for x_nudge, y_nudge in nudges:
      adjacent_x = x + x_nudge
      adjacent_y = y + y_nudge

      if (adjacent_x, adjacent_y) == (x, y):
        continue

      if adjacent_x < 0 or adjacent_x >= self.width:
        continue

      if adjacent_y < 0 or adjacent_y >= self.height:
        continue

      adjacent_spaces.append((adjacent_x, adjacent_y))

    return adjacent_spaces


  def number_calculation(self, x, y):
    if self.grid[y][x] == BOMB:
      return

    bombs_adjacent = 0

    adjacent_spaces = self.adjacencies(x, y)

    for adjacent_x, adjacent_y in adjacent_spaces:
      if self.grid[adjacent_y][adjacent_x] == BOMB:
        bombs_adjacent += 1

    self.grid[y][x] = bombs_adjacent if bombs_adjacent > 0 else SPACE


  def calculate_all_numbers(self):
    for x in range(self.width):
      for y in range(self.height):
        self.number_calculation(x, y)


  def open_space(self, x, y, grid):
    if grid[y][x] is not SPACE:
      raise ValueError

    open_spaces = {(x, y)}
    temp_open_spaces = set()
    discovered_spaces = {(x, y)}

    while open_spaces:
      for space in open_spaces:
        for coordinates in self.adjacencies(*space, mode="NESW"):
          if coordinates in discovered_spaces:
            continue

          adjacent_x, adjacent_y = coordinates

          if grid[adjacent_y][adjacent_x] == SPACE:
            temp_open_spaces |= {(adjacent_x, adjacent_y)}

      discovered_spaces |= temp_open_spaces
      open_spaces        = temp_open_spaces
      temp_open_spaces   = set()

    return discovered_spaces


  def calculate_open_spaces(self, grid):
    open_spaces = []

    for x in range(self.width):
      for y in range(self.height):
        try:
          if (x, y) in chain(*open_spaces):
            continue

          else:
            open_spaces.append(self.open_space(x, y, grid))

        except ValueError:
          continue

    return open_spaces


  # was used in debugging to check the open-space detector (self.calculate_open_spaces)
  def all_open_spaces(self, grid=None):
    grid = grid or self.grid
    open_spaces = self.calculate_open_spaces(grid)

    temp_grid = [[SPACE for _ in range(self.width)] for _ in range(self.height)]

    for i, coordinates in enumerate(open_spaces):
      for x, y in coordinates:
        temp_grid[y][x] = chr(97 + i)

    return temp_grid


  def all_nonbomb_spaces(self):
    return self.all_open_spaces(self.bomb_layer)


  def open_enclosure(self, enclosure):
    try:
      while True:
        x, y = choice(list(enclosure))

        adjustment = False

        for adjacent_x, adjacent_y in self.adjacencies(x, y, mode="NESW"):
          if self.grid[adjacent_y][adjacent_x] == BOMB:
            self.grid[adjacent_y][adjacent_x] = SPACE
            self.place_bomb()
            raise Adjustment

    except Adjustment:
      return


  def check_for_enclosures(self):
    while True:
      nonbomb_spaces = self.calculate_open_spaces(self.bomb_layer)

      # exactly one enclosure means that you can walk to any nonbomb space from
      # any other nonbomb space, and therefore the map is completely open
      if len(nonbomb_spaces) > 1:
        info(f"{len(nonbomb_spaces) - 1} enclosures detected. Opening.")
        for enclosure in nonbomb_spaces[1:]:
          self.open_enclosure(enclosure)

      else:
        break


  def reveal_edges(self):
    # as the edges are guaranteed not to have bombs, the game starts with the
    # edges (and any open space connected to the edges) already revealed.
    for space in chain(
      [(x, 0) for x in range(self.width)],
      [(x, self.height - 1) for x in range(self.width)],
      [(0, y) for y in range(1, self.height - 1)],
      [(self.width - 1, y) for y in range(1, self.height - 1)]):
      self.reveal(space)


  def generate_game(self):
    print("\033[2J\033[3J\033[H", end="", flush=True)
    self.initialize_grid()
    self.bomb_propagation()
    self.check_for_enclosures()
    self.calculate_all_numbers()
    self.reveal_edges()
    self.flags      = 0
    self.cursor     = [0, 0]
    self.status_line = ""
    self.melahcholy = randint(*MELANCHOLY_LENGTH)
    self.playing    = True
    print("\033[2J\033[3J\033[H" + self.player_visible(), end="", flush=True)


  def render_space(self, space, highlight=False):
    if highlight:
      return ANSI_CLEAR + ansi(HIGHLIGHT_COLOUR, HIDDEN)

    message = ANSI_CLEAR

    if space is HIDDEN:
      message += ansi(FIELD_COLOUR, HIDDEN)

    elif space is BOMB:
      message += ansi(BOMB_COLOUR, BOMB)

    elif space is FLAG:
      message += ansi(FIELD_COLOUR, "", background=True) + ansi(FLAG_COLOUR, FLAG)

    elif isinstance(space, int):
      message += ansi(COLOURS[space], str(space))

    else:
      message += " "

    return message


  def player_visible(self):
    return f"\n".join("".join([self.render_space(space) for space in line]) for line in self.player_grid) + ANSI_CLEAR


  def show_cursor(self):
    x, y = self.cursor

    if self.player_grid[y][x] == HIDDEN:
      return f"\033[{y + 1};{x + 1}H" + ansi(PLAYER_FIELD_COLOUR, SPACE, background=True)

    elif isinstance(self.player_grid[y][x], int):
      return f"\033[{y + 1};{x + 1}H" + ansi(PLAYER_COLOUR, "", background=True) + ansi(COLOURS[self.player_grid[y][x]], f"{self.player_grid[y][x]}")

    elif self.player_grid[y][x] == FLAG:
      return f"\033[{y + 1};{x + 1}H" + ansi(PLAYER_FIELD_COLOUR, "", background=True) + ansi(FLAG_COLOUR, FLAG)

    else:
      return f"\033[{y + 1};{x + 1}H" + ansi(PLAYER_COLOUR, SPACE, background=True)


  def move_cursor(self, old_cursor):
    x, y = old_cursor
    for nudge_x, nudge_y in self.adjacencies(x, y):
      self.print_at_cursor(nudge_x, nudge_y)


  def move_player(self, direction):
    x, y = getattr(self, f"cursor_{direction}")()

    if x < 0:
      x = self.width - 1

    if y < 0:
      y = self.height - 1

    x %= self.width
    y %= self.height

    if self.mode == "soldier" and self.player_grid[y][x] == FLAG:
      return

    self.print_at_cursor(*self.cursor)
    self.cursor = [x, y]

    if self.mode == "soldier":
      self.reveal(self.cursor)


  def print_at_cursor(self, x, y, highlight=False):
    print(f"\033[{y + 1};{x + 1}H" + self.render_space(self.player_grid[y][x], highlight=highlight), end="", flush=True)


  def reveal_spaces(self, x, y):
    for space in self.open_space(x, y, self.grid):
      # also reveals a layer of numbers around the open spaces
      for adjacency in self.adjacencies(*space):
        self.reveal(adjacency, reveal_spaces=True)


  def reveal(self, cursor=None, reveal_spaces=False):
    if cursor is None:
      x, y = self.cursor

    else:
      x, y = cursor

    if self.player_grid[y][x] == FLAG:
      return

    previous_space = self.player_grid[y][x]
    self.player_grid[y][x] = self.grid[y][x]
    self.print_at_cursor(x, y)

    if self.player_grid[y][x] == BOMB:
      self.status_line = choice(YOU_DIED)
      EXPLOSION.play()
      # autoprints next to the bomb in red, handily
      print("KABOOM")
      raise Lose_Condition

    elif previous_space != SPACE and self.player_grid[y][x] == SPACE and not reveal_spaces:
      self.reveal_spaces(x, y)

    elif not isinstance(previous_space, int) and isinstance(self.player_grid[y][x], int) and not reveal_spaces:
      NUMBER_SOUNDS[self.player_grid[y][x] - 1].play()


  # TODO: make a cursor object that can, at the very least, push all these
  #       methods down the chain so they're not just sitting here
  def cursor_player(self):
    return self.cursor


  def cursor_up(self):
    return self.cursor[0], self.cursor[1] - 1


  def cursor_down(self):
    return self.cursor[0], self.cursor[1] + 1


  def cursor_left(self):
    return self.cursor[0] - 1, self.cursor[1]


  def cursor_right(self):
    return self.cursor[0] + 1, self.cursor[1]


  def flag(self, direction="player"):
    x, y = getattr(self, f"cursor_{direction}")()

    if x < 0 or x >= self.width or y < 0 or y >= self.height:
      return

    previous_character = self.player_grid[y][x]

    if previous_character == FLAG:
      self.player_grid[y][x] = HIDDEN
      self.flags -= 1

    elif previous_character == HIDDEN:
      self.player_grid[y][x] = FLAG
      self.flags += 1

    self.print_at_cursor(x, y)


  def show_flags(self):
    flags_remaining = self.bombs - self.flags

    return ANSI_CLEAR + f"\033[{self.height + 2};{0}HFlags: {flags_remaining:>4} | {self.status_line.format(mines=flags_remaining): <{MAX_MELANCHOLY}}"


  def reveal_adjacent(self):
    x, y = self.cursor
    if not isinstance(self.player_grid[y][x], int):
      return

    flags_adjacent = 0

    adjacent_spaces = self.adjacencies(x, y)
    spaces_to_reveal = []

    # Windows Minesweeper behaviour: Reveal adjacent spaces only if you're on a
    # number, and only if you have that number of flags adjacent to it.
    # TODO: DRY this
    for adjacent_x, adjacent_y in adjacent_spaces:
      if self.player_grid[adjacent_y][adjacent_x] == FLAG:
        flags_adjacent += 1

      elif self.player_grid[adjacent_y][adjacent_x] == HIDDEN:
        spaces_to_reveal.append((adjacent_x, adjacent_y))

    if flags_adjacent == self.player_grid[y][x]:
      for space in spaces_to_reveal:
        self.reveal(space)


  def check_board(self):
    if self.flags != self.bombs:
      return

    hidden_spaces = [(x, y) for y in range(self.height) for x in range(self.width) if self.player_grid[y][x] == HIDDEN]

    for space in hidden_spaces:
      self.reveal(space)

    raise Win_Condition


  def highlight_adjacent(self):
    x, y = self.cursor
    if not isinstance(self.player_grid[y][x], int):
      return

    flags_adjacent = 0
    spaces_to_highlight = []

    # As some people click and hold on the button to reveal adjacent spaces to
    # check their work, a highlight-adjacent-squares button was added that
    # follows the same behaviour as revealing those adjacent squares.
    # TODO: DRY this
    for adjacent_x, adjacent_y in self.adjacencies(x, y):
      if self.player_grid[adjacent_y][adjacent_x] == FLAG:
        flags_adjacent += 1

      elif self.player_grid[adjacent_y][adjacent_x] == HIDDEN:
        spaces_to_highlight.append((adjacent_x, adjacent_y))

    if flags_adjacent == self.player_grid[y][x]:
      for space in spaces_to_highlight:
        self.highlight(space)


  MOVE_DISPATCH = {
    pygame.K_w: (move_player, {"direction": "up"}),
    pygame.K_s: (move_player, {"direction": "down"}),
    pygame.K_a: (move_player, {"direction": "left"}),
    pygame.K_d: (move_player, {"direction": "right"}),
    pygame.K_KP5: (reveal, {}),
    pygame.K_f: (flag, {"direction": "player"}),
    pygame.K_KP_ENTER: (reveal_adjacent, {}),
    pygame.K_SPACE: (check_board, {}),
    pygame.K_KP8: (flag, {"direction": "up"}),
    pygame.K_KP2: (flag, {"direction": "down"}),
    pygame.K_KP4: (flag, {"direction": "left"}),
    pygame.K_KP6: (flag, {"direction": "right"})}


  def move(self, direction):
    self.unhighlight_adjacent()

    if direction in self.MOVE_DISPATCH:
      f, args = self.MOVE_DISPATCH[direction]

      f(self, **args)

      self.melancholy -= 1

      if self.melancholy <= 0:
        # intended to stop after a while, for now; more procedurally-generated
        # text is possible, but probably way down the line, if at all
        if MELANCHOLY:
          self.status_line = MELANCHOLY.pop(0)

        self.melancholy = randint(*MELANCHOLY_LENGTH)


  def end_game(self):
    raise Game_End


  END_DISPATCH = {
    pygame.K_ESCAPE: end_game,
    pygame.K_r: generate_game}


  def end(self, direction):
    self.unhighlight_adjacent()

    if direction in self.END_DISPATCH:
      self.END_DISPATCH[direction](self)


  def highlight(self, cursor):
    self.print_at_cursor(*cursor, highlight=True)


  def unhighlight_adjacent(self):
    self.move_cursor(self.cursor)


  def win(self):
    self.status_line = choice(YOU_WIN)


  # technically a misnomer, as it obviously shows the cursor too
  def show_status_line(self):
    print(self.show_cursor() + self.show_flags(), end="", flush=True)



def parse_area(area):
  if area is None:
    return None, None

  width, height= area.split("x")
  columns, lines   = spaces(fallback=(30, 20))

  width  = int(width)
  height = int(height)

  if width > columns or height > lines:
    raise ValueError

  return width, height



def main(width, height, bombs, bomb_percentage, colour, mode):
  basicConfig(
    filename=f"sweeper.log",
    level=INFO,
    format='%(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %I:%M:%S %p')

  global COLOURS
  COLOURS = colour

  minefield = Minefield(width=width,
                        height=height,
                        bombs=bombs,
                        bomb_percentage=bomb_percentage,
                        mode=mode)

  minefield.generate_game()

  pygame.mixer.music.play(loops=-1)
  clock = pygame.time.Clock()

  while True:
    try:
      minefield.show_status_line()

      events = pygame.event.get()

      for event in events:
        if event.type == pygame.KEYDOWN:
          dispatch = minefield.move if minefield.playing else minefield.end
          dispatch(event.key)

      pressed = pygame.key.get_pressed()

      if pressed[pygame.K_KP0]:
        minefield.highlight_adjacent()

      else:
        minefield.unhighlight_adjacent()

      clock.tick(60)

    except Lose_Condition:
      pygame.mixer.music.stop()
      minefield.playing = False

    except Win_Condition:
      pygame.mixer.music.stop()
      minefield.playing = False
      minefield.win()



if __name__ == "__main__":
  args = argparser.parse_args()

  try:
    width, height   = parse_area(args.area)
    bombs           = int(args.bombs)
    bomb_percentage = float(args.bomb_percent)
    colour          = COLOUR_SCHEMES[args.colour]

  except (KeyError, ValueError) as e:
    # TODO: Nicer error messages
    print(e.args)

    # used here to avoid the terminal reset characters below
    quit()

  try:
    main(width, height, bombs, bomb_percentage, colour, args.mode)

  except Game_End:
    pass

  finally:
    # cleans up the terminal after the game

    print(ANSI_CLEAR + "\033[2J\033[3J\033[H", end="")