from curses import textpad
import urllib.request
import threading
import socket
import random
import pickle
import curses
import time
import sys
import os
from tkinter import messagebox


# Let op: Curses gebruikt Y,X inplaats van X,Y.


DELAY = 500
GAME_PORT = 9595
MAX_POWERUP_AMOUNT = 80
MAX_PLAYER_AMOUNT = 10
MAX_PASSWORD_LENGTH = 25
snake_display_symbol = 'o'
quit_game = False
auto_reconnect = True
possible_powerups = {"speed":{"kind":"speed","symbol":'+',"duration":5,"color":3, "description":"Increases the snake's speed by 5."},
                "slowness":{"kind":"slowness","symbol":'-',"duration":5,"color":3, "description":"Decreases the snake's speed by 5."},
                "reverse":{"kind":"reverse","symbol":'R',"duration":5,"color":2, "description":"Reverses the snake's controls."},
                "score1":{"kind":"score1","symbol":'1',"duration":0,"color":1, "description":"Increases the snake's score by 1."},
                "score2":{"kind":"score2","symbol":'2',"duration":0,"color":1, "description":"Increases the snake's score by 2."},
                "score5":{"kind":"score5","symbol":'5',"duration":0,"color":1, "description":"Increases the snake's score by 5"},
                "random":{"kind":"random", "description": "Chooses a random powerup from the above."}}
possible_settings = {"Positive Color":1,"Negative Color":2,"Neutral Color":3,"Selection Color":4,"Username":""}
possible_controls = {"Up":"Up-Arrow","Down":"Down-Arrow","Left":"Left-Arrow","Right":"Right-Arrow","Back":"ESC"}
standard_password = ''

class SavedData:
    def __init__(self, highscore, selection_color, positive_color, negative_color, neutral_color, standard_game_height, standard_game_width, standard_powerup_amount, standard_player_amount, username):
        self.highscore = highscore
        self.selection_color = selection_color
        self.positive_color = positive_color
        self.negative_color = negative_color
        self.neutral_color = neutral_color
        self.standard_game_height = standard_game_height
        self.standard_game_width = standard_game_width
        self.standard_powerup_amount = standard_powerup_amount
        self.standard_player_amount = standard_player_amount
        self.username = username


# Check if the game already has some saved data.
if os.path.isfile("saveddata.data"):
    file = open("saveddata.data", "rb")
    object = pickle.load(file)
    file.close()
    highscore = object.highscore
    selection_color = object.selection_color
    positive_color = object.positive_color
    negative_color = object.negative_color
    neutral_color = object.neutral_color
    standard_game_height = object.standard_game_height
    standard_game_width = object.standard_game_width
    standard_powerup_amount = object.standard_powerup_amount
    standard_player_amount = object.standard_player_amount
    username = object.username
else:
    highscore = 0
    selection_color = curses.COLOR_YELLOW
    positive_color = curses.COLOR_GREEN
    negative_color = curses.COLOR_RED
    neutral_color = curses.COLOR_BLUE
    standard_game_height = 20
    standard_game_width = 50
    standard_powerup_amount = 5
    standard_player_amount = 10
    username = ""


# Gets user input
def curses_input(window, height, width, y, x, question):
    window.addstr(y,x-int(len(question)/2), question)
    new_window = curses.newwin(height, width, y+5, int(x-width/2))
    txtbox = curses.textpad.Textbox(new_window)
    curses.textpad.rectangle(screen, y+5 - 1, int(x-width/2) - 1, y+5 + height, int(x-width/2) + width)
    screen.refresh()
    return txtbox.edit()


# Saves the data to a file.
def save_data():
    saveddata = SavedData(highscore,selection_color,positive_color,negative_color,neutral_color,standard_game_height,standard_game_width,standard_powerup_amount,standard_player_amount, username)
    file = open("saveddata.data","wb")
    pickle.dump(saveddata,file)
    file.close()

class ClientSnake:
    def __init__(self):
        pass
class Snake:
    def __init__(self):
        self.positions = [[1,10]]
        self.length = 5
        self._direction = [0,1]
        self.is_alive = False
        self.speed = 10  # The delay will be 1/speed
        self.reversed_controls = False
        threading.Thread(target=self.__loop).start()

    def __loop(self):
        while not quit_game:
            if self.is_alive:
                new_position = [self.positions[-1][0]+self._direction[0],self.positions[-1][1]+self._direction[1]]

                self.positions.append(new_position)
                if len(self.positions) > self.length:
                    self.positions.pop(0)

            time.sleep(1/self.speed)

    # I used this way for changing directions so I could apply the 'reverse' powerup.
    def set_direction(self, direction):
        if self.reversed_controls:
            self._direction = [-direction[0],-direction[1]]
        else:
            self._direction = direction

    def wait_duration(self, duration, action):
        time.sleep(duration)
        action()

    def apply_powerup(self, powerup):
        # THERE HAS TO BE A BETTER WAY OF DOING THIS... From within the PowerUp Definition, But how???

        if powerup.kind == "speed":
            self.speed += 5

            def action():
                self.speed -= 5

            threading.Thread(target=self.wait_duration, args=(powerup.duration, action,)).start()
        elif powerup.kind == "slowness":
            if self.speed > 5:
                self.speed -= 5

                def action():
                    self.speed += 5

                threading.Thread(target=self.wait_duration, args=(powerup.duration, action,)).start()
        elif powerup.kind == "reverse":
            self.reversed_controls = True

            def action():
                self.reversed_controls = False

            threading.Thread(target=self.wait_duration, args=(powerup.duration, action,)).start()

        elif powerup.kind in ["score1", "score2", "score5"]:
            self.length+=int(powerup.kind[-1])

    def reset(self):
        new_self = Snake()
        self.__dict__.update(new_self.__dict__)


class MenuOption:
    def __init__(self, name, fr, to):
        self.name = name
        self.fr = fr
        self.to = to


