import game
import persistance


def exactly_once(func):
    has_been_executed = False

    def func_prime(*args, **kwargs):
        nonlocal has_been_executed
        if not has_been_executed:
            has_been_executed = True
            return func(*args, **kwargs)
    return func_prime


class Handler:

    @classmethod
    @exactly_once
    def initial_prompt(cls):
        return cls._initial_prompt()

    @staticmethod
    def _initial_prompt():
        pass

    def pre_prompt(self):
        pass

    def process_command(self, command):
        raise NotImplemented()

    def get_next_handler(self):
        raise NotImplemented()

    @staticmethod
    def process_help():
        pass


class ParentHandler(Handler):

    def callback_from_child(self):
        pass


class SetupHandler(Handler):
    def __init__(self):
        self.setup_phase = game.SetupPhase(game.State())

    @staticmethod
    def _initial_prompt():
        return "Let's play some Catan! 'addplayer's and then 'done' to begin"

    def process_command(self, command):
        keyword, args = split_input(command)
        if keyword == "help":
            SetupHandler.process_help()
        elif keyword == "addplayer":
            self.process_add_player(args)
        elif keyword == "setstartingplayer":
            self.process_set_starting_player(args)
        elif keyword.lower() == "checkstartingplayer":
            self.process_check_starting_player()
        elif keyword == "done":
            self.process_done()
        else:
            print("Unrecognized command; type help for a list")

    @staticmethod
    def process_help():
        print("help\n"
              "addplayer <playername>\n"
              "setstartingplayer <playername>\n"
              "checkstartingplayer\n"
              "done")

    def process_add_player(self, name):
        if len(name.strip()) == 0:
            print("Must provide a playername")
            return
        self.setup_phase.add_player(name)

    def process_set_starting_player(self, name):
        try:
            self.setup_phase.set_starting_player(name)
        except ValueError:
            print("Could not find player {0}".format(name))

    def process_check_starting_player(self):
        starting_player_name = self.setup_phase.get_starting_player()
        print("Starting player: {0}".format(starting_player_name))

    def process_done(self):
        self.setup_phase.finish_setup()

    def get_next_handler(self):
        if self.setup_phase.done:
            state = self.setup_phase.state
            build_phase = game.BuildPhase(state)
            return BuildPhaseHandler(build_phase)
        return self



class BuildPhaseHandler(ParentHandler):
    def __init__(self, build_phase):
        self.build_phase = build_phase
        self._resources = None
        self.port_check_handler = None

    @staticmethod
    def _initial_prompt():
        return "Starting the build phase!"

    def pre_prompt(self):
        current_player_name = self.build_phase.current_player().name
        print("What resources does {0} collect on their new settlement?".format(current_player_name))

    def process_command(self, command):
        if command == "help":
            BuildPhaseHandler.process_help()
        else:
            self.process_settlement(command)

    @staticmethod
    def process_help():
        print("help\n <roll1> [<roll2> [<roll3>]]")

    def process_settlement(self, args):
        try:
            resources = [int(i) for i in args.strip().split(" ")]
            if len(resources) > 3:
                print("Mmm, can't build a settlement that collects so many resources")
            self.port_check_handler = PortCheckHandler(self)
            self._resources = resources
        except:
            print("Couldn't understand that resource string")
            return self

    def callback_from_child(self):
        port = self.port_check_handler.result
        self.build_phase.build_starting_settlement(self._resources, port)
        self.port_check_handler = None

    def get_next_handler(self):
        if self.build_phase.done:
            state = self.build_phase.state
            play_phase = game.PlayPhase(state)
            return PlayPhaseHandler(play_phase)
        if self.port_check_handler is not None:
            return self.port_check_handler
        return self


class PortCheckHandler(Handler):
    def __init__(self, parent_handler):
        self.result = None
        self.done = False
        self.parent_handler = parent_handler

    def pre_prompt(self):
        print("What port? (2/3/n)")

    def process_command(self, command):
        if command == "help":
            PortCheckHandler.process_help()
        elif command == "2":
            self.result = game.Assets.PORT2
            self.done = True
        elif command == "3":
            self.result = game.Assets.PORT3
            self.done = True
        elif command == "n":
            self.result = None
            self.done = True
        else:
            print("unrecognized command")
        return self

    @staticmethod
    def process_help():
        print("help\n2\n3\nn")

    def get_next_handler(self):
        if self.done:
            self.parent_handler.callback_from_child()
            return self.parent_handler.get_next_handler()
        return self


