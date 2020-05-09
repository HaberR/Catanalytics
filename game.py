class InvalidRoll(Exception):
    pass


class InvalidTurn(Exception):
    pass

class NotEnoughPlayers(Exception):
    pass


class Phase:
    def __init__(self, state):
        self.state = state
        self.done = False


class SetupPhase(Phase):

    def add_player(self, name):
        self.state.players.append(Player(name))

    def set_starting_player(self, name):
        players = self.state.players
        num_players = len(players)
        current_order = [p.name for p in players]
        starting_index = current_order.index(name)
        new_order = [players[i % num_players] for i in range(starting_index, starting_index + num_players)]
        self.state.players = new_order

    def get_starting_player(self):
        return self.state.players[0].name

    def finish_setup(self):
        if len(self.state.players) == 0:
            raise NotEnoughPlayers
        self.done = True


class BuildPhase(Phase):
    def __init__(self, state):
        Phase.__init__(self, state)
        self._num_players = len(self.state.players)
        self._raw_index = 0

    def build_starting_settlement(self, added_resources, port=None):
        if self.done:
            raise Exception("Build phase is over. Can't build more")
        player = self.current_player()
        player.build_starting_settlement(added_resources, port)
        self._raw_index += 1
        self.done = self._raw_index == self._num_players * 2

    def current_player(self):
        true_index = BuildPhase.raw_index_to_true_index(self._raw_index, self._num_players * 2)
        return self.state.players[true_index]

    # num indices must be even
    @staticmethod
    def raw_index_to_true_index(raw_index, num_indices):
        peak_index = (num_indices - 1)/2
        peak_value = num_indices / 2 - 1
        return int(peak_value - int(abs(raw_index - peak_index)))


class PlayPhase(Phase):

    def __init__(self, state):
        Phase.__init__(self, state)
        # -1 so the first roll happens on the 0th turn
        self.current_turn = -1

    def roll(self, roll):
        self.current_turn += 1
        self.state.roll_tracker.add_roll(roll)

    def build_settlement(self, added_resources, port=None):
        player = self.current_player()
        player.build_settlement(self.current_turn, added_resources, port)

    def upgrade(self, settlement):
        player = self.current_player()
        player.upgrade_settlement(self.current_turn, settlement)

    def get_settlements(self):
        player = self.current_player()
        return player.settlement_auditor.get_for_turn(self.current_turn)

    def get_dev_card(self):
        player = self.current_player()
        player.asset_auditor.add_on_turn(self.current_turn, Assets.DEV_CARD)

    def current_player(self):
        num_players = len(self.state.players)
        return self.state.players[self.current_turn % num_players]

    def has_rolled(self):
        return self.current_turn >= 0


class State:
    def __init__(self):
        self.roll_tracker = RollTracker()
        self.players = []


class RollTracker:

    def __init__(self):
        self.rolls = []

    def add_roll(self, roll):
        roll = int(roll)
        if 2 <= roll <= 12:
            self.rolls.append(roll)
        else:
            raise InvalidRoll()

    def get_roll(self, roll_number):
        return self.rolls[roll_number]


class Player:
    def __init__(self, name):
        self.name = name
        self.resource_auditor = DictionaryAuditor({})
        self.asset_auditor = DictionaryAuditor({})
        self.settlement_auditor = ListAuditor([])
        self.city_auditor = ListAuditor([])

    def build_starting_settlement(self, added_resources, port = None):
        settlement = Structure(added_resources)
        self.resource_auditor.add_to_starter(added_resources)
        self.settlement_auditor.add_to_starter(settlement)
        if port is not None:
            self.asset_auditor.add_to_starter(port)

    def build_settlement(self, turn, added_resources, port = None):
        settlement = Structure(added_resources)
        self.resource_auditor.add_on_turn(turn, added_resources)
        self.settlement_auditor.add_on_turn(turn, settlement)
        if port is not None:
            self.asset_auditor.add_on_turn(turn, port)

    def get_development_card(self, turn):
        self.asset_auditor.add_on_turn(turn, Assets.DEV_CARD)

    def upgrade_settlement(self, turn, settlement):
        self.settlement_auditor.remove_on_turn(turn, settlement)
        self.city_auditor.add_on_turn(turn, settlement)


class Assets:
    DEV_CARD = "Dev Card"
    PORT2 = "2-Port"
    PORT3 = "3-Port"