class Navigation:
    def __init__(self,window, own_snake):
        main_menu = [MenuOption("Play","Main","Gamemode"),
                     MenuOption("Settings","Main","Settings"),
                     MenuOption("Info", "Main", "Info"),
                     MenuOption("Exit","Main","EXIT")]

        multiplayer_menu=[MenuOption("Host","MultiPlayer","Host"),
                     MenuOption("Join", "MultiPlayer", "Join"),
                     MenuOption("Back", "MultiPlayer", "Gamemode")]

        host_menu = [MenuOption("Start","Host","MultiPlayHost"),
                     MenuOption("Game Width","Host","change.MP.Game Width"),
                     MenuOption("Game Height","Host","change.MP.Game Height"),
                     MenuOption("Powerup Amount", "Host", "change.MP.Powerup Amount"),
                     MenuOption("Player Amount", "Host", "change.MP.Player Amount"),
                     MenuOption("Password", "Host", "change.MP.Password"),
                     MenuOption("Back", "Host", "MultiPlayer")]

        gamemode_menu = [MenuOption("SinglePlayer","Gamemode","SinglePlayerOptions"),
                     MenuOption("MultiPlayer", "Gamemode", "MultiPlayer"),
                     MenuOption("Back", "Gamemode", "Main")]

        singleplayeroptions_menu = [MenuOption("Start","SinglePlayerOptions","Play"),
                     MenuOption("Game Width","SinglePlayerOptions","change.SP.Game Width"),
                     MenuOption("Game Height","SinglePlayerOptions","change.SP.Game Height"),
                     MenuOption("Powerup Amount", "SinglePlayerOptions", "change.SP.Powerup Amount"),
                     MenuOption("Back", "SinglePlayerOptions", "Gamemode")]

        settings_menu = [MenuOption("Back","Settings","Main")]
        [settings_menu.insert(0,MenuOption(name,"Settings","set."+name)) for name in possible_settings.keys()]

        self.menus = {"Main":main_menu,"Settings":settings_menu,"SinglePlayerOptions":singleplayeroptions_menu, "Gamemode":gamemode_menu, "MultiPlayer":multiplayer_menu, "Host":host_menu}
        self.own_snake = own_snake
        self.window = window
        # Check if the user already has a username, ask for one if it doesn't.
        global username
        while username == "":
            h, w = self.window.getmaxyx()
            username = curses_input(self.window, 1, 15, 10, int(w/2), "Enter a username, You can always change this later.")

        self.current_menu = "Main"
        self.current_selection_index = 0
        self.display_current_menu()
        self.__loop()

    # Displays the menu specified by self.current_menu.
    def display_current_menu(self):
        global standard_game_width, standard_game_height, standard_powerup_amount, standard_player_amount, standard_password, auto_reconnect
        h, w = self.window.getmaxyx()
        # Check if the game should exit:
        if self.current_menu == "EXIT":
            global quit_game
            quit_game = True
        elif self.current_menu == "Play":

            # Fix Game size to fit the window
            if standard_game_height > h-5:
                standard_game_height = h-5
            if standard_game_width > w-5:
                standard_game_width = w-5

            # Create and start the match+input loop
            self.in_match = True
            Match(self.window, standard_game_height, standard_game_width, standard_powerup_amount ,self.own_snake)
            # When you get here, the match is over
            self.in_match = False  # This will stop the input loop.
            self.own_snake.reset()
            self.current_menu = "Main"
            self.display_current_menu()

        elif self.current_menu == "MultiPlayHost":
            self.in_match = True


            while auto_reconnect:
                MultiMatchHost(self.window, standard_game_height, standard_game_width, standard_powerup_amount, standard_player_amount, standard_password,self.own_snake)
                time.sleep(0.1)
            auto_reconnect = True

            # When you get here, the match is over
            self.in_match = False  # This will stop the input loop.
            self.own_snake.reset()
            self.current_menu = "Main"
            self.display_current_menu()
        else:
            self.window.clear()
            self.window.addstr(2, int(w / 2 - len(self.current_menu) / 2), self.current_menu)

            line_number = 6
            x = int(w / 2)

            if self.current_menu == "Info":

                x = int(w / 2 - w / 4)

                self.window.addstr(5, int(w / 2 - len("Controls") / 2), "Controls")
                for action, control_key in possible_controls.items():
                    self.window.addstr(line_number, x, action+": "+control_key)
                    line_number += 1

                self.window.addstr(line_number, int(w / 2 - len("Powerups") / 2), "Powerups")

                for powerup in possible_powerups.values():
                    # Don't display 'random' as a powerup
                    if powerup.get("kind") == "random":
                        continue
                    for name, attribute in powerup.items():

                        try:
                            if name == "kind":
                                line_number += 1  # Extra new line
                                self.window.attron(curses.color_pair(powerup.get("color")))
                                self.window.addstr(line_number, x, str(attribute))
                                self.window.attroff(curses.color_pair(powerup.get("color")))
                                line_number += 1
                            elif name == "duration" and attribute == 0:
                                continue
                            elif not name == "color":
                                self.window.addstr(line_number, x, name+": "+str(attribute))
                                line_number += 1
                        except:
                            # It doesn't fit in the window.
                            # Disable the color in case it didn't fit the window after attron.
                            self.window.attroff(curses.color_pair(powerup.get("color")))
                            pass
            elif self.current_menu == "Join":
                ip = str(curses_input(self.window, 1, 16, line_number, x, "Enter the ip-address of the host.")).replace(" ","")
                # Try local connection if the ip == "":
                if ip == "":
                    ip = str(socket.gethostbyname(socket.gethostname()))
                self.window.clear()
                password = str(curses_input(self.window, 1, 26, line_number, x, "Enter the password of the game."))
                self.window.clear()
                self.in_match = True
                while auto_reconnect:
                    MultiMatchClient(self.window,ip,password,self.own_snake)
                    time.sleep(0.1)
                auto_reconnect = True
                # When you get here, the match is over
                self.in_match = False  # This will stop the input loop.
                self.own_snake.reset()
                self.current_menu = "Main"
                self.display_current_menu()

            elif self.current_menu.startswith("set."):
                option = self.current_menu.replace("set.","")
                variable_name = option.lower().replace(" ","_")
                if option == "Username":
                    global username
                    username = curses_input(self.window, 1, 15, 10, int(w/2), "Enter a new username.")
                    self.window.addstr(line_number + 3, int(x - len("Username changed to "+username) / 2), "Username changed to "+username)
                else:
                    color = None
                    while not color in range(0,256):
                        try:
                            color = int(curses_input(self.window, 1, 4, line_number, x, option+ " - Enter the number of a color from the 256 color palette."))
                        except:
                            # Input wasn't a number
                            pass

                    # THERE HAS TO BE A BETTER WAY OF DOING THIS. with exec() or something
                    global selection_color, positive_color, negative_color, neutral_color
                    if variable_name == "selection_color":
                        selection_color = color
                    elif variable_name == "positive_color":
                        positive_color = color
                    elif variable_name == "negative_color":
                        negative_color = color
                    elif variable_name == "neutral_color":
                        neutral_color = color

                    color_number = possible_settings.get(option)
                    curses.init_pair(color_number, color, curses.COLOR_BLACK)
                    self.window.attron(curses.color_pair(color_number))
                    string = option+" Changed to "+ str(color)
                    self.window.addstr(line_number+3, int(x-len(string)/2), string)
                    self.window.attroff(curses.color_pair(color_number))
                self.window.refresh()
                time.sleep(2)
                self.current_menu = "Settings"
                self.display_current_menu()

            elif self.current_menu.startswith("change."):
                mode = self.current_menu.split('.')[1]
                option = self.current_menu.split('.')[2]
                game_width = -1
                game_height = -1
                powerup_amount = -1
                player_amount = 1
                password = None
                if option == "Game Width":
                    while not game_width in range(10,w-5):
                        try:
                            game_width = int(curses_input(self.window, 1, 5, line_number, x,option + " - Enter a game width that fits your screen."))
                        except:
                            # Input wasn't a number
                            pass
                    standard_game_width = game_width
                elif option == "Game Height":
                    while not game_height in range(10,h-5):
                        try:
                            game_height = int(curses_input(self.window, 1, 5, line_number, x,option + " - Enter a game height that fits your screen."))
                        except:
                            # Input wasn't a number
                            pass
                    standard_game_height = game_height
                elif option == "Powerup Amount":
                    while not powerup_amount in range(0,MAX_POWERUP_AMOUNT+1):
                        try:
                            powerup_amount = int(curses_input(self.window, 1, 5, line_number, x,option + f" - Enter the amount of powerups you want (0-{MAX_POWERUP_AMOUNT})"))
                        except:
                            # Input wasn't a number
                            pass
                    standard_powerup_amount = powerup_amount
                elif option == "Player Amount":
                    while not player_amount in range(2,MAX_PLAYER_AMOUNT+1):
                        try:
                            player_amount = int(curses_input(self.window, 1, 5, line_number, x,option + f" - Enter the maximum amount of players you want (2-{MAX_PLAYER_AMOUNT})"))
                        except:
                            # Input wasn't a number
                            pass
                    standard_player_amount = player_amount
                elif option == "Password":
                    try:
                        password = curses_input(self.window, 1, MAX_PASSWORD_LENGTH+1, line_number, x,option + f" - Enter a Password, Leave blank if you want no password. (Length: [0,{MAX_PASSWORD_LENGTH}])")
                    except:
                        # Input wasn't in range(0,25)
                        pass
                    standard_password = password
                string = option + " Changed!"
                self.window.addstr(line_number + 3, int(x - len(string) / 2), string)
                self.window.refresh()
                time.sleep(2)
                if mode == "SP":
                    self.current_menu = "SinglePlayerOptions"
                elif mode == "MP":
                    self.current_menu = "Host"
                self.display_current_menu()

            else:
                snake_text = "SNAKE SNAKE SNAKE SNAKE SNAKE SNAKE"
                x = int(w / 2 - len(snake_text) / 2)
                y = int(h / 2 - int(len(self.menus[self.current_menu]) / 2)-7)
                self.window.addstr(y, x, snake_text)

                # Display every menu option
                for i,menu_option in enumerate(self.menus[self.current_menu]):
                    x = int(w / 2 - len(menu_option.name) / 2)
                    y = int(h / 2 - int(len(self.menus[self.current_menu])/2) + i)
                    if i == self.current_selection_index:
                        self.window.attron(curses.color_pair(4))
                    self.window.addstr(y, x, menu_option.name)
                    self.window.attroff(curses.color_pair(4))

            self.window.refresh()

    def __loop(self):
        global quit_game
        while not quit_game:

            key = self.window.getch()

            # Check if you pressed a key that has a functionality,
            # otherwise it would be refreshing the current menu for no reason.
            if key in [curses.KEY_UP,curses.KEY_DOWN,curses.KEY_ENTER,27,10,13]:  # 27 = ESC or ALT [10,13] = Enter
                if key == curses.KEY_UP and self.current_selection_index > 0:
                    self.current_selection_index -= 1
                elif key == curses.KEY_DOWN:
                    try:
                        if self.current_selection_index < len(self.menus[self.current_menu])-1:
                            self.current_selection_index += 1
                    except:
                        # Some menu's aren't in 'self.menus' so trying to subscript them wil cause an error.
                        pass
                elif key in [10,13]:            # [10,13] = Enter
                    self.current_menu = self.menus[self.current_menu][self.current_selection_index].to
                    self.current_selection_index = 0
                elif key == 27:                 # 27 = ESC or ALT
                    if self.current_menu == "Main":
                        quit_game = True
                        break
                    else:
                        self.current_menu = "Main"

                self.display_current_menu()


