import random


class ValveScenario:
    """
    Generador de escenarios aleatorios para el minijuego.

    El escenario tiene:

    - una presión inicial fuera del rango objetivo;
    - una tendencia natural del sistema;
    - cuatro válvulas con efectos diferentes;
    - una o dos configuraciones que permiten alcanzar
      el equilibrio real;
    - configuraciones de ajuste para llevar la presión
      hacia el rango objetivo.

    El escenario se verifica antes de entregarse al jugador
    para garantizar que sea resoluble.
    """

    VALVES = ("A", "B", "C", "D")

    def __init__(
        self,
        initial_pressure,
        target_min,
        target_max,
        natural_drift,
        effects,
        stable_solutions,
        adjustment_solutions,
    ):

        self.initial_pressure = initial_pressure
        self.target_min = target_min
        self.target_max = target_max

        self.natural_drift = natural_drift

        self.effects = effects

        self.stable_solutions = stable_solutions
        self.adjustment_solutions = adjustment_solutions

        # Una solución estable elegida para referencia interna.
        self.solution = random.choice(
            self.stable_solutions
        )

    # ============================================================
    # GENERACIÓN
    # ============================================================

    @classmethod
    def generate(cls):

        for _ in range(10000):

            # ----------------------------------------------------
            # RANGO OBJETIVO
            # ----------------------------------------------------

            target_center = random.randint(63, 67)

            target_min = target_center - 2
            target_max = target_center + 2

            # ----------------------------------------------------
            # PRESIÓN INICIAL
            #
            # Nunca comenzamos directamente dentro del rango.
            # ----------------------------------------------------

            if random.choice((True, False)):

                # Presión demasiado baja.
                initial_pressure = random.randint(
                    target_min - 10,
                    target_min - 5
                )

                # La tendencia natural también empuja hacia abajo.
                natural_drift = random.randint(
                    -6,
                    -4
                )

                direction = -1

            else:

                # Presión demasiado alta.
                initial_pressure = random.randint(
                    target_max + 5,
                    target_max + 10
                )

                # La tendencia natural empuja hacia arriba.
                natural_drift = random.randint(
                    4,
                    6
                )

                direction = 1

            # ----------------------------------------------------
            # EFECTOS DE LAS VÁLVULAS
            # ----------------------------------------------------

            effects = cls.generate_effects()

            # ----------------------------------------------------
            # BUSCAR CONFIGURACIONES DE EQUILIBRIO
            # ----------------------------------------------------

            stable_solutions = cls.find_stable_solutions(
                natural_drift,
                effects
            )

            # Queremos una o dos soluciones reales.
            if not (
                1
                <= len(stable_solutions)
                <= 2
            ):
                continue

            # ----------------------------------------------------
            # CONFIGURACIÓN CON TODO CERRADO
            #
            # Debe ser inestable y empujar en la dirección
            # equivocada.
            # ----------------------------------------------------

            all_closed = {
                "A": False,
                "B": False,
                "C": False,
                "D": False,
            }

            all_closed_change = (
                cls.calculate_change(
                    all_closed,
                    natural_drift,
                    effects
                )
            )

            # El signo debe coincidir con la dirección
            # que aleja al sistema del objetivo.
            if (
                all_closed_change * direction
                < 2
            ):
                continue

            # ----------------------------------------------------
            # CONFIGURACIONES PARA ACERCARSE AL OBJETIVO
            # ----------------------------------------------------

            adjustment_solutions = (
                cls.find_adjustment_solutions(
                    initial_pressure,
                    target_min,
                    target_max,
                    natural_drift,
                    effects,
                    direction
                )
            )

            if len(adjustment_solutions) < 2:
                continue

            # ----------------------------------------------------
            # ESCENARIO VÁLIDO
            # ----------------------------------------------------

            scenario = cls(
                initial_pressure=initial_pressure,
                target_min=target_min,
                target_max=target_max,
                natural_drift=natural_drift,
                effects=effects,
                stable_solutions=stable_solutions,
                adjustment_solutions=adjustment_solutions,
            )

            return scenario

        raise RuntimeError(
            "No se pudo generar un escenario válido."
        )

    # ============================================================
    # EFECTOS DE LAS VÁLVULAS
    # ============================================================

    @staticmethod
    def generate_effects():

        effects = {}

        # A = ENTRADA
        effects["A"] = {
            True: random.randint(4, 6),
            False: random.randint(-2, -1),
        }

        # B = ESCAPE
        effects["B"] = {
            True: random.randint(-6, -4),
            False: random.randint(1, 2),
        }

        # C = REGULACIÓN
        effects["C"] = {
            True: random.randint(1, 2),
            False: random.randint(-2, -1),
        }

        # D = SEGURIDAD
        effects["D"] = {
            True: random.randint(-8, -6),
            False: random.randint(2, 4),
        }

        return effects

    # ============================================================
    # CALCULAR CAMBIO TOTAL
    # ============================================================

    @classmethod
    def calculate_change(
        cls,
        configuration,
        natural_drift,
        effects,
    ):

        change = natural_drift

        for valve in cls.VALVES:

            is_open = configuration[valve]

            change += effects[valve][is_open]

        return change

    # ============================================================
    # CONFIGURACIONES ESTABLES
    # ============================================================

    @classmethod
    def find_stable_solutions(
        cls,
        natural_drift,
        effects,
    ):

        solutions = []

        for mask in range(16):

            configuration = {
                "A": bool(mask & 1),
                "B": bool(mask & 2),
                "C": bool(mask & 4),
                "D": bool(mask & 8),
            }

            change = cls.calculate_change(
                configuration,
                natural_drift,
                effects
            )

            # Equilibrio verdadero:
            # la presión deja de tener una tendencia
            # determinista a subir o bajar.
            if change == 0:

                # No permitimos que todo cerrado
                # sea la solución.
                if not any(configuration.values()):
                    continue

                solutions.append(configuration)

        return solutions

    # ============================================================
    # CONFIGURACIONES DE AJUSTE
    # ============================================================

    @classmethod
    def find_adjustment_solutions(
        cls,
        initial_pressure,
        target_min,
        target_max,
        natural_drift,
        effects,
        direction,
    ):

        solutions = []

        for mask in range(16):

            configuration = {
                "A": bool(mask & 1),
                "B": bool(mask & 2),
                "C": bool(mask & 4),
                "D": bool(mask & 8),
            }

            change = cls.calculate_change(
                configuration,
                natural_drift,
                effects
            )

            # No necesitamos una configuración
            # de equilibrio para esta etapa.
            if change == 0:
                continue

            # Si la presión está baja,
            # necesitamos que suba.
            if direction == -1 and change <= 0:
                continue

            # Si la presión está alta,
            # necesitamos que baje.
            if direction == 1 and change >= 0:
                continue

            # Evitamos ajustes demasiado pequeños.
            if abs(change) < 2:
                continue

            # Evitamos saltos demasiado violentos.
            if abs(change) > 7:
                continue

            if cls.can_reach_target(
                initial_pressure,
                target_min,
                target_max,
                change
            ):

                solutions.append(configuration)

        return solutions

    # ============================================================
    # COMPROBAR SI UN AJUSTE PUEDE LLEGAR AL RANGO
    # ============================================================

    @staticmethod
    def can_reach_target(
        initial_pressure,
        target_min,
        target_max,
        change,
    ):

        pressure = initial_pressure

        for _ in range(10):

            pressure += change

            if (
                target_min
                <= pressure
                <= target_max
            ):
                return True

            if pressure <= 0 or pressure >= 100:
                return False

            # Si nos pasamos del rango,
            # esta configuración no sirve como ajuste.
            if change > 0 and pressure > target_max:
                return False

            if change < 0 and pressure < target_min:
                return False

        return False

    # ============================================================
    # INFORMACIÓN
    # ============================================================

    def calculate_change_for(
        self,
        configuration
    ):

        return self.calculate_change(
            configuration,
            self.natural_drift,
            self.effects
        )

    def get_solution_change(self):

        return self.calculate_change_for(
            self.solution
        )

    def get_target_text(self):

        return (
            f"{self.target_min}-"
            f"{self.target_max} PSI"
        )

    # ============================================================
    # DEBUG
    # ============================================================

    def describe(self):

        print()
        print("================================")
        print("       NUEVO ESCENARIO")
        print("================================")

        print(
            f"Presión inicial: "
            f"{self.initial_pressure} PSI"
        )

        print(
            f"Objetivo: "
            f"{self.target_min}-"
            f"{self.target_max} PSI"
        )

        print(
            f"Tendencia natural: "
            f"{self.natural_drift:+d} PSI/s"
        )

        print()
        print("EFECTOS DE LAS VÁLVULAS")

        for valve in self.VALVES:

            print(
                f"{valve}: "
                f"cerrada "
                f"{self.effects[valve][False]:+d} | "
                f"abierta "
                f"{self.effects[valve][True]:+d}"
            )

        print()
        print(
            "CONFIGURACIONES DE EQUILIBRIO:",
            len(self.stable_solutions)
        )

        for configuration in self.stable_solutions:

            print(
                configuration,
                "->",
                self.calculate_change_for(
                    configuration
                ),
                "PSI/s"
            )

        print()
        print(
            "CONFIGURACIONES DE AJUSTE:",
            len(self.adjustment_solutions)
        )

        print()
        print("SOLUCIÓN DE REFERENCIA:")

        for valve in self.VALVES:

            state = (
                "ABIERTA"
                if self.solution[valve]
                else "CERRADA"
            )

            print(
                f"  {valve}: {state}"
            )

        print(
            "Cambio:",
            self.get_solution_change(),
            "PSI/s"
        )

        print("================================")
        print()