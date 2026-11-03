class GameState:
    def __init__(self):
        self.stats = {
            "bondad": 0,
            "curiosidad": 0,
            "dinero": 0,
        }

        self.flags = {
            "vio_mariposa": False,
        }

    def add(self, key, value=1):
        self.stats[key] = self.stats.get(key, 0) + value

    def add_money(self, amount):
        """
        Agrega dinero a la partida.
        """

        self.stats["dinero"] = (
            self.stats.get("dinero", 0)
            + amount
        )

    def get_money(self):
        """
        Devuelve el dinero acumulado.
        """

        return self.stats.get("dinero", 0)

    def set_flag(self, key, value=True):
        self.flags[key] = value