# SinglePlayer only Match.
class Match:
    def __init__(self, window, height, width, powerup_amount ,own_snake):
        self.window = window
        self.height = height
        self.width = width
        self.own_snake = own_snake
        self.game_over = False
        self.powerups = [PowerUp(possible_powerups.get("random"), [height-1,width-1]) for _ in range(powerup_amount)]
        self.own_snake.is_alive = True
        threading.Thread(target=self.__ingame_input_loop).start()
        self.draw_game()
        self.__display_loop()

    # Draws the match.
    def draw_game(self):
        self.window.clear()

        h, w = self.window.getmaxyx()

        left_border = int(w / 2 - self.width / 2)
        right_border = int(w / 2 + self.width / 2)
        top_border = int(h / 2 - self.height / 2)
        bottom_border = int(h / 2 + self.height / 2)
        topleft = [top_border,left_border]
        bottomright = [bottom_border, right_border]

        textpad.rectangle(self.window, topleft[0], topleft[1], bottomright[0], bottomright[1])

        # Draw the Score and Highscore
        score = self.own_snake.length - 5
        global highscore
        if score > highscore:
            highscore = score
        score_text = "Score: "+str(score)
        highscore_text = "HighScore: "+ str(highscore)
        self.window.attron(curses.color_pair(1))
        self.window.addstr(top_border, left_border+1, score_text)
        self.window.addstr(top_border, right_border-len(highscore_text), highscore_text)
        self.window.attroff(curses.color_pair(1))

        # Draw The PowerUps
        for powerup in self.powerups:
            self.window.attron(curses.color_pair(powerup.color))
            self.window.addstr(top_border + powerup.position[0], left_border + powerup.position[1], powerup.symbol)
            self.window.attroff(curses.color_pair(powerup.color))

        # Check if the snake is in a powerup
        for powerup in self.powerups:
            if powerup.position in self.own_snake.positions:
                self.own_snake.apply_powerup(powerup)
                self.powerups.remove(powerup)
                self.powerups.append(PowerUp(random.choice(list(possible_powerups.values())), [self.height - 1, self.width - 1]))

        # Kill the snake if it's head is inside itself.
        if self.own_snake.positions.count(self.own_snake.positions[-1]) >= 2:
            self.own_snake.is_alive = False

        for pos in self.own_snake.positions:

            # Kill the snake when it's out of the window.
            if pos[0] <= 0 or pos[0] >= self.height:
                self.own_snake.is_alive = False
            elif pos[1] <=0 or pos[1] >= self.width:
                self.own_snake.is_alive = False

            self.window.addstr(top_border+pos[0],left_border+pos[1],snake_display_symbol)

        # Stop the game if the snake is dead.
        if not self.own_snake.is_alive:
            self.game_over = True
            game_over_message = "GAME OVER!"
            winner_message = "YOU DIED WITH A SCORE OF "+str(score)
            h, w = self.window.getmaxyx()
            x = int(w / 2 - len(game_over_message) / 2)
            y = int(h / 2)
            self.window.attron(curses.color_pair(2))
            self.window.addstr(y, x, game_over_message)
            self.window.attroff(curses.color_pair(2))
            self.window.refresh()
            time.sleep(1)
            x = int(w / 2 - len(winner_message) / 2)
            y = int(h / 2+1)
            self.window.attron(curses.color_pair(1))
            self.window.addstr(y,x, winner_message)
            self.window.attroff(curses.color_pair(1))
            self.window.refresh()
            time.sleep(2)

        self.window.refresh()

    def __display_loop(self):
        while not quit_game:
            if self.game_over:
                break
            self.draw_game()

    def __ingame_input_loop(self):
        while not self.game_over:

            key = self.window.getch()

            if key == curses.KEY_UP:
                self.own_snake.set_direction([-1, 0])
            elif key == curses.KEY_DOWN:
                self.own_snake.set_direction([1, 0])
            elif key == curses.KEY_LEFT:
                self.own_snake.set_direction([0, -1])
            elif key == curses.KEY_RIGHT:
                self.own_snake.set_direction([0, 1])
            elif key == 27:  # 27 = ESC or ALT
                break