class Structure:
    def __init__(self, resources):
        self.resources = resources

    def __repr__(self):
        return str(self.resources)

    # @classmethod
    # def upgrade(cls, structure):
    #     resources = {
    #         roll: 2 * value
    #         for roll, value in structure.resources
    #     }
    #     return Structure(resources)


class Auditor:
    def __init__(self, starter):
        self.starting_items = starter
        self.all_items_for_update = []
        self.turn_for_update = []

    def add_to_starter(self, added_items):
        added_items = self.__class__.perform_conversion(added_items)
        self.starting_items = self.__class__._add(self.starting_items, added_items)
    
    def add_on_turn(self, turn, added_items):
        added_items = self.__class__.perform_conversion(added_items)
        old_items = self.get_for_turn(turn)
        all_items = self.__class__._add(old_items, added_items)
        self._update_for_turn(turn, all_items)

    def get_for_turn(self, turn):
        if len(self.turn_for_update) == 0:
            return self.starting_items
        # validation
        if turn < 0:
            raise InvalidTurn("No negative turns")
        
        # search backward for the last update before this turn
        update_index = -1
        while self.turn_for_update[update_index] > turn:
            update_index -= 1
        return self.all_items_for_update[update_index]
    
    def remove_on_turn(self, turn, removed_item):
        old_items = self.get_for_turn(turn)
        all_items = self.__class__._remove(old_items, removed_item)
        self._update_for_turn(turn, all_items)
        
        
    def _update_for_turn(self, turn, all_items):
        self.all_items_for_update.append(all_items)
        self.turn_for_update.append(turn)

    @classmethod
    def perform_conversion(cls, items):
        return items

    @classmethod
    def _add(cls, items_one, items_two):
        raise NotImplemented()

    @classmethod
    def _remove(cls, items_one, items_two):
        raise NotImplemented()


class DictionaryAuditor(Auditor):

    @classmethod
    def perform_conversion(cls, items):
        # convert to dictionary if not
        if not isinstance(items, dict):
            if isinstance(items, list):
                # ugly way to turn list into dict
                items = {item: len([i for i in items if i == item]) for item in items}
            else:
                items = {items: 1}
        return items

    @classmethod
    def _add(cls, items_one, items_two):
        # assumed that items_one and items_two are both {}: key -> count
        items_one_keys = set(items_one.keys())
        items_two_keys = set(items_two.keys())
        keys = items_one_keys.union(items_two_keys)
        return {
            key: items_one.get(key, 0) + items_two.get(key, 0)
            for key in keys
        }


class ListAuditor(Auditor):

    @classmethod
    def perform_conversion(cls, items):
        return items if isinstance(items, list) else [items]
    
    @classmethod
    def _add(cls, items_one, items_two):
        return items_one + items_two

    @classmethod
    def _remove(cls, item_list, item):
        copied_list = item_list[:]
        copied_list.remove(item)
        return copied_list
    
#
# class StructureAuditor(Auditor):
#     def add(cls, items_one, items_two):
#         items_one.append(items_two)
#
#     def remove_on_turn(self, turn, removed_item):
#         old_items =


# class AssetAuditor(Auditor):
#
#     @classmethod
#     def add(cls, assets_one, assets_two):


#
# class BasicResourceAuditor:
#
#     def __init__(self):
#         # resource mapping for the ith update
#         # indices look like
#         # {
#         #     roll #: # resources
#         # }
#         self.resources_on_update = []
#         # turn at which the ith update took place
#         self.turn_for_update = []
#
#     def add_resources(self, turn, added_resources):
#         old_resources = self.resources_on_update[-1]
#         new_resources = {
#             roll: old_resources.get(roll, 0) + added_resources.get(roll, 0)
#             for roll in range(2,12)
#         }
#         self.resources_on_update.append(new_resources)
#         self.turn_for_update.append((turn))
#
#     def get_resources_map(self, turn):
#         # validation
#         if self.turn_for_update[-1] < turn:
#             raise InvalidTurn("That turn is too large")
#         if turn < 0:
#             raise InvalidTurn("No negative turns")
#         # search backward for the last update before this turn
#         update_index = -1
#         while self.turn_for_update[update_index] > turn:
#             update_index -= 1
#         return self.resources_on_update[update_index].copy()
#