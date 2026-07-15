"""settlement message"""


class SettlementMessage:
    """Container for end-of-game statistics.

    Holds all the counters collected during a game session and formats
    them into a list of centred lines suitable for terminal display.

    Attributes:
        title: The settlement title (e.g. ``"GAME OVER"``, ``"YOU WIN!"``).
    """

    def __init__(
        self,
        title: str,
        score: int,
        lines: int,
        time: str,
        single: int,
        double: int,
        triple: int,
        tetris: int,
        t_spin: int,
        t_spin_single: int,
        t_spin_double: int,
        t_spin_triple: int,
        mini_t_spin: int,
        mini_t_spin_single: int,
        game_mode: str = "",
    ) -> None:
        # Summary
        self.title = title
        self._score = score
        self._lines = lines
        self._time = time
        self._game_mode = game_mode

        # Line clear counts
        self._single = single
        self._double = double
        self._triple = triple
        self._tetris = tetris

        # T-Spin counts
        self._t_spin = t_spin
        self._t_spin_single = t_spin_single
        self._t_spin_double = t_spin_double
        self._t_spin_triple = t_spin_triple
        self._mini_t_spin = mini_t_spin
        self._mini_t_spin_single = mini_t_spin_single

    def format(self, width: int) -> list[str]:
        """Format all statistics into centred lines fitting within *width*.

        Args:
            width: Available display width in columns.

        Returns:
            List of centred strings, each no wider than *width*.
        """
        harfw = width >> 1
        if self._game_mode:
            msgs = [f"Mode: {self._game_mode}"]
        else:
            msgs: list[str] = []
        msgs += [
            f"Score: {self._score}",
            f"Lines: {self._lines}",
            f"Time: {self._time}",
            f"Single: {self._single}",
            f"Double: {self._double}",
            f"Triple: {self._triple}",
            f"Tetris: {self._tetris}",
            f"T-Spin: {self._t_spin}",
            f"T-Spin Single: {self._t_spin_single}",
            f"T-Spin Double: {self._t_spin_double}",
            f"T-Spin Triple: {self._t_spin_triple}",
            f"Mini-T-Spin: {self._mini_t_spin}",
            f"Mini-T-Spin Single: {self._mini_t_spin_single}",
        ]
        i = 0
        res: list[str] = []
        cur_line = ""
        while i < len(msgs):
            if len(cur_line) + harfw > width or len(msgs[i]) > harfw:
                res.append(cur_line.center(width))
                cur_line = ""
            else:
                cur_line += msgs[i].center(harfw)
                i += 1
            if i == len(msgs):
                res.append(cur_line.center(width))
        return res