class MultiMatchClient:
    def __init__(self, window, host_ip, password,own_snake):
        self.window = window
        self.socket = socket.socket()
        self.host_ip = host_ip
        self.own_snake = own_snake
        self.host_password = password
        self.running = True
        self.in_lobby = True
        self.in_game = False
        # Messages the shows up when the game is over.
        self.game_over_reason = "All snakes are dead."
        self.othersnakes = []
        self.othersnake_names = []
        self.powerups = []
        self.usedpowerupcords = []
        self.unsentmessages = []
        # Indicates the time from the previous message until now. This number gets high when the connection is lost.
        self.time_to_latest_message = 0
        # The maxium value of self.time_to_latest_message before stopping the game.
        self.max_server_delay = 2.5
        threading.Thread(target=self.input_loop).start()
        threading.Thread(target=self.remove_used_powerups).start()

        self.join()

    # basically causes you to leave the match.
    def disconnect(self, reconnect):
        global auto_reconnect
        auto_reconnect = reconnect
        self.window.clear()
        self.running = False
        self.socket.close()

    # Deals with the keyboard inputs of the client while in the lobby
    def input_loop(self):
        global auto_reconnect
        while self.running:
            key = self.window.getch()
            if self.in_lobby:
                if key == 27:  # 27 = ESC or ALT
                    self.disconnect(False)
            else:
                if key == curses.KEY_UP:
                    self.own_snake.set_direction([-1, 0])
                elif key == curses.KEY_DOWN:
                    self.own_snake.set_direction([1, 0])
                elif key == curses.KEY_LEFT:
                    self.own_snake.set_direction([0, -1])
                elif key == curses.KEY_RIGHT:
                    self.own_snake.set_direction([0, 1])
                elif key == 27:  # 27 = ESC or ALT
                    auto_reconnect = False
                    # this makes sure that the server gets notified of our death.
                    self.game_over_reason = "You left."
                    self.own_snake.is_alive = False
                    self.disconnect(False)

    # Removes used powerups from the list as soon as the snake has gone away from the poperups position.
    def remove_used_powerups(self):
        while self.running and self.in_game:
            for i,usedcords in enumerate(self.usedpowerupcords):
                if not usedcords in self.own_snake.positions:
                    self.usedpowerupcords.pop(i)
            time.sleep(0.5)

    # Stops the game if the connection is lost with the host.
    def connection_lost_check(self):
        while self.running and self.in_game:
            if self.time_to_latest_message > self.max_server_delay:
                self.game_over_reason = "Lost connection with the host :("
                self.disconnect(False)
            time.sleep(0.5)
            self.time_to_latest_message += 0.5

    # Receives game info from the host.
    def recv_host_data(self):
        while self.running and self.in_game:
            try:
                data = self.socket.recv(8192)
                data = pickle.loads(data)
            except:
                continue

            self.othersnakes = data[0]
            self.powerups = data[1]
            messages = data[2]
            for msg in messages:
                if msg == "kill":
                    self.own_snake.is_alive = False
                elif msg.startswith("stop"):
                    winner = msg.split(" ")[1]
                    self.game_over_reason = winner + " won!"
                    # This breaks the draw_game() loop, and so runs stop_game()
                    self.in_game = False
            self.time_to_latest_message = 0

    # Sends game info to the host.
    def send_data(self):
        try:
            sent = False
            while self.running and self.in_game:
                # Format of the date that we're sending. = [[[1,1],[1,2],[1,3]],['message1','message2']]
                msg = []
                if self.unsentmessages:
                    msg = self.unsentmessages
                    self.unsentmessages = []

                if not self.own_snake.is_alive:
                    msg.append("dead")

                data = pickle.dumps([self.own_snake.positions,msg])

                try:
                    self.socket.send(data)
                except:
                    continue


        except Exception as e:
            messagebox.showinfo("Error while sending data to host ", str(e))

    # Shows a messages the the game is starting.
    # and starts background threads for receiving and sending from and to the host.
    def start_game(self):
        self.in_lobby = False
        # Draw start messages
        first_message = "Alright, we're gonna start."
        second_message = "Here we go!"
        h, w = self.window.getmaxyx()
        x = int(w / 2 - len(first_message) / 2)
        y = int(h / 2)
        self.window.attron(curses.color_pair(2))
        self.window.addstr(y, x, first_message)
        self.window.attroff(curses.color_pair(2))
        self.window.refresh()
        time.sleep(1)
        x = int(w / 2 - len(second_message) / 2)
        y = int(h / 2 + 1)
        self.window.attron(curses.color_pair(1))
        self.window.addstr(y, x, second_message)
        self.window.attroff(curses.color_pair(1))
        self.window.refresh()

        time.sleep(2)
        # Set the y-position of the snake.
        self.own_snake.positions[0][0] = int(self.socket.recv(1024).decode())

        self.in_game = True
        self.own_snake.is_alive = True

        threading.Thread(target=self.send_data).start()
        threading.Thread(target=self.recv_host_data).start()
        threading.Thread(target=self.connection_lost_check).start()

        self.draw_game()

    # Draws the lobby and continuously receives lobby info from the clients.
    def draw_lobby(self):
        while self.running and self.in_lobby:
            h, w = self.window.getmaxyx()

            left_border = int(w / 2 - self.width / 2)
            right_border = int(w / 2 + self.width / 2)
            top_border = int(h / 2 - self.height / 2)
            bottom_border = int(h / 2 +self.height / 2)
            topleft = [top_border, left_border]
            bottomright = [bottom_border, right_border]

            textpad.rectangle(self.window, topleft[0], topleft[1], bottomright[0], bottomright[1])

            ip_text = "Game IP: " + str(self.host_ip)

            self.window.attron(curses.color_pair(1))
            self.window.addstr(top_border, left_border + 1, ip_text)
            self.window.attroff(curses.color_pair(1))

            x = left_border + 2
            self.window.refresh()

            try:
                recv_data = self.socket.recv(1024)
                self.time_to_latest_message = 0
                self.window.clear()
                try:
                    if recv_data.decode() == "Start":
                        self.start_game()
                    elif recv_data.decode() == "Kick":
                        self.disconnect(False)
                except:
                    # The data wasn't in the right format to do .decode() so it probably still is all_snakes
                    try:
                        all_snakes = pickle.loads(recv_data)
                        self.othersnake_names = all_snakes
                    except:
                        continue
                    # Display all other client's snakes.
                    for i, client in enumerate(all_snakes):
                        self.window.attron(curses.color_pair(1))
                        # Display the host differently
                        if i == 0:
                            self.window.addstr(top_border + i + 3, x, "(HOST) Snake " + str(i + 1) + " -- " + str(client))
                        elif str(client) == username:
                            self.window.attron(curses.color_pair(4))
                            self.window.addstr(top_border + i + 3, x, "(YOU) Snake " + str(i + 1) + " -- " + str(client))
                            self.window.attroff(curses.color_pair(4))
                        else:
                            self.window.addstr(top_border + i + 3, x, "Snake " + str(i + 1) + " -- " + str(client))
                        self.window.attroff(curses.color_pair(1))
                    self.othersnake_names.remove(username)
            except:
                # Could not receive messages from the host.
                self.disconnect(False)
                break

            self.window.refresh()

    # Tries to connect to the host and tries to enter the game by sending the password.
    def join(self):
        h, w = self.window.getmaxyx()
        x = int(w / 2)
        y = int(h / 2)
        try:
            self.socket.connect((self.host_ip,GAME_PORT))
        except:

            msg = "Can't connect to host, Check if the IP address  is correct."
            self.window.addstr(y, int(x-len(msg)/2), msg)
            self.window.refresh()
            time.sleep(5)
            return

        if self.host_password == "":
            self.host_password = " "

        self.socket.send(pickle.dumps([self.host_password,username]))
        return_msg = self.socket.recv(1024).decode()

        if return_msg == "Acces Granted":
            # Receive game info.
            game_info = pickle.loads(self.socket.recv(1024))
            self.width = game_info[1]
            self.height = game_info[0]
            self.window.clear()
            self.draw_lobby()

        else:
            if return_msg == "Duplicate name":
                msg = "There already is someone with the same username in this game, " \
                      "go change yours if you want to join."
            else:
                msg = "The password was incorrect."

            self.window.attron(curses.color_pair(2))
            self.window.addstr(y, int(x - len(msg) / 2), msg)
            self.window.attroff(curses.color_pair(2))
            self.window.refresh()
            time.sleep(4)
            self.disconnect(False)

    # Draws the game while it is running.
    def draw_game(self):
        while self.running and self.in_game:
            h, w = self.window.getmaxyx()
            left_border = int(w / 2 - self.width / 2)
            right_border = int(w / 2 + self.width / 2)
            top_border = int(h / 2 - self.height / 2)
            bottom_border = int(h / 2 + self.height / 2)
            topleft = [top_border, left_border]
            bottomright = [bottom_border, right_border]

            self.window.clear()
            textpad.rectangle(self.window, topleft[0], topleft[1], bottomright[0], bottomright[1])

            # Draw the Score
            score = self.own_snake.length - 5

            score_text = "Score: " + str(score)

            self.window.attron(curses.color_pair(1))
            self.window.addstr(top_border, left_border + 1, score_text)
            self.window.attroff(curses.color_pair(1))

            # Draw your own snake.
            for pos in self.own_snake.positions:
                self.window.attron(curses.color_pair(4))
                self.window.addstr(top_border + pos[0], left_border + pos[1], snake_display_symbol)
                self.window.attroff(curses.color_pair(4))

            # Draw The PowerUps
            for powerup in self.powerups:
                self.window.attron(curses.color_pair(powerup.color))
                self.window.addstr(top_border + powerup.position[0], left_border + powerup.position[1], powerup.symbol)
                self.window.attroff(curses.color_pair(powerup.color))

            # Draw the other snakes
            for positions in self.othersnakes:
                for pos in positions:
                    self.window.addstr(top_border + pos[0], left_border + pos[1], snake_display_symbol)

            # Draw the scoreboard
            self.window.addstr(top_border, right_border + 2, "SCOREBOARD")
            self.window.addstr(top_border + 1, right_border + 2, username + " : " + str(self.own_snake.length))
            for i, user in enumerate(self.othersnake_names):
                if len(self.othersnakes) >= i+1:
                    self.window.addstr(top_border + 2 + i, right_border + 2, user + " : " + str(len(self.othersnakes[i])))

            # Apply powerups to your own snake.
            for i,powerup in enumerate(self.powerups):
                if powerup.position in self.own_snake.positions:
                    if not powerup.position in self.usedpowerupcords:
                        self.own_snake.apply_powerup(powerup)
                        self.unsentmessages.append("pickup"+str(powerup.position))
                        self.usedpowerupcords.append(powerup.position)

            # Check if the snake should be dead.
            for pos in self.own_snake.positions:

                # Kill the snake when it's out of the window.
                if pos[0] <= 0 or pos[0] >= self.height:
                    self.own_snake.is_alive = False
                elif pos[1] <= 0 or pos[1] >= self.width:
                    self.own_snake.is_alive = False

            # Kill the snake if it's head is inside itself.
            if self.own_snake.positions.count(self.own_snake.positions[-1]) >= 2:
                self.own_snake.is_alive = False

            self.window.refresh()
        self.stop_game()

    # gets run after the match is over.
    # Shows a message when the game is over and consequently stops the whole match.
    def stop_game(self):
        # Draw start messages
        first_message = "Game Over!"
        h, w = self.window.getmaxyx()
        x = int(w / 2 - len(first_message) / 2)
        y = int(h / 2)
        self.window.attron(curses.color_pair(2))
        self.window.addstr(y, x, first_message)
        self.window.attroff(curses.color_pair(2))
        self.window.refresh()

        time.sleep(1)
        x = int(w / 2 - len(self.game_over_reason) / 2)
        y = int(h / 2 + 1)
        self.window.attron(curses.color_pair(1))
        self.window.addstr(y, x, self.game_over_reason)
        self.window.attroff(curses.color_pair(1))
        self.window.refresh()
        time.sleep(2)

        self.in_game = False
        self.own_snake.reset()

        if not self.game_over_reason == "You left.":
            self.disconnect(True)


