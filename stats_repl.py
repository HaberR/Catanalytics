from repl import Handler, output
from matplotlib import pyplot as plt

class StatsHandler(Handler):
    def __init__(self, state):
        self.state = state

    @staticmethod
    def _initial_prompt():
        return "Analytics time!"

    def pre_prompt(self):
        pass

    def process_command(self, command):
        raise NotImplemented()

    def process_standings(self):

    def _plot_expected_collected(self):

    def _plot_actual_collected(self):

    def _plot_settlements_over_time(self):

    def _plot_cities_over_time(self):

    def get_next_handler(self):
        raise NotImplemented()

    @staticmethod
    def process_help():
        output("help\nstandings\novertime")