class UpgradeHandler(Handler):

    def __init__(self, play_phase, parent_handler):
        self.play_phase = play_phase
        self.settlements = self.play_phase.get_settlements()
        self.parent_handler = parent_handler
        self.done = False

    def pre_prompt(self):
        current_player_name = self.play_phase.current_player().name
        print("Upgrading a settlement belonging to {0}".format(current_player_name))
        print("Which settlement?\n")
        for i in range(len(self.settlements)):
            settlement = self.settlements[i]
            print("{0}: {1}".format(i, settlement))

    def process_command(self, command):
        if command == 'help':
            UpgradeHandler.process_help()
        else:
            self.process_number(command)

    def process_number(self, number):
        try:
            index = int(number)
            if 0 <= index < len(self.settlements):
                self.play_phase.upgrade(self.settlements[index])
                self.done = True
            else:
                print("invalid selection")
        except ValueError:
            print("unrecognized command")
            return self

    @staticmethod
    def process_help():
        return "help\n<int>\nnevermind"

    def get_next_handler(self):
        if self.done:
            self.parent_handler.callback_from_child()
            return self.parent_handler
        return self


class PlayPhaseHandler(Handler):
    def __init__(self, play_phase):
        self.play_phase = play_phase
        self.port_check_handler = None
        self.upgrade_handler = None
        self._resources_for_build = None

    def pre_prompt(self):
        if not self.play_phase.has_rolled():
            return "Roll to start the game"
        current_player_name = self.play_phase.current_player().name
        return "Would {0} like to build? Roll to start the next turn".format(current_player_name)

    def process_command(self, command):
        keyword, args = split_input(command)
        if keyword == "help":
            PlayPhaseHandler.process_help()
        if keyword == "roll":
            self.process_roll(args)
        elif keyword == "build":
            return self.process_build(args)
        elif keyword == "upgrade":
            return self.process_upgrade()
        elif keyword == "devcard":
            self.process_dev_card()
        elif keyword == "save":
            self.process_save(args)
        return self

    @staticmethod
    def process_help():
        print("help\n"
              "roll <rollnum>\n"
              "build <srcroll1> [<srcroll2> [<srcroll3>]]\n"
              "upgrade\n"
              "devcard\n"
              "save")

    def process_roll(self, roll):
        try:
            self.play_phase.roll(roll)
        except ValueError or game.InvalidRoll:
            print("A roll should be an integer from 2 to 12")

    def process_build(self, args):
        try:
            self._resources_for_build = [int(roll) for roll in args.split(" ")]
            self.port_check_handler = PortCheckHandler(self)
        except ValueError:
            print("resources gained should be specified as an ' ' delimited set of ints")

    def process_upgrade(self):
        self.upgrade_handler = UpgradeHandler(self.play_phase, self)

    def process_dev_card(self):
        self.play_phase.get_dev_card()

    def process_save(self, args):
        if args.strip() == "":
            print("Will save to a new file")
            args = None
        persistance.save(self.play_phase.state, args)

    def get_next_handler(self):
        if self.port_check_handler is not None:
            return self.port_check_handler
        if self.upgrade_handler is not None:
            return self.upgrade_handler
        return self

    def callback_from_child(self):
        if self.port_check_handler is not None:
            self.play_phase.build_settlement(self._resources_for_build, self.port_check_handler.result)
        self._resources_for_build = None
        self.port_check_handler = None
        self.upgrade_handler = None


def split_input(inpt):
    input_array = inpt.split(" ")
    return input_array[0], " ".join(input_array[1:])


def prompt():
    print("> ", end="")


def output(text):
    if text is not None:
        print(text)


def repl():
    old_handler = None
    handler = SetupHandler()
    while handler is not None:
        # try:
            if old_handler != handler:
                output(handler.initial_prompt())
            output(handler.pre_prompt())
            prompt()
            command = input()
            handler.process_command(command)
            handler, old_handler = handler.get_next_handler(), handler
        # except Exception as e:
        #     output("something broke...")
        #     output(e)


def main():
    repl()

if __name__ == '__main__':
    repl()