class MultiMatchHost:
    def __init__(self, window, height, width, powerup_amount, snake_amount,password,own_snake):
        self.window = window
        self.height = height
        self.width = width
        self.running = True
        self.in_lobby = True
        self.in_game = False
        # [client, username, positions, messages, is_alive, Time to last receive]
        self.players = []
        self.death_order = []
        self.own_snake = own_snake
        # The maximum amount of seconds before stopping kicking a client when there isn't any data received.
        self.max_client_delay = 2.5
        self.LAN_ip = socket.gethostbyname(socket.gethostname())
        self.WAN_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
        self.powerups = [PowerUp(possible_powerups.get("random"), [height - 1, width - 1]) for _ in
                         range(powerup_amount)]
        self.snake_amount = snake_amount
        self.password = password
        self.socket = socket.socket()
        self.socket.bind((str(socket.gethostbyname(socket.gethostname())),GAME_PORT))
        self.socket.listen(5)
        threading.Thread(target=self.input_loop).start()
        threading.Thread(target=self.draw_lobby).start()

        self.accept_clients()

    # basically causes the match to stop.
    def disconnect(self, reconnect):
        global auto_reconnect
        auto_reconnect = reconnect
        self.window.clear()
        self.running = False
        self.socket.close()

    # Deals with the keyboard inputs of the host while in the lobby
    def input_loop(self):
        global auto_reconnect
        while self.running:
            key = self.window.getch()

            if self.in_lobby:
                if key == curses.KEY_ENTER or key == 10 or key == 13:
                    # Make sure there is at least one other player before starting the game.
                    if len(self.players) >= 1:
                        # This breaks the draw_lobby() loop, and starts start_game()
                        self.in_lobby = False

                elif key == 27:  # 27 = ESC or ALT
                    for client in [x[0] for x in self.players]:
                        try:
                            client.send(b'Kick')
                        except:
                            pass
                    self.disconnect(False)

            elif self.in_game:
                if key == curses.KEY_UP:
                    self.own_snake.set_direction([-1, 0])
                elif key == curses.KEY_DOWN:
                    self.own_snake.set_direction([1, 0])
                elif key == curses.KEY_LEFT:
                    self.own_snake.set_direction([0, -1])
                elif key == curses.KEY_RIGHT:
                    self.own_snake.set_direction([0, 1])
                elif key == 27:  # 27 = ESC or ALT
                    auto_reconnect = False
                    # Kill all snakes which automatically stops the game from the draw_game() loop.
                    for player in self.players:
                        player[4] = False
                        self.death_order.append(self.players.index(player))
                    self.own_snake.is_alive = False
                    if -1 not in self.death_order:
                        self.death_order.append(-1)

    # kill client snake if it has lost connection.
    def connection_lost_check(self, player_index):
        while self.running and self.in_game:
            if self.players[player_index][5] > self.max_client_delay:
                self.players[player_index][4] = False
                self.death_order.append(player_index)
                break
            time.sleep(0.5)
            self.players[player_index][5] += 0.5

    # Receives client info from the client.
    def recv_client_data(self, client):

        try:
            while self.running and self.in_game:
                try:
                    data = client.recv(1024)
                    data = pickle.loads(data)
                except:
                    continue

                self.players[[x[0] for x in self.players].index(client)][5] = 0
                # # Set the position of the client snake.
                for player in self.players:
                    if player[0] == client:
                        player[2] = data[0]
                if data[1]:
                    for msg in data[1]:
                        # Check if the client picked up a powerup, if so remove it from the powerups.
                        if msg.startswith("pickup"):
                            cords = msg.replace("pickup","").replace("[","").replace("]","")
                            for i, powerup in enumerate(self.powerups):
                                if powerup.position == [int(cords.split(", ")[0]),int(cords.split(", ")[1])]:
                                    self.powerups.pop(i)
                                    self.powerups.append(PowerUp(random.choice(list(possible_powerups.values())),[self.height-1,self.width-1]))
                        elif msg == "dead":
                            index = [x[0] for x in self.players].index(client)

                            # Check if the snake already is dead.
                            if index not in self.death_order:
                                self.players[index][4] = False
                                self.death_order.append(index)

        except Exception as e:

            messagebox.showinfo("Error while receiving data from client ", str(e))

    # Sends game info to the client.
    def send_client_data(self, client):
        time.sleep(0.5)
        while self.running and self.in_game:
            try:
                personal_messages = self.players[[x[0] for x in self.players].index(client)][3]
                # format = [positions,powerups,messages]
                data = [list([self.own_snake.positions]+[x[2] for x in self.players if not x[0] == client]),self.powerups,personal_messages]
                client.send(pickle.dumps(data))
            except:
                break

    # Shows a messages the the game is starting.
    # Notifies all clients that the game is starting
    # and starts background threads for receiving and sending from and to every client.
    def start_game(self):
        # Send the start signal to the clients.
        for client in [x[0] for x in self.players]:
            client.send(b'Start')

        # Draw start messages
        self.window.clear()
        first_message = "Alright, we're gonna start."
        second_message = "Here we go!"
        h, w = self.window.getmaxyx()
        x = int(w / 2 - len(first_message) / 2)
        y = int(h / 2)
        self.window.attron(curses.color_pair(2))
        self.window.addstr(y, x, first_message)
        self.window.attroff(curses.color_pair(2))
        self.window.refresh()
        time.sleep(1)
        x = int(w / 2 - len(second_message) / 2)
        y = int(h / 2 + 1)
        self.window.attron(curses.color_pair(1))
        self.window.addstr(y, x, second_message)
        self.window.attroff(curses.color_pair(1))
        self.window.refresh()
        time.sleep(2)

        spacer = int(1/(len(self.players)+1)*self.height)

        # Send the y start positions to the client snakes.
        for i, client in enumerate([x[0] for x in self.players]):
            client.send(str(1+spacer+i*spacer).encode())

        self.in_game = True
        self.own_snake.is_alive = True

        for player in self.players:
            threading.Thread(target=self.recv_client_data, args=(player[0],)).start()
            threading.Thread(target=self.send_client_data, args=(player[0],)).start()
            threading.Thread(target=self.connection_lost_check, args=(self.players.index(player),)).start()

        try:
            self.draw_game()
        except Exception as e:
            messagebox.showinfo("IN HOST START_GAME", str(e))

    # Draws the lobby and continuously sends lobby info to the clients.
    def draw_lobby(self):
        while self.running and self.in_lobby:
            self.window.clear()

            h, w = self.window.getmaxyx()

            left_border = int(w / 2 - self.width / 2)
            right_border = int(w / 2 + self.width / 2)
            top_border = int(h / 2 - self.height / 2)
            bottom_border = int(h / 2 + self.height / 2)
            topleft = [top_border, left_border]
            bottomright = [bottom_border, right_border]

            textpad.rectangle(self.window, topleft[0], topleft[1], bottomright[0], bottomright[1])

            ip_text = "LAN IP: " + str(self.LAN_ip)+" --- "+"WAN IP: "+ str(self.WAN_ip)

            self.window.attron(curses.color_pair(1))
            self.window.addstr(top_border, left_border + 1, ip_text)
            self.window.attroff(curses.color_pair(1))

            # Show the host that the game can be started when there are one or more other players.
            if len(self.players) >= 1:
                self.window.attron(curses.color_pair(3))
                self.window.addstr(bottom_border+2, int(w/2-len("Press 'ENTER' to start the game!")/2), "Press 'ENTER' to start the game!")
                self.window.attroff(curses.color_pair(3))

            x = left_border+2
            # Display your own snake
            self.window.attron(curses.color_pair(4))
            self.window.addstr(top_border+3, x, "(YOU)(HOST) Snake 1" + " -- " + str(username))
            self.window.attroff(curses.color_pair(4))

            # Display all other client's snakes.
            for i, player in enumerate(self.players):
                self.window.attron(curses.color_pair(1))
                self.window.addstr(top_border+i+4, x, "Snake "+str(i+2) +" -- "+ player[1])
                self.window.attroff(curses.color_pair(1))
                try:
                    # Send a list of all client ip's to every client.
                    player[0].send(pickle.dumps([str(username)]+list([x[1] for x in self.players])))
                except:
                    # The player has disconnected, remove him from the list.
                    self.players.pop(i)

            # Prevent spamming the clients
            time.sleep(0.5)

            if len(self.players) == self.snake_amount:
                # this starts the game.
                break

            self.window.refresh()
        if self.running:
            self.start_game()

    # Kill the snake if it collides with itself or an other snake.
    def snake_collide_check(self):

        all_positions = [x[2] for x in self.players] + [self.own_snake.positions]
        for i_2, player in enumerate(self.players):
            all_other_snake_positions = []
            for i, all_snake_pos in enumerate(all_positions):
                if not i == i_2:
                    for pos in all_snake_pos:
                        all_other_snake_positions.append(pos)
            # Makes sure that the snake has positions.
            if len(player[2]) >= 1:
                if player[2][-1] in all_other_snake_positions:
                    player[3].append("kill")

        all_other_snake_positions = []
        for all_snake_pos in all_positions[:-1]:
            for pos in all_snake_pos:
                all_other_snake_positions.append(pos)

        if self.own_snake.positions[-1] in all_other_snake_positions:
            self.own_snake.is_alive = False
            if -1 not in self.death_order:
                self.death_order.append(-1)

        # Kill the snake if it's head is inside itself.
        if self.own_snake.positions.count(self.own_snake.positions[-1]) >= 2:
            self.own_snake.is_alive = False
            if -1 not in self.death_order:
                self.death_order.append(-1)

    # Deals with clients that want to connect to the lobby.
    def accept_clients(self):
        while self.running and self.in_lobby:
            try:
                client, addr = self.socket.accept()
            except:
                continue
            data = pickle.loads(client.recv(1024))
            password = data[0]
            user = data[1]
            # Check if the password was correct.
            if self.password == "" or password == self.password:
                # Check if there already is a player with the same name.
                if user in [ x[1] for x in self.players]+[username]:
                    client.send(b'Duplicate name')
                    client.close()
                else:
                    client.send(b'Acces Granted')
                    time.sleep(0.1)
                    client.send(pickle.dumps([self.height, self.width]))
                    self.players.append([client, user, [], [], True, 0])
            else:
                client.send(b'Acces Denied')
                client.close()

    # Draws the game while it is running.
    def draw_game(self):
        while self.running and self.in_game:

            # Draws the playing field.
            h, w = self.window.getmaxyx()
            left_border = int(w / 2 - self.width / 2)
            right_border = int(w / 2 + self.width / 2)
            top_border = int(h / 2 - self.height / 2)
            bottom_border = int(h / 2 + self.height / 2)
            topleft = [top_border, left_border]
            bottomright = [bottom_border, right_border]
            self.window.clear()
            textpad.rectangle(self.window, topleft[0], topleft[1], bottomright[0], bottomright[1])

            # Draw the Score
            score = self.own_snake.length - 5
            score_text = "Score: " + str(score)
            self.window.attron(curses.color_pair(1))
            self.window.addstr(top_border, left_border + 1, score_text)
            self.window.attroff(curses.color_pair(1))

            # Draw The PowerUps
            for powerup in self.powerups:
                self.window.attron(curses.color_pair(powerup.color))
                self.window.addstr(top_border + powerup.position[0], left_border + powerup.position[1], powerup.symbol)
                self.window.attroff(curses.color_pair(powerup.color))

            # Draw your own snake.
            for pos in self.own_snake.positions:
                self.window.attron(curses.color_pair(4))
                self.window.addstr(top_border + pos[0], left_border + pos[1], snake_display_symbol)
                self.window.attroff(curses.color_pair(4))

            # Draw the client snakes.
            for positions in [x[2] for x in self.players]:
                try:
                    for pos in positions:
                        self.window.addstr(top_border + pos[0], left_border + pos[1], snake_display_symbol)
                except:
                    # Still got no positions from this snake.
                    pass

            # Draw the scoreboard
            self.window.addstr(top_border, right_border + 2, "SCOREBOARD")
            self.window.addstr(top_border + 1, right_border + 2, username + " : " + str(self.own_snake.length))
            for i, player in enumerate(self.players):
                self.window.addstr(top_border + 2 + i, right_border + 2,
                                       player[1] + " : " + str(len(player[2])))

            # Apply powerups to your own snake.
            for powerup in self.powerups:
                if powerup.position in self.own_snake.positions:
                    self.own_snake.apply_powerup(powerup)
                    self.powerups.remove(powerup)
                    self.powerups.append(PowerUp(random.choice(list(possible_powerups.values())), [self.height - 1, self.width - 1]))

            # Check if the host snake collided with the walls.
            for pos in self.own_snake.positions:
                # Kill the snake when it's out of the window.
                if pos[0] <= 0 or pos[0] >= self.height:
                    self.own_snake.is_alive = False
                    if -1 not in self.death_order:
                        self.death_order.append(-1)
                elif pos[1] <= 0 or pos[1] >= self.width:
                    self.own_snake.is_alive = False
                    if -1 not in self.death_order:
                        self.death_order.append(-1)

            # # Count all dead snakes to indicate if all snakes are dead.
            # dead_snakes = 0
            # if not self.own_snake.is_alive:
            #     dead_snakes += 1
            # for player in self.players:
            #     if not player[4]:
            #         dead_snakes += 1
            #
            # # Stop the game if all snakes are dead.
            # if dead_snakes == (len(self.players)+1):
            #     self.stop_game()

            if len(self.death_order) == (len(self.players)+1):
                self.stop_game()

            # Checks for colliding snakes.
            self.snake_collide_check()
            self.window.refresh()

    # gets run after the match is over.
    # Shows a message when the game is over and consequently stops the whole match.
    def stop_game(self):
        try:

            # Determine who won.
            max_len = len(max([x[2] for x in self.players]+[self.own_snake.positions], key=len))

            longest_snakes = []
            winner = "NOT FOUND!"

            # add all snakes with the max length to longest_snakes.
            for positions in [x[2] for x in self.players]+[self.own_snake.positions]:
                if len(positions) == max_len:
                    longest_snakes.append(positions)

            # Check for snakes with equal lenghts.
            latest_death_pos = -1
            if len(longest_snakes) > 1:

                for longest_snake in longest_snakes:
                    if longest_snake == self.own_snake.positions:
                        death_position = self.death_order.index(-1)
                        if death_position > latest_death_pos:
                            latest_death_pos = death_position
                            winner = username

                    else:
                        index = [x[2] for x in self.players].index(longest_snake)
                        death_position = self.death_order.index(index)
                        if death_position > latest_death_pos:
                            latest_death_pos = death_position
                            winner = self.players[index][1]

            else:
                if longest_snakes[0] == self.own_snake.positions:
                    winner = username
                else:
                    index = [x[2] for x in self.players].index(longest_snakes[0])
                    winner = self.players[index][1]

            for player in self.players:
                player[3].append("stop "+winner)
                # Draw start messages
            first_message = "Game Over!"
            second_message = f"{winner} won!"
            h, w = self.window.getmaxyx()
            x = int(w / 2 - len(first_message) / 2)
            y = int(h / 2)
            self.window.attron(curses.color_pair(2))
            self.window.addstr(y, x, first_message)
            self.window.attroff(curses.color_pair(2))
            self.window.refresh()

            time.sleep(1)
            x = int(w / 2 - len(second_message) / 2)
            y = int(h / 2 + 1)
            self.window.attron(curses.color_pair(1))
            self.window.addstr(y, x, second_message)
            self.window.attroff(curses.color_pair(1))
            self.window.refresh()

            time.sleep(2)

            self.in_game = False
            self.own_snake.reset()
            self.disconnect(True)
        except Exception as e:
            messagebox.showinfo("in stop_game", str(e))



class PowerUp:
    def __init__(self, dict, pos_max):
        self.max_y = pos_max[0]
        self.max_x = pos_max[1]
        self.position = [random.randint(1, self.max_y),random.randint(1,self.max_x)]
        self.used = False

        for k,v in dict.items():
            setattr(self, k, v)

        if self.kind == "random":
            new_self = PowerUp(random.choice(list(possible_powerups.values())),pos_max)
            self.__dict__.update(new_self.__dict__)


if __name__ == '__main__':

    screen = curses.initscr()
    curses.start_color()
    curses.init_pair(1, positive_color, curses.COLOR_BLACK)
    curses.init_pair(2, negative_color, curses.COLOR_BLACK)
    curses.init_pair(3, neutral_color, curses.COLOR_BLACK)
    curses.init_pair(4, selection_color, curses.COLOR_BLACK)
    curses.beep()
    curses.beep()
    screen.timeout(DELAY)
    screen.keypad(1)
    curses.noecho()
    curses.curs_set(0)
    screen.border(0)
    curses.curs_set(0)

    try:
        own_snake = Snake()
        navigator = Navigation(screen, own_snake)
        save_data()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(str(e)+ str(exc_type)+ str(fname)+ str(exc_tb.tb_lineno))
    curses.endwin()

