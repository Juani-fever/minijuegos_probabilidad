import random

from probability.conditional import ValveProbability


class PressureSystem:
    """
    Motor de presión del minijuego.

    La presión cambia por tres elementos:

    1. Tendencia natural del sistema.
    2. Efecto de las cuatro válvulas.
    3. Una perturbación aleatoria.

    La configuración de válvulas determina el cambio neto de presión.

    Ese cambio neto permite calcular las probabilidades condicionadas
    de estabilidad, aumento, peligro y descenso.
    """

    # Debe coincidir con las perturbaciones utilizadas
    # por ValveProbability.
    NOISE_VALUES = (-2, -1, 0, 1, 2)

    # A partir de esta presión consideramos que el sistema
    # entró en una situación crítica.
    DANGER_THRESHOLD = 85

    def __init__(self, scenario):
        self.scenario = scenario

        self.pressure = float(scenario.initial_pressure)

        self.target_min = scenario.target_min
        self.target_max = scenario.target_max

        self.effects = scenario.effects
        self.natural_drift = scenario.natural_drift

        self.last_noise = 0
        self.last_net_change = self.natural_drift

    def calculate_valve_change(self, valves):
        """
        Calcula el efecto producido exclusivamente
        por las cuatro válvulas.
        """

        change = 0

        for valve in ("A", "B", "C", "D"):
            is_open = valves[valve]

            change += self.effects[valve][is_open]

        return change

    def calculate_net_change(self, valves):
        """
        Calcula el cambio neto esperado de presión.

        Este valor depende directamente de la configuración
        elegida por el jugador.
        """

        return (
            self.natural_drift
            + self.calculate_valve_change(valves)
        )

    def calculate_event_probabilities(self, valves):
        """
        Calcula las probabilidades condicionadas por la
        configuración actual de las válvulas.

        Devuelve:

            P(estabilidad | configuración)
            P(aumento | configuración)
            P(peligro | configuración)
            P(descenso | configuración)
        """

        net_change = self.calculate_net_change(valves)

        return ValveProbability.calculate_event_probabilities(
            pressure=self.pressure,
            target_min=self.target_min,
            target_max=self.target_max,
            net_change=net_change,
            danger_threshold=self.DANGER_THRESHOLD,
        )

    def calculate_stability_probability(self, valves):
        """
        Devuelve:

            P(estabilidad | configuración)
        """

        probabilities = self.calculate_event_probabilities(
            valves
        )

        return probabilities["estabilidad"]

    def update(self, valves):
        """
        Actualiza la presión utilizando:

            presión nueva =
            presión actual
            + cambio neto
            + perturbación aleatoria
        """

        net_change = self.calculate_net_change(valves)

        noise = random.choice(self.NOISE_VALUES)

        self.last_net_change = net_change
        self.last_noise = noise

        self.pressure += net_change + noise

        # Limitamos la presión para evitar valores absurdos.
        self.pressure = max(
            0,
            min(110, self.pressure)
        )

        return self.pressure

    def get_status(self):
        """
        Devuelve el estado actual del sistema.
        """

        if self.pressure >= 100:
            return "EXPLOSION"

        if self.pressure >= self.DANGER_THRESHOLD:
            return "CRITICA"

        if self.pressure > self.target_max:
            return "ALTA"

        if self.pressure < self.target_min:
            return "BAJA"

        return "ESTABLE"

    def get_direction(self, valves):
        """
        Devuelve la tendencia de presión producida
        por la configuración actual.
        """

        change = self.calculate_net_change(valves)

        if change > 0:
            return "AUMENTANDO"

        if change < 0:
            return "DISMINUYENDO"

        return "EQUILIBRADA"

    def is_in_target_zone(self):
        """
        Indica si la presión actual está dentro
        del rango seguro.
        """

        return (
            self.target_min
            <= self.pressure
            <= self.target_max
        )

    def get_distance_to_target(self):
        """
        Calcula la distancia hasta la zona objetivo.
        """

        if self.pressure < self.target_min:
            return self.target_min - self.pressure

        if self.pressure > self.target_max:
            return self.pressure - self.target_max

        return 0

    def get_valve_effect(self, valve, is_open):
        """
        Devuelve el efecto de una válvula
        según esté abierta o cerrada.
        """

        return self.effects[valve][is_open]

    def get_net_change(self, valves):
        """
        Devuelve el cambio neto de presión.
        """

        return self.calculate_net_change(valves)