import math
import random


class ValveProbability:
    """
    Motor probabilístico del minijuego.

    Modelo:
    - La configuración elegida en las válvulas determina un cambio neto
      esperado de presión.
    - Cada segundo existe una perturbación aleatoria posible.
    - A partir de todas las perturbaciones posibles calculamos:

        P(estabilidad | configuración)
        P(aumento     | configuración)
        P(peligro     | configuración)

    La probabilidad de estabilidad obtenida para una configuración se usa
    después como p en cinco ensayos de Bernoulli independientes.
    """

    # Cinco perturbaciones equiprobables del sistema.
    NOISE_VALUES = (-2, -1, 0, 1, 2)

    @staticmethod
    def classify_event(
        current_pressure,
        next_pressure,
        target_min,
        target_max,
        danger_threshold=85,
    ):
        """
        Clasifica el resultado de una perturbación en un evento.
        """

        # Presión crítica o superior.
        if next_pressure >= danger_threshold:
            return "peligro"

        # Presión dentro de la zona segura.
        if target_min <= next_pressure <= target_max:
            return "estabilidad"

        # Presión fuera de la zona segura y aumentando.
        if next_pressure > current_pressure:
            return "aumento"

        # Presión fuera de la zona segura y disminuyendo.
        return "descenso"

    @classmethod
    def calculate_event_probabilities(
        cls,
        pressure,
        target_min,
        target_max,
        net_change,
        danger_threshold=85,
    ):
        """
        Calcula las probabilidades condicionadas por la configuración actual.

        Si C representa la configuración elegida por el jugador, entonces
        net_change representa D(C).

        El resultado representa:

            P(evento | C)

        Las cinco perturbaciones son equiprobables, por lo que cada una pesa
        1/5 en el cálculo.
        """

        counts = {
            "estabilidad": 0,
            "aumento": 0,
            "peligro": 0,
            "descenso": 0,
        }

        for noise in cls.NOISE_VALUES:
            next_pressure = pressure + net_change + noise

            event = cls.classify_event(
                pressure,
                next_pressure,
                target_min,
                target_max,
                danger_threshold,
            )

            counts[event] += 1

        total = len(cls.NOISE_VALUES)

        return {
            event: counts[event] / total
            for event in counts
        }

    @classmethod
    def calculate_stability_probability(
        cls,
        pressure,
        target_min,
        target_max,
        net_change,
        danger_threshold=85,
    ):
        """
        Calcula:

            P(estabilidad | configuración)

        Se mantiene este método para conservar compatibilidad
        con versiones anteriores del proyecto.
        """

        probabilities = cls.calculate_event_probabilities(
            pressure,
            target_min,
            target_max,
            net_change,
            danger_threshold,
        )

        return probabilities["estabilidad"]

    @staticmethod
    def bernoulli_success(
        previous_pressure,
        new_pressure,
        target_min,
        target_max,
        net_change=None,
    ):
        """
        Determina si un ensayo observado terminó en estabilidad.

        Se conserva para compatibilidad con versiones anteriores.
        """

        return target_min <= new_pressure <= target_max

    @staticmethod
    def trial(probability):
        """
        Realiza un ensayo de Bernoulli con probabilidad p.
        """

        return random.random() < probability

    @staticmethod
    def binomial_probability(n, k, probability):
        """
        Calcula:

            P(X = k)

        para:

            X ~ Binomial(n, p)
        """

        if n < 0:
            return 0.0

        if k < 0 or k > n:
            return 0.0

        if probability < 0 or probability > 1:
            return 0.0

        return (
            math.comb(n, k)
            * probability ** k
            * (1 - probability) ** (n - k)
        )

    @classmethod
    def binomial_at_least(cls, n, k, probability):
        """
        Calcula:

            P(X >= k)

        para:

            X ~ Binomial(n, p)
        """

        if n < 0:
            return 0.0

        if k < 0:
            k = 0

        if k > n:
            return 0.0

        total = 0.0

        for successes in range(k, n + 1):
            total += cls.binomial_probability(
                n,
                successes,
                probability,
            )

        return total

    @classmethod
    def calculate_test_probability(
        cls,
        successes,
        trials,
        probability,
    ):
        """
        Calcula la probabilidad acumulada de obtener al menos
        'successes' éxitos.
        """

        return cls.binomial_at_least(
            trials,
            successes,
            probability,
        )